"""
Agent Structured Output 모델

LLM이 반드시 이 형식으로 출력하도록 강제
-> JSON 파싱 실패 절대 없음
-> LLM이 말한 것 = DB 업데이트 보장
"""
from pydantic import BaseModel, Field


# ============================================
# Orchestrator Output (Claude Sonnet 4.5)
# ============================================

class StateChange(BaseModel):
    """
    상태 변경 명령

    Orchestrator가 판단한 결과를 구조화된 형태로 출력
    """
    # 체력/스태미나 변경
    health_change: int | None = Field(
        default=None,
        description="체력 변화량 (양수면 회복, 음수면 피해)"
    )
    stamina_change: int | None = Field(
        default=None,
        description="스태미나 변화량"
    )

    # 코인/경험치
    coins_change: int | None = Field(
        default=None,
        description="코인 변화량 (시나리오 보상 등)"
    )
    exp_change: int | None = Field(
        default=None,
        description="경험치 변화량"
    )

    # 위치 이동
    new_position: str | None = Field(
        default=None,
        description="새로운 위치 (이동 시)"
    )

    # NPC 상태 변경
    killed_npc_id: str | None = Field(
        default=None,
        description="죽인 NPC ID"
    )

    # 아이템 획득
    new_items: list[str] = Field(
        default_factory=list,
        description="획득한 아이템 이름 목록"
    )

    # 패닉 레벨 변경
    panic_change: int | None = Field(
        default=None,
        description="패닉 레벨 변화량"
    )


class OrchestratorDecision(BaseModel):
    """
    Orchestrator의 판단 결과 (Claude Sonnet 4.5 출력)

    with_structured_output으로 강제되는 출력 형식
    """
    # 1. 상황 분석
    situation_analysis: str = Field(
        description="현재 상황 분석 (플레이어 행동, NPC 반응, 시나리오 진행 등)"
    )

    # 2. 개연성 검증
    is_action_valid: bool = Field(
        description="플레이어 행동이 개연성 있는지 여부"
    )
    validation_reason: str = Field(
        description="개연성 판단 근거 (능력치, 아이템, 거리 등)"
    )

    # 3. 상태 변경 결정
    state_changes: StateChange = Field(
        description="적용할 상태 변경"
    )

    # 4. Narrator에게 전달할 지시
    narrator_instruction: str = Field(
        description="Narrator가 서술할 때 강조해야 할 포인트"
    )

    # 5. 시나리오 진행 상태
    scenario_progress: str | None = Field(
        default=None,
        description="시나리오 진행 상황 업데이트"
    )

    # 6. 다음 턴 예상
    next_turn_hint: str = Field(
        description="다음 턴에 일어날 가능성이 높은 일 (서술에는 포함 안 됨, 내부용)"
    )


# ============================================
# Narrator Output (GPT-4o)
# ============================================

class NarratorOutput(BaseModel):
    """
    Narrator의 서술 결과 (GPT-4o 출력)

    with_structured_output으로 강제되는 출력 형식
    """
    # 웹소설 스타일 서술
    narrative: str = Field(
        description="웹소설 스타일의 몰입감 있는 서술 (2-4 문단)"
    )

    # 분위기/톤
    scene_mood: str = Field(
        description="장면의 분위기 (tense, hopeful, desperate, calm 등)"
    )

    # NPC 반응 요약
    npc_reactions: list[str] = Field(
        default_factory=list,
        description="주요 NPC의 반응 요약 (각 NPC별로)"
    )

    # 제안 선택지
    suggested_choices: list[str] = Field(
        default_factory=list,
        description="플레이어에게 제안할 선택지 (Interactive 모드에서 3-4개, Auto 모드에서는 0개 가능)",
        max_length=4
    )


# ============================================
# 통합 턴 결과
# ============================================

class TurnResult(BaseModel):
    """
    한 턴의 최종 결과

    Orchestrator 판단 + Narrator 서술
    """
    turn: int

    # Orchestrator 결과
    orchestrator_decision: OrchestratorDecision

    # Narrator 서술
    narrator_output: NarratorOutput

    # 실제 적용된 상태 변경 (validation 후)
    applied_changes: StateChange

    # 검증 실패 시
    validation_failed: bool = False
    validation_error: str | None = None
