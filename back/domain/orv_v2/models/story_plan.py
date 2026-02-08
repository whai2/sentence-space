"""
스토리 플랜 모델 (Plan-and-Execute)

시나리오 시작 시 전체 스토리 구조를 미리 계획하고,
각 턴마다 이 계획에 따라 진행
"""
from pydantic import BaseModel, Field
from enum import Enum


# ============================================
# Story Phase & Event
# ============================================

class StoryEvent(BaseModel):
    """스토리 이벤트"""
    event_id: str
    description: str
    key_characters: list[str] = Field(default_factory=list)
    trigger_condition: str | None = None  # "turn >= 3", "npc_death", etc.
    narrative_hints: list[str] = Field(default_factory=list)


class StoryPhase(BaseModel):
    """스토리 진행 단계"""
    phase_id: str
    phase_name: str
    description: str

    # 목표 턴 범위
    target_turn_start: int
    target_turn_end: int

    # 이 단계에서 일어나야 할 이벤트들
    events: list[StoryEvent] = Field(default_factory=list)

    # 다음 단계로 넘어가는 조건
    completion_condition: str

    # 서술 톤
    narrative_tone: str = "tense"  # tense, calm, hopeful, desperate


# ============================================
# Story Plan
# ============================================

class StoryPlan(BaseModel):
    """
    시나리오 전체 스토리 플랜

    Planner Agent가 시나리오 시작 시 생성
    MongoDB에 저장되어 각 턴마다 참조
    """
    session_id: str
    scenario_id: str

    # 전체 스토리 아크
    phases: list[StoryPhase] = Field(default_factory=list)

    # 주요 선택지/분기점
    critical_choices: list[dict] = Field(default_factory=list)

    # 플랜 생성 정보
    created_at_turn: int


# ============================================
# Story Progress
# ============================================

class StoryProgress(BaseModel):
    """
    현재 스토리 진행 상황

    MongoDB game_sessions에 embedded document로 저장
    """
    current_phase_id: str
    current_phase_name: str
    current_turn: int

    # 완료된 이벤트
    completed_events: list[str] = Field(default_factory=list)

    # 다음에 일어나야 할 이벤트
    next_event: StoryEvent | None = None

    # 플레이어가 벗어난 정도 (0-10)
    deviation_level: int = 0


# ============================================
# Planner Output
# ============================================

class PlannerOutput(BaseModel):
    """
    Planner Agent의 출력

    시나리오 시작 시 생성되는 전체 스토리 플랜
    """
    story_plan: StoryPlan
    opening_narrative: str | None = None  # 시작 서술 (optional - Haiku 호환성)
    initial_choices: list[str] = Field(default_factory=list)
