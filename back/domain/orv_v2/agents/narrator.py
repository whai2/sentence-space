"""
Novel Narrator Agent

GPT-4o 기반 웹소설 서술 에이전트
- Orchestrator의 지시를 받아 서술 생성
- 전지적 독자 시점 스타일
- 분위기 조성 및 선택지 제안
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from domain.orv_v2.models import (
    GameState,
    OrchestratorDecision,
    NarratorOutput,
)


# ============================================
# Narrator 프롬프트
# ============================================

NARRATOR_SYSTEM_PROMPT = """당신은 "전지적 독자 시점" 스타일의 **웹소설 작가**입니다.

## 핵심 역할
Orchestrator의 지시를 받아 **몰입감 있는 웹소설 서술**을 생성합니다.

## 서술 스타일 (중요!)

### ✅ 좋은 예시 (이렇게 써주세요)

```
지하철이 멈췄다.

김독자는 스마트폰에서 눈을 떼지 않은 채 주변을 살폈다. 사람들은 아직 아무것도 눈치채지 못한 것 같았다. 하지만 곧 알게 될 것이다.

[남은 시간 - 4분 38초]

'시작됐구나.'

이윽고 객차 안에 낮은 울음소리가 퍼지기 시작했다. 한 여학생이 떨리는 손으로 창밖을 가리켰다.

"저, 저기..."

김독자도 창밖을 봤다. 어둠 속에서 무언가가 움직이고 있었다. 아직 형체를 알아볼 수는 없었지만, 그것이 무엇인지는 이미 알고 있었다.

그는 조용히 자리에서 일어났다.
```

**특징:**
- 짧고 강렬한 문장
- 김독자의 내면 독백 (' ')으로 심리 표현
- 메타적 요소 (시스템 메시지, 타이머 등)
- 불필요한 "~했다" 반복 회피
- 긴장감 있는 전개

### ❌ 나쁜 예시 (절대 이렇게 쓰지 마세요)

```
김독자는 주변을 세심히 살피기 시작했다. 그는 사람들 사이로 몇몇이 불안한 눈빛으로 주위를 살피고 있다는 것을 감지했다. 한쪽에서 누군가가 작은 소리로 속삭였고, 그것이 주변 사람들의 귀에 들어가자 미묘한 파장이 일어났다. 김독자는 그들의 대화를 엿들으며, 그들이 무언가를 두려워하고 있다는 것을 감지했다.
```

**문제점:**
- "김독자는 ~했다" 계속 반복
- 너무 설명적이고 장황함
- 긴장감 없음
- 내면 독백 없음

## 구체적인 작성 규칙

1. **짧은 문장 사용**: 한 문장은 2줄 이하
2. **내면 독백 활용**: 김독자의 생각을 ' ' 안에
3. **메타적 요소**: [시스템 메시지], 푸른 창 등 활용
4. **Show, Don't Tell**: "두려워했다" (X) → "손이 떨렸다" (O)
5. **리듬감**: 짧은 문장과 긴 문장을 섞어 리듬 생성
6. **원작 지식 활용**: 김독자만 아는 정보를 독백으로 암시

## 분위기별 톤
- **tense**: 짧고 끊어지는 문장, 시간 압박 강조
- **hopeful**: 약간 긴 호흡, 희망적인 발견
- **desperate**: 극도로 짧은 문장, 절박한 내면 독백
- **calm**: 분석적인 톤, 전략적 사고

## 선택지 제안
- 구체적이고 행동 지향적
- 예: "주변을 살핀다" (X) → "창밖의 그림자를 주시하며 움직임을 파악한다" (O)

## 금지 사항
- "~했다", "~였다" 남발 금지
- 장황한 설명 금지
- 플레이어 행동 강제 금지
- 결과 예측 금지

## 출력 형식
반드시 구조화된 JSON 형식으로 출력하세요.
- narrative: 웹소설 서술 (2-4 문단, 위 스타일 준수)
- scene_mood: 장면 분위기
- npc_reactions: NPC 반응 요약 목록
- suggested_choices: 선택지 3-4개
"""


def create_narrator_prompt(
    player_action: str,
    game_state: GameState,
    orchestrator_decision: OrchestratorDecision,
    npc_reactions: list[str] | None = None,
) -> str:
    """Narrator 서술용 프롬프트 생성"""

    player = game_state.player

    # Orchestrator 지시사항
    instruction = f"""
## Orchestrator 지시사항
{orchestrator_decision.narrator_instruction}

## 상황 분석
{orchestrator_decision.situation_analysis}

## 적용된 상태 변경
{_format_state_changes(orchestrator_decision.state_changes)}
"""

    # NPC 반응 (있으면)
    npc_section = ""
    if npc_reactions:
        npc_section = f"""
## NPC 반응
{chr(10).join([f"- {reaction}" for reaction in npc_reactions])}
"""

    # 현재 상태
    state_summary = f"""
## 현재 상태 (서술에 자연스럽게 녹여내세요)
- 위치: {player.position}
- 체력: {player.health}/{player.max_health}
- 턴: {game_state.turn_count}
"""

    if game_state.current_scenario:
        state_summary += f"""
- 시나리오: {game_state.current_scenario.title}
- 남은 시간: {game_state.current_scenario.remaining_time}턴
"""

    # Few-shot 예시
    few_shot_example = """
## 📝 서술 스타일 예시 (반드시 이 스타일을 따르세요!)

### ✅ 좋은 예시:
칼날이 번쩍였다.

김독자는 몸을 옆으로 굴렸다. 칼끝이 어깨를 스쳤다. 따끔한 통증.

'빠르군.'

상대는 이미 다음 공격을 준비하고 있었다. 하지만 김독자도 마찬가지였다.

[체력 -5]

그는 손을 뻗어 상대의 팔목을 잡았다.

### ❌ 나쁜 예시:
김독자는 공격을 피했다. 그는 상대가 빠르다는 것을 알아차렸다. 김독자는 반격을 준비했다.

---
"""

    prompt = f"""
{few_shot_example}

{instruction}

{state_summary}

{npc_section}

## 플레이어 행동
{player_action}

---

위 정보를 바탕으로 **전지적 독자 시점** 스타일의 웹소설 서술을 작성하세요.

**서술 규칙 (필수)**:
- 위 "좋은 예시" 스타일을 반드시 따르세요
- 짧고 강렬한 문장 (한 문장 2줄 이하)
- 김독자의 내면 독백 (' ')
- "~했다", "~였다" 남발 금지
- Show, Don't Tell

**기타 중요사항**:
1. Orchestrator의 지시사항을 반영하세요
2. 상태 변경을 자연스럽게 서술에 녹여내세요
3. 2-4 문단으로 간결하게
4. 김독자의 심리와 전략적 사고를 묘사하세요
5. 선택지는 구체적이고 현실적으로 제안하세요
"""

    return prompt


def _format_state_changes(changes) -> str:
    """상태 변경을 읽기 쉽게 포맷"""
    lines = []

    if changes.health_change:
        lines.append(f"- 체력: {changes.health_change:+d}")
    if changes.coins_change:
        lines.append(f"- 코인: {changes.coins_change:+d}")
    if changes.exp_change:
        lines.append(f"- 경험치: {changes.exp_change:+d}")
    if changes.new_position:
        lines.append(f"- 이동: {changes.new_position}")
    if changes.killed_npc_id:
        lines.append(f"- NPC 사망: {changes.killed_npc_id}")
    if changes.new_items:
        lines.append(f"- 아이템 획득: {', '.join(changes.new_items)}")
    if changes.panic_change:
        lines.append(f"- 패닉 레벨: {changes.panic_change:+d}")

    return "\n".join(lines) if lines else "- (변경 없음)"


# ============================================
# Narrator Agent
# ============================================

class NarratorAgent:
    """
    웹소설 서술 에이전트

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
            NarratorOutput,
            method="function_calling"
        )

    async def narrate(
        self,
        player_action: str,
        game_state: GameState,
        orchestrator_decision: OrchestratorDecision,
        npc_reactions: list[str] | None = None,
    ) -> NarratorOutput:
        """
        웹소설 서술 생성

        Args:
            player_action: 플레이어 행동
            game_state: 현재 게임 상태
            orchestrator_decision: Orchestrator 판단 결과
            npc_reactions: NPC 반응 목록 (NPC Agent가 생성)

        Returns:
            NarratorOutput: 구조화된 서술 결과
        """
        # 프롬프트 생성
        prompt = create_narrator_prompt(
            player_action=player_action,
            game_state=game_state,
            orchestrator_decision=orchestrator_decision,
            npc_reactions=npc_reactions,
        )

        # LLM 호출 (Structured Output)
        messages = [
            SystemMessage(content=NARRATOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        output: NarratorOutput = await self.structured_llm.ainvoke(messages)

        return output
