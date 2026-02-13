"""
ORV v3 Narrator 테스트 스크립트

사용법:
    cd /Users/no-eunsu/hobby/sentence-space/back
    python -m domain.orv_v3.scripts.test_narrator          # 전체 테스트
    python -m domain.orv_v3.scripts.test_narrator 1        # 시나리오 1만
    python -m domain.orv_v3.scripts.test_narrator 2 3      # 시나리오 2, 3
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from domain.orv_v3.config import NarratorConfig, create_narrator_llm
from domain.orv_v3.narrator import NarratorAgent, SceneInput


# ============================================
# 샘플 입력 데이터 (전지적 독자 시점 세계관)
# ============================================

SAMPLE_WORLD_SETTING = """「전지적 독자 시점」 세계관.

어느 날, 세계가 소설이 되었다. 김독자가 유일하게 완독한 웹소설 「멸망 이후의 세 가지 방법」의 내용이 현실에서 그대로 재현되기 시작한다.

핵심 설정:
- "시나리오"가 현실을 지배한다. 도깨비들이 시나리오를 공지하고, 인간들은 시나리오를 클리어해야 생존할 수 있다.
- "성좌"들이 인간들의 행동을 관람하며, 코인(후원)을 보낸다.
- "스킬"과 "속성"이 존재하며, 시나리오를 클리어하면 보상을 받는다.
- 김독자만이 소설의 전체 내용을 알고 있어, 미래에 일어날 일을 예측할 수 있다.
- 현재 시점: 1차 시나리오 직전. 서울 지하철 3호선에서 최초의 시나리오가 시작되려 한다.

분위기: 일상이 붕괴되는 순간. 아직 대부분의 사람들은 무슨 일이 일어나고 있는지 모른다."""


SAMPLE_CHARACTER_SHEET = """### 김독자 (주인공)
- 직업: 회사원 (평범한 직장인)
- 나이: 28세
- 성격: 냉정하고 분석적. 감정을 잘 드러내지 않는다. 하지만 내면에는 강한 의지가 있다.
- 말투: 짧고 건조한 문장. 내면 독백이 많다. 속으로는 냉소적.
- 현재 상태: 퇴근길 지하철에서 「전지적 독자 시점」의 마지막 화를 막 읽었다. 곧 세계가 변할 것을 알고 있지만, 아직 행동하지 않고 관찰 중.
- 특수 능력: 「전지적 독자 시점」 완독자. 앞으로 일어날 모든 시나리오의 내용을 알고 있다.

### 유상아
- 직업: 지하철 승객 (대학생)
- 나이: 22세
- 성격: 활발하고 정의감이 강하다. 위기 상황에서도 남을 돕는 성향.
- 말투: 반말과 존댓말을 상황에 따라 섞어 사용. 감정이 목소리에 그대로 드러남.
- 현재 상태: 이어폰을 끼고 음악을 듣고 있다가, 지하철이 멈추면서 이상함을 느끼기 시작."""


# ============================================
# 테스트 시나리오들
# ============================================

TEST_SCENARIOS = [
    {
        "name": "시나리오 1: 도입 - 지하철이 멈추다",
        "narrative_stage": "도입부 - 일상의 균열. 아직 시나리오가 시작되지 않았지만, 이상한 징후가 나타나기 시작한다.",
        "previous_scene": "(이것이 첫 장면입니다. 직전 장면은 없습니다.)",
        "player_action": "스마트폰으로 「전지적 독자 시점」 마지막 화를 읽고 있다. 지하철이 갑자기 멈추자 주변을 조용히 관찰한다.",
        "extra_direction": "첫 장면이므로 세계관과 분위기를 자연스럽게 소개해주세요. 김독자가 '무언가를 알고 있다'는 느낌을 독백으로 암시하되, 직접적으로 설명하지 마세요.",
    },
    {
        "name": "시나리오 2: 갈등 고조 - 도깨비의 등장",
        "narrative_stage": "갈등 고조 - 시나리오가 공지되었다. 사람들이 혼란에 빠지기 시작한다.",
        "previous_scene": (
            "지하철이 멈춘 지 3분이 지났다. 객차 안의 조명이 한 번 깜빡였다.\n\n"
            "그때, 허공에 푸른 창이 떠올랐다.\n\n"
            "[주목하세요. 이제부터 당신들의 이야기가 시작됩니다.]\n\n"
            "승객들의 비명이 객차를 채웠다. 누군가 뒷걸음질을 쳤고, "
            "어딘가에서 유리가 깨지는 소리가 들렸다.\n\n"
            "김독자만이 조용히 그 창을 올려다보고 있었다.\n\n"
            "'드디어 시작됐군.'"
        ),
        "player_action": "김독자는 자리에서 일어나 객차 앞쪽으로 조용히 이동한다. 도깨비가 나타날 위치를 이미 알고 있기 때문이다.",
        "extra_direction": "도깨비의 등장을 서술해주세요. 도깨비는 작은 체구에 기묘한 미소를 짓고 있습니다. 1차 시나리오를 공지합니다. 주변 사람들의 공포와 김독자의 냉정함의 대비를 강조해주세요.",
    },
    {
        "name": "시나리오 3: 클라이맥스 - 생존을 위한 선택",
        "narrative_stage": "클라이맥스 - 1차 시나리오의 제한 시간이 다가오고 있다. 살아남기 위해 결단을 내려야 한다.",
        "previous_scene": (
            "[1차 시나리오 - 제한 시간 내에 생명체를 죽이시오]\n"
            "[남은 시간 - 2분 13초]\n\n"
            "객차 안은 이미 아수라장이었다. 피 냄새가 코를 찔렀다. "
            "누군가는 울고 있었고, 누군가는 이미 움직이지 않았다.\n\n"
            "유상아가 김독자의 소매를 잡았다.\n\n"
            '"우리... 어떡해요?"\n\n'
            "그녀의 손이 떨리고 있었다. 하지만 눈빛은 아직 살아 있었다.\n\n"
            "김독자는 발밑을 내려다봤다. 바닥을 기어가는 벌레 한 마리가 보였다."
        ),
        "player_action": "바닥의 벌레를 밟아 죽인다. 그리고 유상아에게 '당신도 해요. 벌레도 생명체입니다.'라고 말한다.",
        "extra_direction": "긴박한 클라이맥스 장면입니다. 김독자의 행동이 주변 사람들에게 미치는 영향을 서술하세요. 유상아의 반응을 포함해주세요. 시나리오 클리어 직전의 긴장감을 극대화하세요.",
    },
]


# ============================================
# 테스트 실행
# ============================================


async def run_test(agent: NarratorAgent, scenario: dict, index: int) -> str:
    """단일 시나리오 테스트"""
    print(f"\n{'=' * 70}")
    print(f"  테스트 {index + 1}: {scenario['name']}")
    print(f"{'=' * 70}")
    print(f"\n[서사 단계] {scenario['narrative_stage']}")
    print(f"[플레이어 행동] {scenario['player_action']}")
    print(f"\n{'─' * 70}")
    print("생성 중...")

    scene_input = SceneInput(
        world_setting=SAMPLE_WORLD_SETTING,
        character_sheet=SAMPLE_CHARACTER_SHEET,
        narrative_stage=scenario["narrative_stage"],
        previous_scene=scenario["previous_scene"],
        player_action=scenario["player_action"],
        extra_direction=scenario.get("extra_direction", ""),
    )

    start_time = time.time()
    result = await agent.narrate(scene_input)
    elapsed = time.time() - start_time

    print(f"\n{'─' * 70}")
    print(f"  생성된 장면 ({len(result)}자, {elapsed:.1f}초)")
    print(f"{'─' * 70}\n")
    print(result)
    print(f"\n{'─' * 70}")

    # 간단한 품질 체크
    checks = {
        "분량 (500~1500자)": 500 <= len(result) <= 1500,
        "내면 독백 포함 (')": "'" in result,
        "'김독자는' 과다반복 없음 (≤3)": result.count("김독자는") <= 3,
        "'~했다' 3연속 없음": "했다." not in _find_triple_repeat(result),
    }

    print("\n[품질 체크]")
    for check_name, passed in checks.items():
        status = "PASS" if passed else "WARN"
        print(f"  [{status}] {check_name}")

    return result


def _find_triple_repeat(text: str) -> str:
    """'~했다.' 가 3문장 연속인 패턴 탐지"""
    sentences = text.replace("\n", " ").split(".")
    count = 0
    for s in sentences:
        s = s.strip()
        if s.endswith("했다") or s.endswith("였다"):
            count += 1
            if count >= 3:
                return "했다."
        else:
            count = 0
    return ""


async def main():
    """메인 테스트 함수"""
    print("=" * 70)
    print("  ORV v3 Narrator Agent 테스트")
    print("  Model: Gemini 2.5 Flash via OpenRouter")
    print("=" * 70)

    # API 키 확인
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("\n[ERROR] OPENROUTER_API_KEY 환경변수가 설정되지 않았습니다.")
        print("  방법 1: .env 파일에 OPENROUTER_API_KEY=sk-xxx 추가")
        print(
            "  방법 2: OPENROUTER_API_KEY=sk-xxx "
            "python -m domain.orv_v3.scripts.test_narrator"
        )
        sys.exit(1)

    print(f"\n  API Key: {api_key[:8]}...{api_key[-4:]}")

    # Agent 생성
    config = NarratorConfig.from_env()
    llm = create_narrator_llm(config)
    agent = NarratorAgent(llm=llm)

    print(f"  Model: {config.model}")
    print(f"  Temperature: {config.temperature}")

    # 테스트 시나리오 선택
    if len(sys.argv) > 1:
        indices = [int(i) - 1 for i in sys.argv[1:]]
    else:
        indices = list(range(len(TEST_SCENARIOS)))

    results = []
    for i in indices:
        if 0 <= i < len(TEST_SCENARIOS):
            result = await run_test(agent, TEST_SCENARIOS[i], i)
            results.append(result)

    # 요약
    print(f"\n\n{'=' * 70}")
    print(f"  테스트 완료: {len(results)}개 시나리오")
    print(f"{'=' * 70}")
    for i, result in enumerate(results):
        print(f"  시나리오 {indices[i] + 1}: {len(result)}자")


if __name__ == "__main__":
    asyncio.run(main())
