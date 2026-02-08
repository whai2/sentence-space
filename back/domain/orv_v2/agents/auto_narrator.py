"""
Auto-Narrator Agent

GPT-4o 기반 자동 스토리 진행 에이전트
- 사용자 입력 없이 자동으로 멀티턴 스토리 생성
- 시나리오 시작 시점 감지 및 모드 전환 제안
"""
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from domain.orv_v2.models import GameState, ScenarioContext
from domain.orv_v2.models.scenario import EnrichedScenarioContext


# ============================================
# Auto-Narrator Structured Output
# ============================================

class AutoNarratorOutput(BaseModel):
    """
    Auto-Narrator 출력 (Structured Output)

    자동 진행 시 LLM이 플레이어 행동도 생성
    """
    # 자동 생성된 플레이어 행동
    player_action: str = Field(
        description="김독자가 수행한 행동 (자연스럽게)"
    )

    # 서술
    narrative: str = Field(
        description="웹소설 스타일 서술 (2-3 문단)"
    )

    # 분위기
    scene_mood: str = Field(
        description="장면 분위기 (tense, calm, hopeful, desperate)"
    )

    # 👉 시나리오 시작 감지
    scenario_starting: bool = Field(
        default=False,
        description="시나리오가 시작되는 시점인가? (도깨비 등장, 미션 공지 등)"
    )

    # 시나리오 시작 시 제공할 선택지
    initial_choices: list[str] = Field(
        default_factory=list,
        description="시나리오 시작 시 사용자에게 제공할 선택지 3-4개"
    )


# ============================================
# Auto-Narrator Prompts
# ============================================

AUTO_NARRATOR_SYSTEM_PROMPT = """당신은 "전지적 독자 시점" 웹소설의 **자동 진행 모드** 작가입니다.

## 핵심 역할
사용자 입력 없이 **김독자의 행동과 그 결과**를 자동으로 생성합니다.

## 자동 진행 원칙
1. **자연스러운 흐름**: 김독자가 현재 상황에서 취할 법한 행동 선택
2. **긴장감 유지**: 너무 빨리 해결하지 말 것 (관찰 → 분석 → 행동)
3. **캐릭터 일관성**: 김독자의 성격 (냉정, 전략적, 생존 우선) 유지
4. **점진적 진행**: 한 턴에 너무 많은 일이 일어나지 않도록

## 서술 스타일 (필수!)

### ✅ 좋은 예시
```
지하철이 멈췄다. 정확히는 3분 전이었다.

김독자는 스마트폰 화면을 내려다봤다. 「전지적 독자 시점」의 마지막 화. 그는 이미 결말을 알고 있었다.

'시작이군.'

주변 승객들은 아직 아무것도 모른다. 하지만 곧 알게 될 것이다. 이 세계가 어떻게 변할지.

객차 안이 어두워지기 시작했다.
```

### ❌ 나쁜 예시
```
김독자는 주변을 세심히 살피기 시작했다. 그는 무언가 이상한 기운을 감지했다. 김독자는 조용히 자리에서 일어나 주위를 둘러보았다.
```

**작성 규칙:**
- 짧고 강렬한 문장
- 김독자의 내면 독백 (' ')
- 메타적 요소 ([시스템], 「 」)
- "~했다" 남발 금지
- Show, Don't Tell

## 시나리오 시작 감지 (중요!)
다음 상황에서 **scenario_starting = true**로 설정:
- 도깨비가 등장하여 시나리오 공지
- 푸른 창이 뜨면서 미션 제시
- 제한 시간이 시작되는 순간
- "목표: ..." 같은 명확한 임무 제시

시나리오가 시작되면:
1. scenario_starting = true
2. initial_choices에 사용자가 선택할 수 있는 행동 3-4개 제공
3. 이후 게임은 INTERACTIVE 모드로 전환됨
"""


def create_auto_narrator_prompt(
    game_state: GameState,
    scenario_context: ScenarioContext | None,
    recent_history: str,
    enriched_context: EnrichedScenarioContext | None = None,
    story_guidance: str | None = None,
) -> str:
    """
    Auto-Narrator 프롬프트 생성

    Args:
        game_state: 현재 게임 상태
        scenario_context: 기본 시나리오 컨텍스트 (호환성 유지)
        recent_history: 최근 진행 요약
        enriched_context: GraphRAG로 강화된 시나리오 컨텍스트
        story_guidance: StoryExecutor의 가이던스
    """

    player = game_state.player

    state_summary = f"""
## 현재 상태 (턴 {game_state.turn_count})
- 위치: {player.position}
- 체력: {player.health}/{player.max_health}
- 코인: {player.coins}
- 레벨: {player.level}
"""

    # EnrichedContext 우선 사용
    scenario_info = ""
    if enriched_context:
        scenario_info = f"""
## 시나리오 정보
- 제목: {enriched_context.title} ({enriched_context.difficulty})
- 목표: {enriched_context.objective}
- 남은 시간: {enriched_context.remaining_time}턴

### 상세 배경
{enriched_context.detailed_description}

### 주요 등장인물
"""
        for char in enriched_context.key_characters[:3]:  # 상위 3명만
            scenario_info += f"\n- **{char.name}** ({char.character_type}): {char.role}"
            scenario_info += f"\n  {char.description[:100]}..."

        # 주인공 전용 트릭 (김독자만 아는 지식)
        if enriched_context.protagonist_tricks:
            scenario_info += "\n\n### 김독자만 아는 정보 (원작 지식)"
            for trick in enriched_context.protagonist_tricks:
                scenario_info += f"\n- **{trick.name}**"
                scenario_info += f"\n  {trick.description[:120]}..."
                if trick.narrative_hint:
                    scenario_info += f"\n  💭 서술 힌트: {trick.narrative_hint}"

        # 대안 솔루션 (도덕성 기준)
        if enriched_context.alternative_solutions:
            scenario_info += "\n\n### 가능한 선택지 (도덕성 순서)"
            for sol in enriched_context.alternative_solutions[:3]:  # 상위 3개
                scenario_info += f"\n- {sol.trick.name} (도덕성: {sol.morality_score}/10, 난이도: {sol.difficulty}/10)"

    elif scenario_context:
        # Fallback: 기본 시나리오 컨텍스트 사용
        scenario_info = f"""
## 시나리오 정보
- 제목: {scenario_context.title}
- 목표: {scenario_context.objective}
- 남은 시간: {scenario_context.remaining_time}턴
"""

    history_section = f"""
## 최근 진행
{recent_history}
"""

    # StoryExecutor 가이던스 (있으면)
    guidance_section = ""
    if story_guidance:
        guidance_section = f"""
## 📖 스토리 가이던스 (중요!)

{story_guidance}

**이 가이던스를 따라 서술하세요:**
- 현재 단계의 분위기와 톤을 유지하세요
- 다음 이벤트가 자연스럽게 발생하도록 유도하세요
- 서술 힌트를 참고하여 원작 느낌을 살리세요
"""

    # Few-shot 예시 (User Message에 직접 포함)
    few_shot_example = """
## 📝 서술 스타일 예시 (반드시 이 스타일을 따르세요!)

### ✅ 좋은 예시:
지하철이 멈췄다.

김독자는 스마트폰에서 눈을 떼지 않았다. 「전지적 독자 시점」 마지막 화. 화면 속 글자들이 천천히 스크롤되고 있었다.

'끝이군.'

주변 승객들이 웅성거리기 시작했다. 누군가 "왜 멈췄지?"라고 중얼거렸다. 하지만 김독자는 이미 알고 있었다.

객차 안이 어두워졌다.

### ❌ 나쁜 예시 (절대 이렇게 쓰지 마세요):
김독자는 주변을 둘러보았다. 그는 승객들이 당황한 표정으로 창밖을 내다보고 있다는 것을 알아차렸다. 김독자는 자리에서 일어났다.

---
"""

    prompt = f"""
{few_shot_example}

{state_summary}

{scenario_info}

{history_section}

{guidance_section}

---

다음 턴을 자동으로 진행하세요:
1. 김독자가 현재 상황에서 취할 법한 행동 선택
2. 그 행동의 결과를 서술
3. 시나리오가 시작되는 순간이라면 scenario_starting = true

**서술 규칙 (필수)**:
- 위 "좋은 예시" 스타일을 반드시 따르세요
- 짧고 강렬한 문장 (한 문장 2줄 이하)
- 김독자의 내면 독백 (' ')
- "~했다", "~였다" 남발 금지
- Show, Don't Tell

**기타**:
- **스토리 가이던스를 우선 참고**하세요 (있는 경우)
- 원작 지식을 활용하여 김독자가 일반인과 다른 선택을 하도록 하세요
- 너무 급하게 진행하지 마세요 (한 턴에 한 가지 행동)
- 김독자의 성격 (냉정, 전략적, 생존 우선)을 유지하세요
"""

    return prompt


# ============================================
# Auto-Narrator Agent
# ============================================

class AutoNarratorAgent:
    """
    자동 스토리 진행 에이전트

    GPT-4o 기반
    """

    def __init__(self, llm: ChatOpenAI):
        """
        Args:
            llm: GPT-4o LLM (LLMFactory에서 생성)
        """
        self.llm = llm
        # Structured Output 강제 (function_calling 방식)
        self.structured_llm = llm.with_structured_output(
            AutoNarratorOutput,
            method="function_calling"
        )

    async def generate_turn(
        self,
        game_state: GameState,
        scenario_context: ScenarioContext | None,
        recent_history: str,
        enriched_context: EnrichedScenarioContext | None = None,
        story_guidance: str | None = None,
    ) -> AutoNarratorOutput:
        """
        자동으로 다음 턴 생성

        Args:
            game_state: 현재 게임 상태
            scenario_context: 기본 시나리오 컨텍스트 (호환성)
            recent_history: 최근 3-5턴 요약
            enriched_context: GraphRAG로 강화된 시나리오 컨텍스트
            story_guidance: StoryExecutor의 가이던스

        Returns:
            AutoNarratorOutput: 자동 생성된 턴
        """
        prompt = create_auto_narrator_prompt(
            game_state=game_state,
            scenario_context=scenario_context,
            recent_history=recent_history,
            enriched_context=enriched_context,
            story_guidance=story_guidance,
        )

        messages = [
            SystemMessage(content=AUTO_NARRATOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        output: AutoNarratorOutput = await self.structured_llm.ainvoke(messages)

        return output
