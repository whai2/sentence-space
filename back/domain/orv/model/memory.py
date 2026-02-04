"""
기억 시스템 모델 정의

NPC의 장기/단기 기억, 관계 기억, 목표 등을 관리하는 모델들.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """단일 기억 단위"""

    memory_id: str
    npc_id: str

    # 내용
    event_type: str  # "interaction", "witnessed", "heard", "internal", "npc_dialogue"
    summary: str  # 요약 (검색용)
    detailed_content: str | None = None  # 상세 내용

    # 메타데이터
    turn_occurred: int
    timestamp: datetime = Field(default_factory=datetime.now)
    location: str

    # 관련 엔티티
    involves_player: bool = False
    involves_npcs: list[str] = Field(default_factory=list)  # NPC IDs
    speaker_id: str | None = None  # 대화의 경우 화자

    # 중요도 및 감정
    importance: int = Field(default=5, ge=1, le=10)  # 1-10
    emotional_valence: float = Field(default=0, ge=-1, le=1)  # -1(부정) ~ 1(긍정)
    emotional_intensity: float = Field(default=0.5, ge=0, le=1)  # 감정 강도

    # 검색용 키워드
    keywords: list[str] = Field(default_factory=list)

    # 기억 접근 추적
    access_count: int = 0
    last_accessed: datetime | None = None

    # 장기 기억 전환 여부
    is_consolidated: bool = False

    def touch(self) -> None:
        """기억 접근 시 호출"""
        self.access_count += 1
        self.last_accessed = datetime.now()


class RelationshipMemory(BaseModel):
    """NPC와 다른 엔티티(플레이어/NPC) 간의 관계 기억"""

    npc_id: str
    target_id: str  # "player" 또는 NPC ID
    target_type: str  # "player", "npc"
    target_name: str  # 표시용 이름

    # 관계 수치
    trust: int = Field(default=0, ge=-100, le=100)  # 신뢰도
    fear: int = Field(default=0, ge=0, le=100)  # 공포도
    respect: int = Field(default=0, ge=-100, le=100)  # 존경도
    affinity: int = Field(default=0, ge=-100, le=100)  # 호감도
    familiarity: int = Field(default=0, ge=0, le=100)  # 친밀도

    # 관계 라벨
    relationship_label: str = "stranger"  # stranger, acquaintance, ally, enemy, friend

    # 대상에 대한 인식
    perceived_traits: list[str] = Field(default_factory=list)  # ["dangerous", "kind", "unpredictable"]

    # 상호작용 이력
    first_interaction_turn: int | None = None
    last_interaction_turn: int | None = None
    interaction_count: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0

    # 핵심 기억 참조 (memory_id 목록)
    key_memory_ids: list[str] = Field(default_factory=list)

    def update_from_interaction(
        self,
        interaction_type: str,
        intensity: int = 10,
        turn: int | None = None,
    ) -> None:
        """상호작용에 따른 관계 업데이트"""
        if self.first_interaction_turn is None:
            self.first_interaction_turn = turn

        self.last_interaction_turn = turn
        self.interaction_count += 1
        self.familiarity = min(100, self.familiarity + 2)

        if interaction_type == "help":
            self.trust = min(100, self.trust + intensity)
            self.affinity = min(100, self.affinity + intensity)
            self.positive_interactions += 1
        elif interaction_type == "attack":
            self.trust = max(-100, self.trust - intensity * 2)
            self.fear = min(100, self.fear + intensity)
            self.affinity = max(-100, self.affinity - intensity * 2)
            self.negative_interactions += 1
        elif interaction_type == "threaten":
            self.fear = min(100, self.fear + intensity)
            self.trust = max(-100, self.trust - intensity // 2)
            self.negative_interactions += 1
        elif interaction_type == "talk":
            self.familiarity = min(100, self.familiarity + intensity // 2)
        elif interaction_type == "betray":
            self.trust = max(-100, self.trust - intensity * 3)
            self.affinity = max(-100, self.affinity - intensity * 2)
            self.negative_interactions += 1
        elif interaction_type == "save_life":
            self.trust = min(100, self.trust + intensity * 2)
            self.affinity = min(100, self.affinity + intensity * 2)
            self.respect = min(100, self.respect + intensity)
            self.positive_interactions += 1

        self._update_label()

    def _update_label(self) -> None:
        """관계 라벨 자동 갱신"""
        if self.trust >= 50 and self.affinity >= 50:
            self.relationship_label = "friend"
        elif self.trust >= 30 and self.affinity >= 20:
            self.relationship_label = "ally"
        elif self.trust <= -50 or self.fear >= 80:
            self.relationship_label = "enemy"
        elif self.familiarity >= 30:
            self.relationship_label = "acquaintance"
        else:
            self.relationship_label = "stranger"


class NPCGoal(BaseModel):
    """NPC의 목표"""

    goal_id: str
    goal_type: str  # "survival", "social", "task", "emotional"
    description: str
    priority: int = Field(default=5, ge=1, le=10)  # 1-10

    # 목표 상태
    status: str = "active"  # active, completed, failed, abandoned
    progress: float = Field(default=0, ge=0, le=1)  # 0-1

    # 조건
    target_entity_id: str | None = None  # 관련 대상 (플레이어, NPC 등)
    completion_condition: str | None = None

    # 기한
    created_turn: int
    deadline_turn: int | None = None


class NPCMemoryStore(BaseModel):
    """NPC 개별 기억 저장소"""

    npc_id: str
    npc_name: str

    # 기억 저장
    short_term_memories: list[MemoryEntry] = Field(default_factory=list)  # 최근 N턴
    long_term_memories: list[MemoryEntry] = Field(default_factory=list)  # 중요 기억
    working_memory: list[str] = Field(default_factory=list)  # 현재 턴 컨텍스트

    # 관계 기억
    relationships: dict[str, RelationshipMemory] = Field(default_factory=dict)  # target_id -> RelationshipMemory

    # 목표
    goals: list[NPCGoal] = Field(default_factory=list)

    # 설정
    short_term_capacity: int = 20  # 단기 기억 용량
    long_term_capacity: int = 50  # 장기 기억 용량

    def add_memory(self, memory: MemoryEntry) -> None:
        """기억 추가"""
        self.short_term_memories.append(memory)

        # 용량 초과 시 중요도 낮은 기억 제거 또는 장기 기억으로 전환
        if len(self.short_term_memories) > self.short_term_capacity:
            self._consolidate_memories()

    def _consolidate_memories(self) -> None:
        """단기 기억을 장기 기억으로 전환"""
        # 중요도 순 정렬
        self.short_term_memories.sort(key=lambda m: m.importance, reverse=True)

        # 상위 중요 기억은 장기로 전환
        while len(self.short_term_memories) > self.short_term_capacity:
            oldest = self.short_term_memories.pop()

            # 중요도 7 이상이면 장기 기억으로
            if oldest.importance >= 7:
                oldest.is_consolidated = True
                self.long_term_memories.append(oldest)

                # 장기 기억도 용량 체크
                if len(self.long_term_memories) > self.long_term_capacity:
                    self.long_term_memories.sort(key=lambda m: m.importance, reverse=True)
                    self.long_term_memories.pop()

    def get_relationship(self, target_id: str) -> RelationshipMemory | None:
        """특정 대상과의 관계 조회"""
        return self.relationships.get(target_id)

    def update_relationship(
        self,
        target_id: str,
        target_type: str,
        target_name: str,
        interaction_type: str,
        intensity: int = 10,
        turn: int | None = None,
    ) -> RelationshipMemory:
        """관계 업데이트 (없으면 생성)"""
        if target_id not in self.relationships:
            self.relationships[target_id] = RelationshipMemory(
                npc_id=self.npc_id,
                target_id=target_id,
                target_type=target_type,
                target_name=target_name,
            )

        rel = self.relationships[target_id]
        rel.update_from_interaction(interaction_type, intensity, turn)
        return rel

    def get_all_memories(self) -> list[MemoryEntry]:
        """모든 기억 반환 (검색용)"""
        return self.short_term_memories + self.long_term_memories

    def get_active_goals(self) -> list[NPCGoal]:
        """활성 목표 반환"""
        return [g for g in self.goals if g.status == "active"]

    def clear_working_memory(self) -> None:
        """현재 턴 작업 기억 초기화"""
        self.working_memory = []


class TurnContext(BaseModel):
    """턴 컨텍스트 (에이전트에게 전달)"""

    turn_number: int
    player_action: str
    player_position: str
    player_name: str

    # 현재 위치 정보
    location_name: str
    location_description: str

    # 주변 NPC 정보
    nearby_npc_ids: list[str] = Field(default_factory=list)
    nearby_npc_names: list[str] = Field(default_factory=list)

    # 최근 이벤트
    recent_events: list[str] = Field(default_factory=list)

    # 시나리오 정보
    scenario_objective: str | None = None
    panic_level: int = 0


class NPCContext(BaseModel):
    """NPC 에이전트에게 전달되는 컨텍스트"""

    turn_context: TurnContext

    # NPC 자신의 정보
    npc_id: str
    npc_name: str
    personality_summary: str
    emotional_state: str
    health: int
    position: str

    # 관련 기억
    relevant_memories: list[MemoryEntry] = Field(default_factory=list)

    # 플레이어와의 관계
    player_relationship: RelationshipMemory | None = None

    # 현재 목표
    active_goals: list[NPCGoal] = Field(default_factory=list)

    # 이번 턴 이 NPC가 언급되었는지
    is_addressed: bool = False
    addressed_content: str | None = None


class NPCDecision(BaseModel):
    """NPC의 의사결정 결과"""

    npc_id: str
    npc_name: str

    # 행동
    action_type: str  # "speak", "act", "react", "none"
    action_description: str  # 행동 설명

    # 대사 (있는 경우)
    dialogue: str | None = None
    dialogue_target: str | None = None  # "player", NPC ID, "all"
    dialogue_tone: str | None = "neutral"  # hostile, friendly, fearful, neutral

    # 내면
    internal_thought: str | None = None  # 내적 독백

    # 감정 변화
    new_emotional_state: str | None = None

    # 다른 NPC에게 영향
    affects_npcs: list[str] = Field(default_factory=list)  # NPC IDs

    # 기억으로 저장할 내용
    memory_summary: str | None = None
    memory_importance: int = 5


class NPCInteraction(BaseModel):
    """NPC 간 상호작용 계획"""

    initiator_id: str
    target_id: str  # NPC ID 또는 "player"
    interaction_type: str  # "dialogue", "help", "attack", "observe"
    context: str  # 상호작용 배경


class TurnPlan(BaseModel):
    """Director가 계획한 턴 진행"""

    # 활성화할 NPC
    active_npc_ids: list[str] = Field(default_factory=list)

    # NPC 간 상호작용
    npc_interactions: list[NPCInteraction] = Field(default_factory=list)

    # 서사 초점
    narrative_focus: str = ""  # 이번 턴의 서사적 핵심

    # 분위기
    scene_mood: str = "tense"  # tense, calm, chaotic, dramatic

    # 특별 이벤트
    special_events: list[str] = Field(default_factory=list)
