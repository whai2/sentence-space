"""
시나리오 관련 모델

- 시나리오 템플릿 (Master Data)
- 시나리오 요약 (History 압축)
"""
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# 시나리오 템플릿 (Master Data)
# ============================================

class ScenarioPhase(BaseModel):
    """시나리오 진행 단계"""
    phase_id: str
    description: str
    trigger: str  # "turn_1", "turn_5", "npc_death" 등


class NPCSpawn(BaseModel):
    """NPC 스폰 정보"""
    npc_type: str
    count_range: tuple[int, int]  # (min, max)
    location: str


class ScenarioTemplate(BaseModel):
    """
    시나리오 템플릿 (MongoDB scenarios)

    고정 데이터로, 게임 시작 시 DB에 미리 저장됨
    """
    scenario_id: str
    title: str
    difficulty: str  # "D급", "C급", "B급" 등

    objective: str
    time_limit: int | None = None  # 턴 수
    reward_coins: int = 0
    reward_exp: int = 0

    # 시나리오 진행 단계
    phases: list[ScenarioPhase] = Field(default_factory=list)

    # 스폰될 NPC
    npc_spawns: list[NPCSpawn] = Field(default_factory=list)


# ============================================
# 시나리오 요약 (History 압축)
# ============================================

class KeyDecision(BaseModel):
    """핵심 결정 순간"""
    turn: int
    action: str
    result: str


class ScenarioSummary(BaseModel):
    """
    시나리오 요약 (MongoDB scenario_summaries)

    시나리오 완료 시 Orchestrator가 생성
    전체 히스토리를 압축하여 다음 시나리오에서 참고
    """
    session_id: str
    scenario_id: str

    # 턴 범위
    turn_start: int
    turn_end: int

    # Orchestrator가 생성한 요약
    summary: str

    # 핵심 결정들
    key_decisions: list[KeyDecision] = Field(default_factory=list)

    # 시나리오 종료 시점 상태 스냅샷
    final_state: dict  # {player_health, player_coins, killed_npcs, etc.}

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# 시나리오 컨텍스트 (LLM에게 전달)
# ============================================

class ScenarioContext(BaseModel):
    """
    현재 시나리오의 컨텍스트

    Orchestrator가 판단에 사용할 정보
    """
    scenario_id: str
    title: str
    objective: str
    difficulty: str

    remaining_time: int | None
    current_phase: str | None  # "intro", "escalation", "climax"

    # 이전 시나리오 요약 (있으면)
    previous_summaries: list[ScenarioSummary] = Field(default_factory=list)


# ============================================
# GraphRAG 강화 모델
# ============================================

class CharacterInfo(BaseModel):
    """캐릭터 정보 (Neo4j에서 조회)"""
    character_id: str
    name: str
    character_type: str  # "dokkaebi", "civilian", "monster"
    description: str
    role: str  # "scenario_host", "potential_victim", "ally"
    personality_traits: list[str] = Field(default_factory=list)
    appearance: str | None = None


class RuleInfo(BaseModel):
    """규칙 정보 (Neo4j에서 조회)"""
    rule_id: str
    rule_type: str  # "win_condition", "fail_condition", "system_rule", "hidden_trick"
    description: str
    is_hidden: bool
    importance: int


class TrickInfo(BaseModel):
    """트릭 정보 (김독자만 아는 지식)"""
    trick_id: str
    name: str
    description: str
    difficulty_to_discover: int
    is_protagonist_knowledge: bool
    narrative_hint: str  # AutoNarrator 서술 시 힌트


class AlternativeSolution(BaseModel):
    """대안 솔루션 (도덕성 기반)"""
    trick: TrickInfo
    difficulty: int  # 실행 난이도 (1-10)
    morality_score: int  # 도덕성 점수 (1-10, 높을수록 도덕적)


class LocationInfo(BaseModel):
    """위치 정보"""
    location_id: str
    name: str
    description: str
    atmosphere: str
    danger_level: int


class EnrichedScenarioContext(BaseModel):
    """
    GraphRAG로 강화된 시나리오 컨텍스트

    Neo4j 지식 그래프에서 조회한 상세 정보 포함
    AutoNarrator가 원작에 충실한 서술을 생성하는 데 사용
    """
    # 기본 정보 (ScenarioContext와 동일)
    scenario_id: str
    title: str
    objective: str
    difficulty: str
    remaining_time: int | None
    current_phase: str | None = None

    # GraphRAG 추가 정보
    detailed_description: str
    key_characters: list[CharacterInfo] = Field(default_factory=list)
    locations: list[LocationInfo] = Field(default_factory=list)
    win_conditions: list[RuleInfo] = Field(default_factory=list)
    fail_conditions: list[RuleInfo] = Field(default_factory=list)

    # 주인공 전용 트릭 (김독자만 알고 있음)
    protagonist_tricks: list[TrickInfo] = Field(default_factory=list)

    # 대안 솔루션 (도덕성 순으로 정렬됨)
    alternative_solutions: list[AlternativeSolution] = Field(default_factory=list)

    # 서술 힌트 (AutoNarrator용)
    narrative_hints: list[str] = Field(default_factory=list)
