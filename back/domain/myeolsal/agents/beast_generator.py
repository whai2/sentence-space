"""
괴수 보간 생성 에이전트

세계관 규칙에 맞는 새로운 괴수 생성
"""
import json
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from domain.myeolsal.models import (
    BeastEntry,
    BeastLayer,
    BeastStats,
    CombatPattern,
    MyeolsalRules,
)


class GenerationRequest(BaseModel):
    """괴수 생성 요청"""
    concept: str = Field(description="기본 컨셉 (예: '7급 화염 늑대')")
    grade: str | None = Field(default=None, description="등급 지정")
    species: str | None = Field(default=None, description="종 지정")
    constraints: dict[str, Any] = Field(default_factory=dict, description="추가 제약")


class GeneratedBeast(BaseModel):
    """LLM 생성 결과"""
    title: str = Field(description="괴수 이름")
    grade: str = Field(description="등급 (9급~특급)")
    species: str = Field(description="종 (괴수종, 악마종, 거신, 재앙)")
    danger_class: str = Field(description="위험도 (안전, 보통, 위험, 치명)")
    description: str = Field(description="기본 설명")
    combat_patterns: list[dict] = Field(description="전투 패턴")
    survival_guide: str = Field(description="생존 지침")
    warnings: list[str] = Field(description="주의사항")
    lore_notes: str = Field(description="세계관 메모")
    stats: dict = Field(description="능력치")
    weaknesses: list[str] = Field(description="약점")
    resistances: list[str] = Field(description="저항")
    coin_reward_range: list[int] = Field(description="코인 보상 [min, max]")
    evolution_line: list[str] = Field(default_factory=list, description="진화 계통")


SYSTEM_PROMPT = """당신은 'tls123', 멸살법의 저자입니다.
독자들을 위한 괴수 백과를 집필합니다.

## 규칙
1. **등급별 스탯 범위**를 반드시 준수하세요:
{grade_rules}

2. **종별 특성**을 따르세요:
{species_rules}

3. **속성 상성**을 고려하세요:
{element_rules}

4. tls123의 목소리로 쓰세요:
   - 실용적이고 직접적인 어조
   - 직접 경험하거나 조사한 것처럼 서술
   - 생존에 필요한 핵심만 전달

5. **보간된 항목임을 암시**하세요:
   - "추정", "확인 안 됨" 등의 표현 사용
   - 불확실한 정보는 명시

## 기존 괴수 예시
{example_beasts}

## 출력 형식
JSON 형식으로 출력하세요. 아래 필드를 포함해야 합니다:
- title, grade, species, danger_class
- description, combat_patterns, survival_guide, warnings, lore_notes
- stats (hp, atk, defense, spd, spc)
- weaknesses, resistances, coin_reward_range
"""


class BeastGeneratorAgent:
    """
    괴수 보간 생성 에이전트

    세계관 규칙에 맞는 새로운 괴수를 생성
    """

    def __init__(
        self,
        llm: ChatAnthropic,
        rules: MyeolsalRules,
        example_beasts: list[BeastEntry] | None = None
    ):
        """
        Args:
            llm: Claude LLM 인스턴스
            rules: 멸살법 규칙
            example_beasts: 참고할 예시 괴수들
        """
        self.llm = llm
        self.rules = rules
        self.example_beasts = example_beasts or []

    def _format_grade_rules(self) -> str:
        """등급 규칙 포맷팅"""
        lines = []
        for gr in self.rules.grade_stat_ranges:
            lines.append(
                f"- {gr.grade}: HP {gr.hp_range[0]}~{gr.hp_range[1]}, "
                f"ATK {gr.atk_range[0]}~{gr.atk_range[1]}, "
                f"DEF {gr.def_range[0]}~{gr.def_range[1]}, "
                f"SPD {gr.spd_range[0]}~{gr.spd_range[1]}, "
                f"SPC {gr.spc_range[0]}~{gr.spc_range[1]}"
            )
        return "\n".join(lines)

    def _format_species_rules(self) -> str:
        """종별 특성 포맷팅"""
        lines = []
        for sp in self.rules.species_traits:
            traits = ", ".join(sp.special_traits[:3])
            lines.append(f"- {sp.species}: 지능({sp.intelligence}), 협상({sp.negotiable}), {traits}")
        return "\n".join(lines)

    def _format_element_rules(self) -> str:
        """속성 상성 포맷팅"""
        lines = []
        for el in self.rules.elemental_affinities:
            strong = ", ".join(el.strong_against[:2]) if el.strong_against else "없음"
            weak = ", ".join(el.weak_against[:2]) if el.weak_against else "없음"
            lines.append(f"- {el.element}: 강함→{strong}, 약함→{weak}")
        return "\n".join(lines)

    def _format_examples(self) -> str:
        """예시 괴수 포맷팅"""
        if not self.example_beasts:
            return "예시 없음"

        examples = []
        for beast in self.example_beasts[:3]:  # 최대 3개
            examples.append(f"""
### {beast.title} ({beast.grade} {beast.species})
설명: {beast.description[:200]}...
스탯: HP={beast.stats.hp}, ATK={beast.stats.atk}, DEF={beast.stats.defense}
약점: {', '.join(beast.weaknesses)}
생존: {beast.survival_guide[:100]}...
""")
        return "\n".join(examples)

    async def generate(
        self,
        request: GenerationRequest,
        similar_beasts: list[BeastEntry] | None = None
    ) -> BeastEntry:
        """
        새로운 괴수 생성

        Args:
            request: 생성 요청
            similar_beasts: 참고할 유사 괴수들

        Returns:
            생성된 괴수
        """
        # 예시 괴수 업데이트
        examples = similar_beasts or self.example_beasts

        # 프롬프트 구성
        system_prompt = SYSTEM_PROMPT.format(
            grade_rules=self._format_grade_rules(),
            species_rules=self._format_species_rules(),
            element_rules=self._format_element_rules(),
            example_beasts=self._format_examples() if not similar_beasts else self._format_similar_beasts(similar_beasts)
        )

        # 사용자 요청 구성
        user_prompt = f"""다음 컨셉의 새로운 괴수를 생성해주세요:

**컨셉**: {request.concept}
"""
        if request.grade:
            user_prompt += f"**등급 지정**: {request.grade}\n"
        if request.species:
            user_prompt += f"**종 지정**: {request.species}\n"
        if request.constraints:
            user_prompt += f"**추가 조건**: {json.dumps(request.constraints, ensure_ascii=False)}\n"

        user_prompt += "\nJSON 형식으로 출력해주세요."

        # LLM 호출 (구조화된 출력)
        structured_llm = self.llm.with_structured_output(GeneratedBeast)

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])

        chain = prompt | structured_llm
        result: GeneratedBeast = await chain.ainvoke({})

        # BeastEntry로 변환
        beast_id = self._generate_id(result.title, result.grade, result.species)

        return BeastEntry(
            id=beast_id,
            layer=BeastLayer.GENERATED,
            confidence=0.7,  # 생성된 항목은 신뢰도 낮음
            source="generated:claude",
            volume=1,
            tags=self._generate_tags(result),
            title=result.title,
            grade=result.grade,
            species=result.species,
            danger_class=result.danger_class,
            description=result.description,
            combat_patterns=[
                CombatPattern(**p) for p in result.combat_patterns
            ],
            survival_guide=result.survival_guide,
            warnings=result.warnings,
            lore_notes=result.lore_notes,
            stats=BeastStats(**result.stats),
            weaknesses=result.weaknesses,
            resistances=result.resistances,
            coin_reward_range=tuple(result.coin_reward_range),
            evolution_line=result.evolution_line,
        )

    def _format_similar_beasts(self, beasts: list[BeastEntry]) -> str:
        """유사 괴수 포맷팅"""
        examples = []
        for beast in beasts[:3]:
            examples.append(f"- {beast.title} ({beast.grade} {beast.species}): {beast.description[:100]}...")
        return "\n".join(examples)

    def _generate_id(self, title: str, grade: str, species: str) -> str:
        """괴수 ID 생성"""
        # 한글을 영문으로 변환하지 않고 간단히 처리
        import re
        clean_title = re.sub(r'[^\w가-힣]', '_', title.lower())
        grade_num = grade.replace('급', '').replace('특', 'special')
        return f"beast_gen_{clean_title}_{grade_num}"

    def _generate_tags(self, result: GeneratedBeast) -> list[str]:
        """태그 생성"""
        tags = [result.grade, result.species]
        tags.extend(result.weaknesses[:2])
        return tags
