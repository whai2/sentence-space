"""
Scenario Orchestrator Agent

Claude Sonnet 4.5 기반 최상위 의사결정 에이전트
- 상황 분석 및 개연성 검증
- 상태 변경 승인/거부
- NPC 활성화 결정
- Narrator에게 서술 지시
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from domain.orv_v2.models import (
    GameState,
    ScenarioContext,
    OrchestratorDecision,
    StateChange,
)


# ============================================
# Orchestrator 프롬프트
# ============================================

ORCHESTRATOR_SYSTEM_PROMPT = """당신은 "전지적 독자 시점" 텍스트 RPG의 **시나리오 총괄 오케스트레이터**입니다.

## 핵심 역할
1. **상황 분석**: 플레이어 행동, 현재 상태, 시나리오 목표를 종합 분석
2. **개연성 검증**: 행동이 설정, 능력치, 물리 법칙에 부합하는지 검증
3. **상태 변경 결정**: 개연성 있는 상태 변경만 승인
4. **Narrator 지시**: 서술 에이전트에게 강조할 포인트 전달

## 검증 기준
### 1. 능력치 검증
- 플레이어의 근력/민첩/스탯으로 가능한 행동인가?
- 예: 근력 10으로 성인 남성 때려눕히기 → 불가능

### 2. 거리/위치 검증
- 플레이어와 대상이 같은 위치에 있는가?
- 예: 다른 객차에 있는 NPC 공격 → 불가능

### 3. 아이템/장비 검증
- 필요한 아이템을 보유하고 있는가?
- 예: 무기 없이 NPC 살해 → 어려움 (맨손은 낮은 데미지)

### 4. 시간/쿨다운 검증
- 스킬 쿨다운이 끝났는가?
- 시나리오 제한 시간은 남았는가?

### 5. 세계관 설정 검증
- "전지적 독자 시점" 세계관에 부합하는가?
- 예: 시나리오 시작 전에 성좌 후원 받기 → 불가능

## 출력 형식
반드시 구조화된 JSON 형식으로 출력하세요.
- situation_analysis: 상황 분석
- is_action_valid: true/false
- validation_reason: 검증 근거 (구체적으로)
- state_changes: 적용할 상태 변경
- narrator_instruction: Narrator에게 전달할 지시
- scenario_progress: 시나리오 진행 상황
- next_turn_hint: 다음 턴 예상

## 중요 원칙
- **개연성 우선**: 플레이어가 원하는 대로가 아니라, 설정상 가능한 대로
- **투명한 근거**: 왜 이렇게 판단했는지 명확히 기록
- **긴장감 유지**: 너무 쉽게 성공하면 재미없음, 적절한 난이도 유지
"""


def create_orchestrator_prompt(
    player_action: str,
    game_state: GameState,
    scenario_context: ScenarioContext | None,
) -> str:
    """Orchestrator 판단용 프롬프트 생성"""

    # 현재 상태 요약
    player = game_state.player
    state_summary = f"""
## 현재 게임 상태 (턴 {game_state.turn_count})

### 플레이어: {player.name}
- 레벨: {player.level}
- 체력: {player.health}/{player.max_health}
- 코인: {player.coins}
- 위치: {player.position}
- 스탯: 근력 {player.attributes.strength}, 민첩 {player.attributes.agility}, 지구력 {player.attributes.endurance}

### 인벤토리
{chr(10).join([f"- {item.name} ({item.item_type}, 데미지 {item.base_damage})" for item in player.inventory]) if player.inventory else "- (비어있음)"}

### 스킬
{chr(10).join([f"- {skill.name} Lv.{skill.level} (쿨다운: {skill.cooldown}턴)" for skill in player.skills]) if player.skills else "- (없음)"}
"""

    # 시나리오 컨텍스트
    scenario_summary = ""
    if scenario_context:
        scenario_summary = f"""
## 현재 시나리오
- 제목: {scenario_context.title} ({scenario_context.difficulty})
- 목표: {scenario_context.objective}
- 남은 시간: {scenario_context.remaining_time}턴
- 현재 단계: {scenario_context.current_phase or "알 수 없음"}
"""

        # 이전 시나리오 요약
        if scenario_context.previous_summaries:
            prev = scenario_context.previous_summaries[-1]  # 가장 최근 것만
            scenario_summary += f"""
### 이전 시나리오 요약
{prev.summary}

주요 결정:
{chr(10).join([f"- 턴 {d.turn}: {d.action} → {d.result}" for d in prev.key_decisions[:3]])}
"""

    # 전체 프롬프트
    prompt = f"""
{state_summary}

{scenario_summary}

## 플레이어 행동
{player_action}

---

위 행동을 분석하고, 개연성을 검증한 뒤, 적용할 상태 변경을 결정하세요.

**중요**:
1. 플레이어가 원하는 결과가 아니라, **설정상 가능한 결과**를 판단하세요.
2. 능력치, 아이템, 위치를 철저히 체크하세요.
3. 너무 쉽게 성공하면 재미없습니다. 적절한 난이도를 유지하세요.
"""

    return prompt


# ============================================
# Orchestrator Agent
# ============================================

class OrchestratorAgent:
    """
    시나리오 총괄 오케스트레이터

    Claude Sonnet 4.5 기반
    """

    def __init__(self, llm: ChatOpenAI):
        """
        Args:
            llm: Claude Sonnet 4.5 LLM (LLMFactory에서 생성)
        """
        self.llm = llm
        # Structured Output 강제 (function_calling 방식)
        self.structured_llm = llm.with_structured_output(
            OrchestratorDecision,
            method="function_calling"
        )

    async def decide(
        self,
        player_action: str,
        game_state: GameState,
        scenario_context: ScenarioContext | None = None,
    ) -> OrchestratorDecision:
        """
        플레이어 행동을 분석하고 판단

        Args:
            player_action: 플레이어 행동
            game_state: 현재 게임 상태
            scenario_context: 시나리오 컨텍스트

        Returns:
            OrchestratorDecision: 구조화된 판단 결과
        """
        # 프롬프트 생성
        prompt = create_orchestrator_prompt(
            player_action=player_action,
            game_state=game_state,
            scenario_context=scenario_context,
        )

        # LLM 호출 (Structured Output)
        messages = [
            SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        decision: OrchestratorDecision = await self.structured_llm.ainvoke(messages)

        return decision

    def validate_state_changes(
        self,
        changes: StateChange,
        game_state: GameState,
    ) -> tuple[bool, str | None]:
        """
        상태 변경 추가 검증 (이중 안전장치)

        Orchestrator가 판단했지만, 한번 더 체크

        Returns:
            (is_valid, error_message)
        """
        player = game_state.player

        # 체력 범위 체크
        if changes.health_change:
            new_health = player.health + changes.health_change
            if new_health > player.max_health:
                return False, f"체력이 최대치를 초과합니다 ({new_health} > {player.max_health})"
            # 음수는 허용 (죽음)

        # 코인 음수 방지
        if changes.coins_change:
            new_coins = player.coins + changes.coins_change
            if new_coins < 0:
                return False, f"코인이 부족합니다 (현재: {player.coins}, 변화: {changes.coins_change})"

        # 위치 이동 검증 (간단히 체크)
        if changes.new_position:
            valid_positions = [
                "3호선_객차_1", "3호선_객차_2", "3호선_객차_3",
                "3호선_객차_4", "3호선_객차_5", "3호선_객차_6",
                "3호선_운전실", "지하철_플랫폼"
            ]
            if changes.new_position not in valid_positions:
                return False, f"존재하지 않는 위치입니다: {changes.new_position}"

        return True, None
