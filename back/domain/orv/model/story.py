"""
스토리 비트 시스템 모델

3막 구조 + 긴장 곡선 + 복선/회수 시스템을 통한 장기적 스토리텔링 지원.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# 스토리 단계 (3막 구조)
# ============================================================================


class StoryPhase(str, Enum):
    """
    3막 구조 기반 스토리 단계.

    Act 1: 설정
    - EXPOSITION: 세계관 소개, 캐릭터 설정
    - INCITING_INCIDENT: 이야기 시작 계기

    Act 2: 대립
    - RISING_ACTION: 긴장 고조, 복잡성 증가
    - MIDPOINT: 주요 반전 또는 전환
    - COMPLICATIONS: 상황 악화
    - CRISIS: 클라이맥스 직전 최악의 순간

    Act 3: 해결
    - CLIMAX: 최종 대결
    - FALLING_ACTION: 결과 정리
    - RESOLUTION: 새로운 균형
    """

    # Act 1: 설정
    EXPOSITION = "exposition"
    INCITING_INCIDENT = "inciting_incident"

    # Act 2: 대립
    RISING_ACTION = "rising_action"
    MIDPOINT = "midpoint"
    COMPLICATIONS = "complications"
    CRISIS = "crisis"

    # Act 3: 해결
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"


# 단계별 기본 톤 가이드
PHASE_TONE_GUIDANCE: dict[StoryPhase, str] = {
    StoryPhase.EXPOSITION: "세계관과 캐릭터를 자연스럽게 소개. 호기심 유발.",
    StoryPhase.INCITING_INCIDENT: "긴박한 사건 발생. 일상의 균형이 깨짐.",
    StoryPhase.RISING_ACTION: "긴장 고조. 새로운 도전과 장애물 등장.",
    StoryPhase.MIDPOINT: "중요한 반전 또는 깨달음. 이야기의 방향 전환.",
    StoryPhase.COMPLICATIONS: "상황 악화. 희망이 위협받음.",
    StoryPhase.CRISIS: "최악의 순간. 모든 것이 불가능해 보임.",
    StoryPhase.CLIMAX: "최종 대결. 모든 긴장의 정점.",
    StoryPhase.FALLING_ACTION: "결과 정리. 승리/패배의 여파.",
    StoryPhase.RESOLUTION: "새로운 균형. 변화된 세계/캐릭터.",
}

# 단계 순서 (진행 방향 검증용)
PHASE_ORDER = list(StoryPhase)


# ============================================================================
# 복선/회수 시스템
# ============================================================================


class PlotPointType(str, Enum):
    """복선 타입"""

    FORESHADOWING = "foreshadowing"  # 미래 이벤트 암시
    CHEKHOV_GUN = "chekhov_gun"  # 나중에 반드시 사용될 아이템/디테일
    CHARACTER_SEED = "character_seed"  # 캐릭터 특성/배경 힌트
    THEME_ECHO = "theme_echo"  # 주제 강화
    MYSTERY = "mystery"  # 미해결 질문


class PlotPointStatus(str, Enum):
    """복선 상태"""

    PLANTED = "planted"  # 심어짐 (아직 눈에 띄지 않음)
    NOTICED = "noticed"  # 인지됨 (독자/플레이어가 알아챔)
    DEVELOPING = "developing"  # 발전 중 (추가 힌트 제공)
    PAYOFF_READY = "payoff_ready"  # 회수 준비됨
    RESOLVED = "resolved"  # 회수 완료


class PlotPoint(BaseModel):
    """
    단일 복선/회수 포인트.

    복선이 심어지고 회수되기까지의 전체 생애주기를 추적.
    """

    plot_point_id: str
    point_type: PlotPointType

    # 복선 내용
    seed_description: str  # 심어진 내용 (내부 기록용)
    seed_narrative: str  # 실제 서술된 문장
    payoff_description: str  # 회수될 내용 (내부 기록용)
    payoff_narrative: Optional[str] = None  # 회수 시 서술된 문장

    # 타이밍
    turn_planted: int
    turn_resolved: Optional[int] = None
    min_turns_before_payoff: int = Field(default=3, ge=1)
    max_turns_before_payoff: int = Field(default=20, ge=1)

    # 상태
    status: PlotPointStatus = PlotPointStatus.PLANTED

    # 중요도 (1-10, 높을수록 중요)
    importance: int = Field(default=5, ge=1, le=10)

    # 연관 요소
    related_npc_ids: list[str] = Field(default_factory=list)
    related_location: Optional[str] = None
    related_item_ids: list[str] = Field(default_factory=list)

    # 키워드 (검색용)
    keywords: list[str] = Field(default_factory=list)

    def can_payoff(self, current_turn: int) -> bool:
        """회수 가능 여부 확인"""
        if self.status == PlotPointStatus.RESOLVED:
            return False
        turns_since_planted = current_turn - self.turn_planted
        return turns_since_planted >= self.min_turns_before_payoff

    def should_payoff_soon(self, current_turn: int) -> bool:
        """곧 회수해야 하는지 확인 (max 턴에 근접)"""
        if self.status == PlotPointStatus.RESOLVED:
            return False
        turns_since_planted = current_turn - self.turn_planted
        return turns_since_planted >= self.max_turns_before_payoff - 3

    def is_overdue(self, current_turn: int) -> bool:
        """회수 기한 초과 여부"""
        if self.status == PlotPointStatus.RESOLVED:
            return False
        turns_since_planted = current_turn - self.turn_planted
        return turns_since_planted > self.max_turns_before_payoff


# ============================================================================
# 스토리 비트
# ============================================================================


class StoryBeat(BaseModel):
    """
    스토리의 핵심 이벤트 기록.

    각 중요한 순간을 기록하여 스토리 흐름을 추적.
    """

    beat_id: str
    turn: int
    phase: StoryPhase

    # 내용
    summary: str  # 무슨 일이 일어났는지
    significance: str  # 왜 중요한지

    # 관련 요소
    involved_npc_ids: list[str] = Field(default_factory=list)
    triggered_plot_points: list[str] = Field(default_factory=list)  # plot_point_id 목록
    resolved_plot_points: list[str] = Field(default_factory=list)

    # 감정/긴장
    tension_change: int = Field(default=0, ge=-30, le=30)  # 긴장도 변화량


# ============================================================================
# 긴장 곡선
# ============================================================================


class TensionLevel(str, Enum):
    """긴장 수준"""

    CALM = "calm"  # 0-20: 회복/휴식
    LOW = "low"  # 21-40: 가벼운 긴장
    MODERATE = "moderate"  # 41-60: 표준 진행
    HIGH = "high"  # 61-80: 긴박한 순간
    CRITICAL = "critical"  # 81-100: 최고조 드라마


def get_tension_level(tension: int) -> TensionLevel:
    """긴장도 값에서 레벨 반환"""
    if tension <= 20:
        return TensionLevel.CALM
    elif tension <= 40:
        return TensionLevel.LOW
    elif tension <= 60:
        return TensionLevel.MODERATE
    elif tension <= 80:
        return TensionLevel.HIGH
    else:
        return TensionLevel.CRITICAL


class TensionCurve(BaseModel):
    """
    긴장 곡선 관리.

    스토리 전반의 긴장도 흐름을 추적하고 페이싱 가이드 제공.
    """

    current_tension: int = Field(default=30, ge=0, le=100)
    target_tension: int = Field(default=50, ge=0, le=100)  # 현재 단계의 목표 긴장도

    # 히스토리: (turn, tension_value)
    tension_history: list[tuple[int, int]] = Field(default_factory=list)

    # 페이싱 추적
    turns_at_high_tension: int = Field(default=0, ge=0)  # HIGH/CRITICAL 유지 턴 수
    turns_at_low_tension: int = Field(default=0, ge=0)  # CALM 유지 턴 수

    def get_level(self) -> TensionLevel:
        """현재 긴장 수준"""
        return get_tension_level(self.current_tension)

    def update(self, new_tension: int, turn: int) -> None:
        """긴장도 업데이트 및 히스토리 기록"""
        self.current_tension = max(0, min(100, new_tension))
        self.tension_history.append((turn, self.current_tension))

        # 페이싱 카운터 업데이트
        level = self.get_level()
        if level in (TensionLevel.HIGH, TensionLevel.CRITICAL):
            self.turns_at_high_tension += 1
            self.turns_at_low_tension = 0
        elif level == TensionLevel.CALM:
            self.turns_at_low_tension += 1
            self.turns_at_high_tension = 0
        else:
            self.turns_at_high_tension = 0
            self.turns_at_low_tension = 0

    def needs_relief(self) -> bool:
        """숨 돌릴 틈이 필요한지 (5턴 이상 HIGH/CRITICAL)"""
        return self.turns_at_high_tension >= 5

    def needs_escalation(self) -> bool:
        """사건이 필요한지 (3턴 이상 CALM)"""
        return self.turns_at_low_tension >= 3

    def get_pacing_guidance(self) -> str:
        """페이싱 가이드 반환"""
        if self.needs_relief():
            return "긴장 완화 필요: 잠시 숨 돌릴 수 있는 순간을 만들어주세요."
        elif self.needs_escalation():
            return "긴장 상승 필요: 새로운 사건이나 위협을 도입해주세요."
        elif self.current_tension < self.target_tension - 20:
            return "목표 긴장도보다 낮음: 점진적으로 긴장을 높여주세요."
        elif self.current_tension > self.target_tension + 20:
            return "목표 긴장도보다 높음: 잠시 완급 조절이 필요합니다."
        else:
            return "적절한 페이싱: 현재 흐름을 유지하세요."


# 단계별 목표 긴장도
PHASE_TARGET_TENSION: dict[StoryPhase, int] = {
    StoryPhase.EXPOSITION: 25,
    StoryPhase.INCITING_INCIDENT: 50,
    StoryPhase.RISING_ACTION: 55,
    StoryPhase.MIDPOINT: 65,
    StoryPhase.COMPLICATIONS: 70,
    StoryPhase.CRISIS: 85,
    StoryPhase.CLIMAX: 95,
    StoryPhase.FALLING_ACTION: 50,
    StoryPhase.RESOLUTION: 20,
}


# ============================================================================
# 스토리 아크
# ============================================================================


class StoryArc(BaseModel):
    """
    하나의 스토리 아크 (시작부터 끝까지).

    여러 아크를 연결하여 더 큰 이야기를 구성할 수 있음.
    """

    arc_id: str
    title: str
    description: str

    # 진행 상태
    current_phase: StoryPhase = StoryPhase.EXPOSITION
    start_turn: int = 0
    end_turn: Optional[int] = None
    is_complete: bool = False

    # 구성 요소
    beats: list[StoryBeat] = Field(default_factory=list)
    plot_points: list[PlotPoint] = Field(default_factory=list)
    tension_curve: TensionCurve = Field(default_factory=TensionCurve)

    # 단계별 톤 가이드 (기본값 오버라이드 가능)
    custom_tone_guidance: dict[str, str] = Field(default_factory=dict)

    def get_tone_guidance(self) -> str:
        """현재 단계의 톤 가이드 반환"""
        phase_key = self.current_phase.value
        if phase_key in self.custom_tone_guidance:
            return self.custom_tone_guidance[phase_key]
        return PHASE_TONE_GUIDANCE.get(self.current_phase, "")

    def get_active_plot_points(self) -> list[PlotPoint]:
        """활성 상태의 복선 목록"""
        return [
            pp
            for pp in self.plot_points
            if pp.status != PlotPointStatus.RESOLVED
        ]

    def get_ready_payoffs(self, current_turn: int) -> list[PlotPoint]:
        """회수 준비된 복선 목록"""
        return [
            pp
            for pp in self.plot_points
            if pp.can_payoff(current_turn) and pp.status != PlotPointStatus.RESOLVED
        ]

    def get_overdue_plot_points(self, current_turn: int) -> list[PlotPoint]:
        """회수 기한 초과된 복선 목록"""
        return [
            pp
            for pp in self.plot_points
            if pp.is_overdue(current_turn)
        ]

    def advance_phase(self) -> Optional[StoryPhase]:
        """다음 단계로 진행. 이미 마지막이면 None 반환."""
        current_idx = PHASE_ORDER.index(self.current_phase)
        if current_idx < len(PHASE_ORDER) - 1:
            self.current_phase = PHASE_ORDER[current_idx + 1]
            # 목표 긴장도 업데이트
            self.tension_curve.target_tension = PHASE_TARGET_TENSION[self.current_phase]
            return self.current_phase
        else:
            self.is_complete = True
            return None

    def add_beat(self, beat: StoryBeat) -> None:
        """스토리 비트 추가"""
        self.beats.append(beat)

    def add_plot_point(self, plot_point: PlotPoint) -> None:
        """복선 추가"""
        self.plot_points.append(plot_point)

    def resolve_plot_point(
        self, plot_point_id: str, payoff_narrative: str, turn: int
    ) -> Optional[PlotPoint]:
        """복선 회수"""
        for pp in self.plot_points:
            if pp.plot_point_id == plot_point_id:
                pp.status = PlotPointStatus.RESOLVED
                pp.payoff_narrative = payoff_narrative
                pp.turn_resolved = turn
                return pp
        return None


# ============================================================================
# 스토리 컨텍스트 (Director용)
# ============================================================================


class StoryContext(BaseModel):
    """
    Director에게 전달할 스토리 컨텍스트.

    현재 스토리 상태를 요약하여 의사결정에 활용.
    """

    # 현재 단계
    current_phase: StoryPhase
    phase_tone: str

    # 긴장도
    tension_level: TensionLevel
    tension_value: int
    pacing_guidance: str

    # 복선
    active_plot_points: list[PlotPoint]
    ready_payoffs: list[PlotPoint]
    overdue_plot_points: list[PlotPoint]

    # 최근 비트
    recent_beats: list[StoryBeat]  # 최근 3-5개

    def to_prompt_context(self) -> str:
        """프롬프트용 텍스트 생성"""
        lines = [
            "## 스토리 컨텍스트",
            "",
            f"**현재 이야기 단계**: {self.current_phase.value}",
            f"**단계 톤**: {self.phase_tone}",
            f"**긴장도**: {self.tension_level.value} ({self.tension_value}/100)",
            f"**페이싱**: {self.pacing_guidance}",
            "",
        ]

        if self.active_plot_points:
            lines.append("### 활성 복선")
            for pp in self.active_plot_points:
                status_marker = ""
                if pp in self.ready_payoffs:
                    status_marker = " [회수 가능]"
                if pp in self.overdue_plot_points:
                    status_marker = " [회수 필요!]"
                lines.append(
                    f"- [{pp.point_type.value}] {pp.seed_description} "
                    f"(중요도: {pp.importance}){status_marker}"
                )
            lines.append("")

        if self.ready_payoffs:
            lines.append("### 회수 준비된 복선")
            for pp in self.ready_payoffs:
                lines.append(f"- **{pp.seed_description}** → {pp.payoff_description}")
            lines.append("")

        if self.recent_beats:
            lines.append("### 최근 주요 이벤트")
            for beat in self.recent_beats[-3:]:
                lines.append(f"- [{beat.phase.value}] {beat.summary}")
            lines.append("")

        return "\n".join(lines)
