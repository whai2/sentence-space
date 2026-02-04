"""
StoryManager - 스토리 아크, 복선, 긴장 곡선 관리

Director와 함께 장기적 스토리텔링을 지원합니다.
"""

import uuid
from typing import Optional

from domain.orv.model import (
    GameState,
    StoryPhase,
    StoryArc,
    StoryBeat,
    PlotPoint,
    PlotPointType,
    PlotPointStatus,
    TensionLevel,
    StoryContext,
    PHASE_TONE_GUIDANCE,
    PHASE_TARGET_TENSION,
)


class StoryManager:
    """
    스토리 아크, 복선, 긴장 곡선을 관리하는 서비스.

    주요 기능:
    - 스토리 아크 생성 및 관리
    - 스토리 단계 진행 체크 및 전환
    - 복선 심기/회수
    - 긴장 곡선 관리
    - Director용 스토리 컨텍스트 생성
    """

    def __init__(self) -> None:
        # session_id -> StoryArc
        self._arcs: dict[str, StoryArc] = {}

    # ========================================================================
    # 아크 관리
    # ========================================================================

    def create_arc(
        self,
        session_id: str,
        title: str,
        description: str,
        start_turn: int = 0,
        initial_plot_points: Optional[list[PlotPoint]] = None,
    ) -> StoryArc:
        """새 스토리 아크 생성"""
        arc = StoryArc(
            arc_id=str(uuid.uuid4()),
            title=title,
            description=description,
            start_turn=start_turn,
            current_phase=StoryPhase.EXPOSITION,
        )

        # 목표 긴장도 초기화
        arc.tension_curve.target_tension = PHASE_TARGET_TENSION[StoryPhase.EXPOSITION]

        # 초기 복선 추가
        if initial_plot_points:
            for pp in initial_plot_points:
                arc.add_plot_point(pp)

        self._arcs[session_id] = arc
        return arc

    def get_arc(self, session_id: str) -> Optional[StoryArc]:
        """세션의 활성 아크 반환"""
        return self._arcs.get(session_id)

    def set_arc(self, session_id: str, arc: StoryArc) -> None:
        """아크 설정 (로드 시 사용)"""
        self._arcs[session_id] = arc

    # ========================================================================
    # 단계 진행
    # ========================================================================

    def check_phase_progression(
        self,
        session_id: str,
        game_state: GameState,
        player_action: str,
        npc_reactions: list[str],
    ) -> tuple[bool, Optional[StoryPhase]]:
        """
        스토리 단계 진행 여부 체크.

        Returns:
            (should_advance, new_phase)
        """
        arc = self._arcs.get(session_id)
        if arc is None or arc.is_complete:
            return False, None

        current_phase = arc.current_phase
        current_turn = game_state.turn_count

        # 단계별 진행 조건 체크
        should_advance = self._check_phase_conditions(
            current_phase, current_turn, arc.start_turn, game_state, player_action
        )

        if should_advance:
            new_phase = arc.advance_phase()
            return True, new_phase

        return False, None

    def _check_phase_conditions(
        self,
        phase: StoryPhase,
        current_turn: int,
        start_turn: int,
        game_state: GameState,
        player_action: str,
    ) -> bool:
        """단계별 진행 조건 체크"""
        turns_in_arc = current_turn - start_turn

        # 기본 턴 수 기반 조건 (최소 턴)
        min_turns_per_phase = {
            StoryPhase.EXPOSITION: 2,
            StoryPhase.INCITING_INCIDENT: 1,
            StoryPhase.RISING_ACTION: 3,
            StoryPhase.MIDPOINT: 2,
            StoryPhase.COMPLICATIONS: 3,
            StoryPhase.CRISIS: 2,
            StoryPhase.CLIMAX: 2,
            StoryPhase.FALLING_ACTION: 1,
            StoryPhase.RESOLUTION: 1,
        }

        # 현재 단계에서 최소 턴을 채웠는지 확인
        # (간단한 구현 - 실제로는 각 단계 시작 턴을 추적해야 함)
        phase_min = min_turns_per_phase.get(phase, 2)

        # 현재 시나리오 상태 확인
        current_scenario = game_state.current_scenario
        scenario_started = current_scenario is not None
        scenario_complete = game_state.scenario_cleared
        first_kill = game_state.first_kill_completed

        if phase == StoryPhase.EXPOSITION:
            # 시나리오가 시작되면 INCITING_INCIDENT로
            if scenario_started and turns_in_arc >= phase_min:
                return True

        elif phase == StoryPhase.INCITING_INCIDENT:
            # 첫 번째 주요 충돌 후 RISING_ACTION으로
            if turns_in_arc >= phase_min:
                return True

        elif phase == StoryPhase.RISING_ACTION:
            # 턴 수 기반 또는 첫 킬 완료 시 MIDPOINT로
            if first_kill or turns_in_arc >= phase_min + 3:
                return True

        elif phase == StoryPhase.MIDPOINT:
            # 추가 턴 후 COMPLICATIONS로
            if turns_in_arc >= phase_min:
                return True

        elif phase == StoryPhase.COMPLICATIONS:
            # 추가 턴 후 CRISIS로
            if turns_in_arc >= phase_min:
                return True

        elif phase == StoryPhase.CRISIS:
            # 시나리오 완료 직전 또는 턴 수 기반
            if turns_in_arc >= phase_min + 2:
                return True

        elif phase == StoryPhase.CLIMAX:
            # 시나리오 완료되면 FALLING_ACTION으로
            if scenario_complete:
                return True

        elif phase == StoryPhase.FALLING_ACTION:
            # CLIMAX 후 2턴이면 RESOLUTION으로
            if turns_in_arc >= phase_min:
                return True

        return False

    def advance_phase_manually(
        self, session_id: str
    ) -> Optional[StoryPhase]:
        """수동으로 단계 진행"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return None
        return arc.advance_phase()

    # ========================================================================
    # 복선 관리
    # ========================================================================

    def plant_plot_point(
        self,
        session_id: str,
        point_type: PlotPointType,
        seed_description: str,
        seed_narrative: str,
        payoff_description: str,
        turn: int,
        importance: int = 5,
        min_turns: int = 3,
        max_turns: int = 20,
        related_npc_ids: Optional[list[str]] = None,
        related_location: Optional[str] = None,
        related_item_ids: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
    ) -> Optional[PlotPoint]:
        """복선 심기"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return None

        plot_point = PlotPoint(
            plot_point_id=str(uuid.uuid4()),
            point_type=point_type,
            seed_description=seed_description,
            seed_narrative=seed_narrative,
            payoff_description=payoff_description,
            turn_planted=turn,
            min_turns_before_payoff=min_turns,
            max_turns_before_payoff=max_turns,
            importance=importance,
            related_npc_ids=related_npc_ids or [],
            related_location=related_location,
            related_item_ids=related_item_ids or [],
            keywords=keywords or [],
        )

        arc.add_plot_point(plot_point)
        return plot_point

    def get_active_plot_points(self, session_id: str) -> list[PlotPoint]:
        """활성 복선 목록"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return []
        return arc.get_active_plot_points()

    def get_ready_payoffs(
        self, session_id: str, current_turn: int
    ) -> list[PlotPoint]:
        """회수 준비된 복선 목록"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return []
        return arc.get_ready_payoffs(current_turn)

    def get_overdue_plot_points(
        self, session_id: str, current_turn: int
    ) -> list[PlotPoint]:
        """회수 기한 초과된 복선 목록"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return []
        return arc.get_overdue_plot_points(current_turn)

    def check_payoff_triggers(
        self,
        session_id: str,
        game_state: GameState,
        player_action: str,
    ) -> list[PlotPoint]:
        """
        플레이어 행동에서 복선 회수 트리거 체크.

        키워드 매칭으로 관련 복선을 찾습니다.
        """
        arc = self._arcs.get(session_id)
        if arc is None:
            return []

        current_turn = game_state.turn_count
        ready_payoffs = arc.get_ready_payoffs(current_turn)

        # 플레이어 행동에서 키워드 추출 (간단한 구현)
        action_words = set(player_action.lower().split())
        current_location = game_state.player.position

        triggered = []
        for pp in ready_payoffs:
            # 키워드 매칭
            pp_keywords = set(kw.lower() for kw in pp.keywords)
            if action_words & pp_keywords:
                triggered.append(pp)
                continue

            # 위치 매칭
            if pp.related_location and pp.related_location == current_location:
                if any(kw in player_action for kw in pp.keywords):
                    triggered.append(pp)
                    continue

            # 기한 초과된 중요 복선은 강제 트리거 후보
            if pp.is_overdue(current_turn) and pp.importance >= 7:
                triggered.append(pp)

        return triggered

    def update_plot_point_status(
        self,
        session_id: str,
        plot_point_id: str,
        new_status: PlotPointStatus,
    ) -> Optional[PlotPoint]:
        """복선 상태 업데이트"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return None

        for pp in arc.plot_points:
            if pp.plot_point_id == plot_point_id:
                pp.status = new_status
                return pp
        return None

    def resolve_plot_point(
        self,
        session_id: str,
        plot_point_id: str,
        payoff_narrative: str,
        turn: int,
    ) -> Optional[PlotPoint]:
        """복선 회수"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return None
        return arc.resolve_plot_point(plot_point_id, payoff_narrative, turn)

    # ========================================================================
    # 긴장 곡선
    # ========================================================================

    def calculate_tension_adjustment(
        self,
        session_id: str,
        game_state: GameState,
        player_action: str,
        npc_reactions: list[str],
    ) -> int:
        """
        긴장도 조정값 계산.

        다양한 요소를 고려하여 긴장도 변화량 결정.
        """
        adjustment = 0

        # 플레이어 행동 분석
        action_lower = player_action.lower()

        # 전투/위험 관련 키워드
        danger_keywords = ["공격", "싸우", "도망", "위험", "죽", "피", "전투"]
        if any(kw in action_lower for kw in danger_keywords):
            adjustment += 10

        # 휴식/안전 관련 키워드
        calm_keywords = ["휴식", "쉬", "안전", "대화", "살펴"]
        if any(kw in action_lower for kw in calm_keywords):
            adjustment -= 5

        # 시나리오 상태 반영
        scenario_started = game_state.current_scenario is not None
        scenario_complete = game_state.scenario_cleared
        if scenario_started and not scenario_complete:
            # 시나리오 진행 중에는 기본 긴장 유지
            adjustment += 2

        # 활성 NPC 수에 따른 조정
        active_npcs = len([n for n in game_state.npcs if n.is_alive])
        if active_npcs > 5:
            adjustment += 3

        # 최대 변화량 제한
        return max(-20, min(20, adjustment))

    def update_tension(
        self,
        session_id: str,
        adjustment: int,
        turn: int,
    ) -> Optional[TensionLevel]:
        """긴장도 업데이트"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return None

        new_tension = arc.tension_curve.current_tension + adjustment
        arc.tension_curve.update(new_tension, turn)
        return arc.tension_curve.get_level()

    def get_pacing_guidance(self, session_id: str) -> str:
        """페이싱 가이드 반환"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return ""
        return arc.tension_curve.get_pacing_guidance()

    # ========================================================================
    # 스토리 비트
    # ========================================================================

    def add_story_beat(
        self,
        session_id: str,
        turn: int,
        summary: str,
        significance: str,
        involved_npc_ids: Optional[list[str]] = None,
        triggered_plot_points: Optional[list[str]] = None,
        resolved_plot_points: Optional[list[str]] = None,
        tension_change: int = 0,
    ) -> Optional[StoryBeat]:
        """스토리 비트 추가"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return None

        beat = StoryBeat(
            beat_id=str(uuid.uuid4()),
            turn=turn,
            phase=arc.current_phase,
            summary=summary,
            significance=significance,
            involved_npc_ids=involved_npc_ids or [],
            triggered_plot_points=triggered_plot_points or [],
            resolved_plot_points=resolved_plot_points or [],
            tension_change=tension_change,
        )

        arc.add_beat(beat)
        return beat

    # ========================================================================
    # Director용 컨텍스트
    # ========================================================================

    def get_narrative_context(
        self,
        session_id: str,
        game_state: GameState,
    ) -> Optional[StoryContext]:
        """Director용 스토리 컨텍스트 생성"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return None

        current_turn = game_state.turn_count

        return StoryContext(
            current_phase=arc.current_phase,
            phase_tone=arc.get_tone_guidance(),
            tension_level=arc.tension_curve.get_level(),
            tension_value=arc.tension_curve.current_tension,
            pacing_guidance=arc.tension_curve.get_pacing_guidance(),
            active_plot_points=arc.get_active_plot_points(),
            ready_payoffs=arc.get_ready_payoffs(current_turn),
            overdue_plot_points=arc.get_overdue_plot_points(current_turn),
            recent_beats=arc.beats[-5:] if arc.beats else [],
        )

    # ========================================================================
    # 영속성 지원
    # ========================================================================

    def export_arc(self, session_id: str) -> Optional[dict]:
        """아크를 dict로 내보내기 (저장용)"""
        arc = self._arcs.get(session_id)
        if arc is None:
            return None
        return arc.model_dump()

    def import_arc(self, session_id: str, arc_data: dict) -> StoryArc:
        """dict에서 아크 로드"""
        arc = StoryArc.model_validate(arc_data)
        self._arcs[session_id] = arc
        return arc
