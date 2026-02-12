"""
괴수 배치 생성 스크립트

LLM을 활용해 100마리의 괴수를 5마리씩 배치로 생성.
기존 BeastGeneratorAgent의 프롬프트 형식과 GeneratedBeast 모델을 재활용.

Usage:
    cd back
    uv run python -m domain.myeolsal.scripts.batch_generate              # 100마리 생성
    uv run python -m domain.myeolsal.scripts.batch_generate --dry-run    # 컨셉만 출력
    uv run python -m domain.myeolsal.scripts.batch_generate --resume     # 중단된 곳부터 재개
    uv run python -m domain.myeolsal.scripts.batch_generate --count 20   # 20마리만 생성
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from domain.myeolsal.models import (
    BeastEntry,
    BeastLayer,
    BeastStats,
    CombatPattern,
    MyeolsalRules,
)
from domain.myeolsal.agents.beast_generator import GeneratedBeast, SYSTEM_PROMPT
from domain.myeolsal.agents.beast_validator import BeastValidatorAgent
from domain.myeolsal.container import (
    get_myeolsal_rules,
    get_pinecone_repository,
    get_validator,
)
from domain.myeolsal.scripts.concept_matrix import (
    generate_concepts,
    print_concepts,
    BeastConcept,
)
from server.config import get_settings


# === 배치 생성용 모델 ===

class BatchGeneratedBeasts(BaseModel):
    """5마리 배치 생성 결과"""
    beasts: list[GeneratedBeast] = Field(description="생성된 괴수 리스트 (5마리)")


# === 등급별 코인 보상 참고값 ===

COIN_REFERENCE = {
    "9급": "5~20",
    "8급": "15~50",
    "7급": "30~100",
    "6급": "80~250",
    "5급": "200~600",
    "4급": "500~1500",
    "3급": "1000~3000",
    "2급": "2500~7000",
    "1급": "5000~15000",
    "특급": "10000~50000",
}


# === 배치 시스템 프롬프트 확장 ===

BATCH_SYSTEM_ADDENDUM = """
## 추가 규칙 (배치 생성)

6. 정확히 {batch_size}마리를 생성하세요. 각각 **다른 이름, 다른 컨셉**이어야 합니다.

7. **코인 보상 참고값** (등급별 [min, max]):
{coin_reference}

8. **중복 금지** - 아래 이름은 이미 존재합니다. 절대 동일 이름 사용 금지:
{existing_names}

9. combat_patterns의 각 항목은 반드시 name, trigger, description 필드를 포함해야 합니다.
   trigger 예시: "always", "hp_below_50", "enraged", "group_3plus", "night_only"

10. stats는 반드시 hp, atk, defense, spd, spc 필드를 포함해야 합니다.
    스탯 값은 등급 범위 표를 엄격히 따르세요.
"""


BATCH_USER_PROMPT = """다음 {batch_size}개 컨셉에 맞는 괴수를 각각 생성해주세요:

{concepts}

각 괴수마다 JSON 형식으로 아래 필드를 모두 포함해 출력하세요:
title, grade, species, danger_class, description, combat_patterns, survival_guide, warnings, lore_notes, stats, weaknesses, resistances, coin_reward_range, evolution_line
"""


# === 진행 상황 파일 ===

PROGRESS_FILE = Path(__file__).parent / "_batch_progress.json"
DATA_DIR = Path(__file__).parent.parent / "data"
CANON_FILE = DATA_DIR / "canon_beasts.json"


def get_batch_llm():
    """배치 생성용 LLM (max_tokens 높음)"""
    settings = get_settings()

    if settings.openrouter_api_key:
        return ChatOpenAI(
            model=settings.llm_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=8192,
        )

    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.7,
        max_tokens=8192,
    )


def get_existing_names() -> set[str]:
    """기존 괴수 이름 목록"""
    if not CANON_FILE.exists():
        return set()
    with open(CANON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {b["title"] for b in data.get("beasts", [])}


def format_rules(rules: MyeolsalRules) -> tuple[str, str, str]:
    """규칙 포맷팅 (BeastGeneratorAgent 로직 재사용)"""
    grade_lines = []
    for gr in rules.grade_stat_ranges:
        grade_lines.append(
            f"- {gr.grade}: HP {gr.hp_range[0]}~{gr.hp_range[1]}, "
            f"ATK {gr.atk_range[0]}~{gr.atk_range[1]}, "
            f"DEF {gr.def_range[0]}~{gr.def_range[1]}, "
            f"SPD {gr.spd_range[0]}~{gr.spd_range[1]}, "
            f"SPC {gr.spc_range[0]}~{gr.spc_range[1]}"
        )

    species_lines = []
    for sp in rules.species_traits:
        traits = ", ".join(sp.special_traits[:3])
        species_lines.append(f"- {sp.species}: 지능({sp.intelligence}), 협상({sp.negotiable}), {traits}")

    element_lines = []
    for el in rules.elemental_affinities:
        strong = ", ".join(el.strong_against[:2]) if el.strong_against else "없음"
        weak = ", ".join(el.weak_against[:2]) if el.weak_against else "없음"
        element_lines.append(f"- {el.element}: 강함→{strong}, 약함→{weak}")

    return "\n".join(grade_lines), "\n".join(species_lines), "\n".join(element_lines)


def generate_id(title: str, grade: str) -> str:
    """괴수 ID 생성"""
    clean_title = re.sub(r'[^\w가-힣]', '_', title.lower())
    grade_num = grade.replace('급', '').replace('특', 'special')
    return f"beast_gen_{clean_title}_{grade_num}"


def generated_to_entry(result: GeneratedBeast) -> BeastEntry:
    """GeneratedBeast → BeastEntry 변환"""
    beast_id = generate_id(result.title, result.grade)

    tags = [result.grade, result.species]
    tags.extend(result.weaknesses[:2])

    return BeastEntry(
        id=beast_id,
        layer=BeastLayer.GENERATED,
        confidence=0.7,
        source="generated:claude:batch",
        volume=1,
        tags=tags,
        title=result.title,
        grade=result.grade,
        species=result.species,
        danger_class=result.danger_class,
        description=result.description,
        combat_patterns=[CombatPattern(**p) for p in result.combat_patterns],
        survival_guide=result.survival_guide,
        warnings=result.warnings,
        lore_notes=result.lore_notes,
        stats=BeastStats(**result.stats),
        weaknesses=result.weaknesses,
        resistances=result.resistances,
        coin_reward_range=tuple(result.coin_reward_range),
        evolution_line=result.evolution_line,
    )


def load_progress() -> dict:
    """진행 상황 로드"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_batches": [], "generated_beasts": []}


def save_progress(progress: dict) -> None:
    """진행 상황 저장"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def append_to_canon(beasts: list[BeastEntry]) -> None:
    """canon_beasts.json에 추가"""
    if not CANON_FILE.exists():
        data = {"beasts": []}
    else:
        with open(CANON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    for beast in beasts:
        beast_dict = beast.model_dump(mode="json")
        # datetime → string 변환
        for key in ("created_at", "updated_at"):
            if key in beast_dict and beast_dict[key]:
                beast_dict[key] = str(beast_dict[key])
        data["beasts"].append(beast_dict)

    with open(CANON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def run_batch(
    batch_idx: int,
    concepts: list[BeastConcept],
    llm,
    rules: MyeolsalRules,
    validator: BeastValidatorAgent,
    existing_names: set[str],
) -> list[BeastEntry]:
    """단일 배치 실행"""
    batch_size = len(concepts)

    # 규칙 포맷팅
    grade_rules, species_rules, element_rules = format_rules(rules)

    # 코인 참고값
    coin_ref_lines = [f"  - {g}: [{v}]" for g, v in COIN_REFERENCE.items()]
    coin_reference = "\n".join(coin_ref_lines)

    # 기존 이름 (축약)
    name_list = ", ".join(sorted(existing_names)[:80])
    if len(existing_names) > 80:
        name_list += f" ... 외 {len(existing_names) - 80}개"

    # 시스템 프롬프트
    system_prompt = SYSTEM_PROMPT.format(
        grade_rules=grade_rules,
        species_rules=species_rules,
        element_rules=element_rules,
        example_beasts="(배치 생성 모드 - 예시 생략)",
    ) + BATCH_SYSTEM_ADDENDUM.format(
        batch_size=batch_size,
        coin_reference=coin_reference,
        existing_names=name_list,
    )

    # 컨셉 목록
    concept_text = "\n".join(
        f"{i+1}. {c.prompt}" for i, c in enumerate(concepts)
    )

    user_prompt = BATCH_USER_PROMPT.format(
        batch_size=batch_size,
        concepts=concept_text,
    )

    # LLM 호출
    structured_llm = llm.with_structured_output(BatchGeneratedBeasts)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt),
    ])
    chain = prompt | structured_llm

    print(f"\n  [Batch {batch_idx+1}] LLM 호출 중... ({batch_size}마리)")
    start = time.time()
    result: BatchGeneratedBeasts = await chain.ainvoke({})
    elapsed = time.time() - start
    print(f"  [Batch {batch_idx+1}] LLM 응답 ({elapsed:.1f}s, {len(result.beasts)}마리)")

    # 변환 + 검증
    valid_beasts: list[BeastEntry] = []
    for gen_beast in result.beasts:
        try:
            beast = generated_to_entry(gen_beast)

            # 이름 중복 체크
            if beast.title in existing_names:
                print(f"    - SKIP (중복): {beast.title}")
                continue

            # 검증 + 자동 수정
            beast = validator.fix_stats(beast)
            validation = validator.validate(beast)

            if validation.is_valid:
                valid_beasts.append(beast)
                existing_names.add(beast.title)
                print(f"    + OK: {beast.title} ({beast.grade} {beast.species})")
            else:
                print(f"    - FAIL: {beast.title} - {validation.errors}")
        except Exception as e:
            print(f"    - ERROR: {gen_beast.title} - {e}")

    return valid_beasts


async def main():
    parser = argparse.ArgumentParser(description="괴수 배치 생성")
    parser.add_argument("--dry-run", action="store_true", help="컨셉만 출력")
    parser.add_argument("--count", type=int, default=100, help="생성할 괴수 수")
    parser.add_argument("--resume", action="store_true", help="중단된 곳부터 재개")
    parser.add_argument("--batch-size", type=int, default=5, help="배치당 괴수 수")
    parser.add_argument("--save-pinecone", action="store_true", default=True, help="Pinecone 저장")
    parser.add_argument("--no-pinecone", action="store_true", help="Pinecone 저장 안 함")
    args = parser.parse_args()

    save_pinecone = not args.no_pinecone

    # 컨셉 생성
    concepts = generate_concepts(count=args.count)
    print(f"\n{'='*60}")
    print(f"  괴수 배치 생성 ({args.count}마리, {args.batch_size}마리/배치)")
    print(f"{'='*60}")

    if args.dry_run:
        print_concepts(concepts)
        print(f"\n  --dry-run 모드: 실제 생성하지 않음")
        return

    # 의존성
    rules = get_myeolsal_rules()
    validator = get_validator()
    llm = get_batch_llm()
    pinecone_repo = get_pinecone_repository() if save_pinecone else None
    existing_names = get_existing_names()

    print(f"\n  기존 괴수: {len(existing_names)}마리")
    if pinecone_repo:
        print(f"  Pinecone 카운트: {pinecone_repo.count()}")

    # 배치 분할
    batches = []
    for i in range(0, len(concepts), args.batch_size):
        batches.append(concepts[i:i + args.batch_size])

    # 재개 처리
    progress = load_progress() if args.resume else {"completed_batches": [], "generated_beasts": []}
    start_batch = len(progress["completed_batches"])

    if start_batch > 0:
        print(f"\n  재개: {start_batch}번째 배치부터 ({len(progress['generated_beasts'])}마리 완료)")
        # 이미 생성된 이름 추가
        for b in progress["generated_beasts"]:
            existing_names.add(b["title"])

    # 배치 실행
    all_beasts: list[BeastEntry] = []
    total_start = time.time()

    for batch_idx in range(start_batch, len(batches)):
        batch_concepts = batches[batch_idx]

        try:
            beasts = await run_batch(
                batch_idx=batch_idx,
                concepts=batch_concepts,
                llm=llm,
                rules=rules,
                validator=validator,
                existing_names=existing_names,
            )

            # Pinecone 저장
            if pinecone_repo and beasts:
                for beast in beasts:
                    try:
                        pinecone_repo.add_beast(beast)
                    except Exception as e:
                        print(f"    ! Pinecone 저장 실패: {beast.title} - {e}")

            all_beasts.extend(beasts)

            # canon_beasts.json 추가 (배치마다)
            if beasts:
                append_to_canon(beasts)

            # 진행 상황 저장
            progress["completed_batches"].append(batch_idx)
            for b in beasts:
                progress["generated_beasts"].append({
                    "id": b.id,
                    "title": b.title,
                    "grade": b.grade,
                    "species": b.species,
                })
            save_progress(progress)

        except Exception as e:
            print(f"\n  !!! Batch {batch_idx+1} 실패: {e}")
            print(f"  진행 상황 저장됨. --resume 으로 재개 가능.")
            save_progress(progress)
            break

    # 결과
    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  생성 완료!")
    print(f"  총 소요 시간: {total_elapsed:.1f}s")
    print(f"  생성 성공: {len(all_beasts)}마리")
    print(f"  기존 + 신규: {len(existing_names)}마리")
    if pinecone_repo:
        print(f"  Pinecone 카운트: {pinecone_repo.count()}")
    print(f"{'='*60}")

    # 등급 분포
    grade_dist: dict[str, int] = {}
    for b in all_beasts:
        grade_dist[b.grade] = grade_dist.get(b.grade, 0) + 1
    print(f"\n  === 신규 등급 분포 ===")
    for g in ["9급", "8급", "7급", "6급", "5급", "4급", "3급", "2급", "1급", "특급"]:
        cnt = grade_dist.get(g, 0)
        bar = "#" * cnt
        print(f"  {g:4s}: {cnt:2d} {bar}")

    # 진행 파일 정리
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        print(f"\n  진행 파일 삭제됨")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
