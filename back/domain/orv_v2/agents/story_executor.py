"""
Story Executor Agent

각 턴마다 스토리 플랜을 확인하고 다음에 일어나야 할 이벤트를 결정
"""
from pydantic import BaseModel, Field
from domain.orv_v2.models.story_plan import (
    StoryPlan,
    StoryProgress,
    StoryPhase,
    StoryEvent
)
from domain.orv_v2.models import GameState


# ============================================
# Executor Output
# ============================================

class ExecutorGuidance(BaseModel):
    """
    Executor가 Auto-Narrator에게 제공하는 가이드

    현재 단계와 다음 이벤트 정보
    """
    current_phase: StoryPhase
    next_event: StoryEvent | None
    narrative_guidance: str = Field(
        description="Auto-Narrator를 위한 서술 가이드"
    )
    is_phase_transition: bool = Field(
        default=False,
        description="페이즈 전환 시점인가?"
    )


# ============================================
# Story Executor Agent
# ============================================

class StoryExecutorAgent:
    """
    스토리 실행 에이전트

    각 턴마다 스토리 플랜을 참조하여 진행 상황 관리
    """

    def __init__(self):
        """에이전트 초기화 (LLM 불필요)"""
        pass

    def get_current_guidance(
        self,
        story_plan: StoryPlan,
        story_progress: StoryProgress,
        game_state: GameState
    ) -> ExecutorGuidance:
        """
        현재 턴의 가이던스 생성

        Args:
            story_plan: 전체 스토리 플랜
            story_progress: 현재 진행 상황
            game_state: 게임 상태

        Returns:
            ExecutorGuidance: Auto-Narrator를 위한 가이드
        """
        current_turn = game_state.turn_count

        # 1. 현재 Phase 찾기
        current_phase = self._find_current_phase(story_plan, current_turn)

        if not current_phase:
            # 플랜에 없는 턴 (플레이어가 크게 벗어남)
            return self._create_fallback_guidance(story_progress)

        # 2. 다음 이벤트 결정
        next_event = self._find_next_event(
            current_phase,
            story_progress.completed_events
        )

        # 3. Phase 전환 체크
        is_phase_transition = self._check_phase_transition(
            current_phase,
            current_turn,
            story_plan
        )

        # 4. 서술 가이드 생성
        narrative_guidance = self._create_narrative_guidance(
            current_phase=current_phase,
            next_event=next_event,
            is_phase_transition=is_phase_transition,
            current_turn=current_turn
        )

        return ExecutorGuidance(
            current_phase=current_phase,
            next_event=next_event,
            narrative_guidance=narrative_guidance,
            is_phase_transition=is_phase_transition
        )

    def update_progress(
        self,
        story_progress: StoryProgress,
        completed_event_id: str | None,
        new_phase_id: str | None = None
    ) -> StoryProgress:
        """
        진행 상황 업데이트

        Args:
            story_progress: 현재 진행 상황
            completed_event_id: 완료된 이벤트 ID
            new_phase_id: 새로운 Phase ID (전환 시)

        Returns:
            업데이트된 StoryProgress
        """
        if completed_event_id:
            story_progress.completed_events.append(completed_event_id)

        if new_phase_id:
            story_progress.current_phase_id = new_phase_id

        story_progress.current_turn += 1

        return story_progress

    # ============================================
    # Private Methods
    # ============================================

    def _find_current_phase(
        self,
        story_plan: StoryPlan,
        current_turn: int
    ) -> StoryPhase | None:
        """현재 턴에 해당하는 Phase 찾기"""
        for phase in story_plan.phases:
            if phase.target_turn_start <= current_turn <= phase.target_turn_end:
                return phase

        # 범위를 벗어나면 가장 가까운 Phase 반환
        if current_turn < story_plan.phases[0].target_turn_start:
            return story_plan.phases[0]
        elif current_turn > story_plan.phases[-1].target_turn_end:
            return story_plan.phases[-1]

        return None

    def _find_next_event(
        self,
        current_phase: StoryPhase,
        completed_events: list[str]
    ) -> StoryEvent | None:
        """다음에 일어나야 할 이벤트 찾기"""
        for event in current_phase.events:
            if event.event_id not in completed_events:
                return event
        return None

    def _check_phase_transition(
        self,
        current_phase: StoryPhase,
        current_turn: int,
        story_plan: StoryPlan
    ) -> bool:
        """Phase 전환 시점인지 체크"""
        # 현재 Phase의 마지막 턴 근처
        if current_turn >= current_phase.target_turn_end - 1:
            return True
        return False

    def _create_narrative_guidance(
        self,
        current_phase: StoryPhase,
        next_event: StoryEvent | None,
        is_phase_transition: bool,
        current_turn: int
    ) -> str:
        """Auto-Narrator를 위한 서술 가이드 생성"""
        guidance_parts = []

        # Phase 정보
        guidance_parts.append(f"현재 단계: {current_phase.phase_name}")
        guidance_parts.append(f"단계 설명: {current_phase.description}")
        guidance_parts.append(f"서술 톤: {current_phase.narrative_tone}")

        # 다음 이벤트
        if next_event:
            guidance_parts.append(f"\n다음 이벤트: {next_event.description}")
            if next_event.narrative_hints:
                guidance_parts.append("서술 힌트:")
                for hint in next_event.narrative_hints:
                    guidance_parts.append(f"  - {hint}")

        # Phase 전환
        if is_phase_transition:
            guidance_parts.append("\n⚠️ 곧 다음 단계로 전환됩니다. 이 단계를 마무리하는 분위기로 서술하세요.")

        return "\n".join(guidance_parts)

    def _create_fallback_guidance(
        self,
        story_progress: StoryProgress
    ) -> ExecutorGuidance:
        """플랜 이탈 시 대체 가이던스"""
        fallback_phase = StoryPhase(
            phase_id="fallback",
            phase_name="자유 진행",
            description="플레이어가 계획에서 벗어났습니다. 자연스럽게 대응하세요.",
            target_turn_start=0,
            target_turn_end=999,
            completion_condition="자유 진행",
            narrative_tone="calm",
            events=[]
        )

        return ExecutorGuidance(
            current_phase=fallback_phase,
            next_event=None,
            narrative_guidance="플레이어의 자유로운 선택에 따라 자연스럽게 이야기를 전개하세요.",
            is_phase_transition=False
        )
