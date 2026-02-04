from pydantic import BaseModel, Field
import math


class Coordinate(BaseModel):
    """위도/경도 좌표"""

    lat: float  # 위도
    lng: float  # 경도

    def distance_to(self, other: "Coordinate") -> float:
        """두 좌표 사이의 거리(미터) - Haversine 공식"""
        R = 6371000  # 지구 반지름 (미터)
        lat1, lat2 = math.radians(self.lat), math.radians(other.lat)
        delta_lat = math.radians(other.lat - self.lat)
        delta_lng = math.radians(other.lng - self.lng)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c


# 서울 지하철 3호선 좌표 매핑
SUBWAY_COORDINATES = {
    "3호선_객차_1": Coordinate(lat=37.5028, lng=127.0244),
    "3호선_객차_2": Coordinate(lat=37.5029, lng=127.0245),
    "3호선_객차_3": Coordinate(lat=37.5030, lng=127.0246),
    "3호선_객차_4": Coordinate(lat=37.5031, lng=127.0247),
    "3호선_객차_5": Coordinate(lat=37.5032, lng=127.0248),
    "3호선_객차_6": Coordinate(lat=37.5033, lng=127.0249),
    "3호선_운전실": Coordinate(lat=37.5027, lng=127.0243),
    "지하철_플랫폼": Coordinate(lat=37.5035, lng=127.0250),
}


# ============================================
# 스킬 진화/변형 시스템
# ============================================

class SkillModifier(BaseModel):
    """스킬 수정자 - 버프/디버프/진화 효과"""

    modifier_id: str
    name: str
    effect_type: str  # "damage_boost", "cooldown_reduce", "effect_change", "evolution"
    value: float = 0  # 수치 변화량
    description: str = ""
    duration: int | None = None  # None이면 영구, 숫자면 턴 수
    trigger_condition: str | None = None  # "on_kill", "low_health", "first_use" 등
    is_active: bool = True


class SkillEvolution(BaseModel):
    """스킬 진화 정보"""

    from_skill_id: str
    to_skill_id: str
    to_skill_name: str
    to_grade: str
    condition: str  # 진화 조건 설명
    condition_type: str  # "proficiency", "kill_count", "special_action"
    condition_value: int = 100  # 조건 수치


class SkillInstance(BaseModel):
    """보유 스킬 (동적 상태 포함)"""

    skill_id: str
    base_skill_id: str | None = None  # 원본 스킬 ID (진화한 경우)
    name: str
    grade: str  # 일반, 희귀, 전설, 신화
    level: int = 1
    proficiency: int = 0  # 숙련도 (100이 되면 레벨업)
    max_proficiency: int = 100
    cooldown: int = 0  # 남은 쿨다운 (턴)
    max_cooldown: int = 0  # 기본 쿨다운
    description: str = ""

    # 동적 수정자
    modifiers: list[SkillModifier] = Field(default_factory=list)

    # 진화 가능 여부
    can_evolve: bool = False
    evolution_progress: int = 0  # 진화 진행도
    evolution_target: SkillEvolution | None = None

    # 사용 통계
    use_count: int = 0
    kill_count: int = 0  # 이 스킬로 처치한 수

    def add_proficiency(self, amount: int) -> bool:
        """숙련도 추가, 레벨업 시 True 반환"""
        self.proficiency += amount
        if self.proficiency >= self.max_proficiency:
            self.proficiency = 0
            self.level += 1
            self.max_proficiency = int(self.max_proficiency * 1.5)
            return True
        return False

    def apply_modifiers(self, base_value: float, effect_type: str) -> float:
        """수정자 적용"""
        result = base_value
        for mod in self.modifiers:
            if mod.is_active and mod.effect_type == effect_type:
                result += mod.value
        return result


# ============================================
# 아이템 상태 관리 시스템
# ============================================

class ItemModifier(BaseModel):
    """아이템 수정자"""

    modifier_id: str
    name: str
    effect_type: str  # "damage", "defense", "special"
    value: float = 0
    description: str = ""


class ItemInstance(BaseModel):
    """아이템 인스턴스 (동적 상태 포함)"""

    item_id: str
    name: str
    item_type: str  # "weapon", "consumable", "material", "key_item"
    description: str = ""

    # 내구도 시스템
    durability: int = 100
    max_durability: int = 100
    is_breakable: bool = True

    # 강화 시스템
    enhancement_level: int = 0
    max_enhancement: int = 10

    # 기본 스탯
    base_damage: int = 0
    base_defense: int = 0

    # 수정자
    modifiers: list[ItemModifier] = Field(default_factory=list)

    # 특수 효과
    special_effects: list[str] = Field(default_factory=list)  # "bleeding", "poison" 등

    # 스택 가능 여부
    stackable: bool = False
    stack_count: int = 1
    max_stack: int = 1

    # 사용 가능 여부
    usable: bool = False
    use_effect: str | None = None  # "heal_30", "stamina_50" 등

    def get_total_damage(self) -> int:
        """강화 및 수정자 적용된 총 데미지"""
        damage = self.base_damage + (self.enhancement_level * 2)
        for mod in self.modifiers:
            if mod.effect_type == "damage":
                damage += int(mod.value)
        return damage

    def use_durability(self, amount: int = 1) -> bool:
        """내구도 사용, 파괴되면 True 반환"""
        if not self.is_breakable:
            return False
        self.durability -= amount
        return self.durability <= 0


# ============================================
# NPC 관계/기억 시스템
# ============================================

class NPCMemory(BaseModel):
    """NPC가 기억하는 이벤트"""

    memory_id: str
    event_type: str  # "helped", "attacked", "witnessed", "conversation"
    description: str
    turn_occurred: int
    impact: int = 0  # 관계도 변화량 (-100 ~ 100)
    is_important: bool = False  # 중요 기억은 잊지 않음


class NPCRelationship(BaseModel):
    """플레이어와 NPC의 관계"""

    affinity: int = Field(default=0, ge=-100, le=100)  # 호감도
    trust: int = Field(default=0, ge=-100, le=100)  # 신뢰도
    fear: int = Field(default=0, ge=0, le=100)  # 공포도

    relationship_type: str = "stranger"  # stranger, acquaintance, ally, enemy, etc.

    # 관계 이력
    interactions_count: int = 0
    last_interaction_turn: int | None = None

    def update_from_action(self, action_type: str, intensity: int = 10) -> None:
        """행동에 따른 관계 업데이트"""
        if action_type == "help":
            self.affinity = min(100, self.affinity + intensity)
            self.trust = min(100, self.trust + intensity // 2)
        elif action_type == "attack":
            self.affinity = max(-100, self.affinity - intensity * 2)
            self.fear = min(100, self.fear + intensity)
        elif action_type == "threaten":
            self.fear = min(100, self.fear + intensity)
            self.trust = max(-100, self.trust - intensity)
        elif action_type == "persuade":
            self.trust = min(100, self.trust + intensity)

        self.interactions_count += 1
        self._update_relationship_type()

    def _update_relationship_type(self) -> None:
        """관계 타입 자동 갱신"""
        if self.affinity >= 50 and self.trust >= 30:
            self.relationship_type = "ally"
        elif self.affinity <= -50 or self.fear >= 70:
            self.relationship_type = "enemy"
        elif self.interactions_count >= 3:
            self.relationship_type = "acquaintance"
        else:
            self.relationship_type = "stranger"


class NPCPersonality(BaseModel):
    """NPC 성격 특성"""

    bravery: int = Field(default=50, ge=0, le=100)  # 용기 (높으면 도망 안감)
    aggression: int = Field(default=50, ge=0, le=100)  # 공격성
    empathy: int = Field(default=50, ge=0, le=100)  # 공감 능력
    selfishness: int = Field(default=50, ge=0, le=100)  # 이기심
    rationality: int = Field(default=50, ge=0, le=100)  # 합리성 (높으면 감정적 반응 적음)


class NPCInstance(BaseModel):
    """NPC 인스턴스 (동적 상태 포함)"""

    id: str
    name: str
    npc_type: str = "civilian"  # civilian, hostile, ally, special
    named: bool = False  # 이름이 확정되었는지 여부 (이름을 물어보면 True)
    description: str
    position: str
    coordinates: Coordinate

    # 기본 상태
    health: int = 100
    max_health: int = 100
    is_alive: bool = True
    disposition: str = "neutral"  # hostile, neutral, friendly, terrified

    # 장비
    has_weapon: bool = False
    weapon_type: str | None = None
    equipped_items: list[str] = Field(default_factory=list)

    # 중요도
    is_important: bool = False  # 주요 인물 여부
    is_unique: bool = False  # 유니크 NPC (죽으면 부활 안함)

    # 대화 시스템
    dialogue_state: str = "initial"
    available_dialogues: list[str] = Field(default_factory=list)

    # 관계 시스템
    relationship: NPCRelationship = Field(default_factory=NPCRelationship)

    # 기억 시스템
    memories: list[NPCMemory] = Field(default_factory=list)
    memory_capacity: int = 10  # 최대 기억 수 (중요하지 않은 것은 잊음)

    # 성격
    personality: NPCPersonality = Field(default_factory=NPCPersonality)

    # AI 상태
    current_goal: str | None = None  # "flee", "fight", "hide", "help_player"
    emotional_state: str = "calm"  # calm, panicked, angry, sad, hopeful

    # 통계
    damage_dealt_to_player: int = 0
    damage_received_from_player: int = 0

    def add_memory(self, memory: NPCMemory) -> None:
        """기억 추가 (용량 초과시 중요하지 않은 것 삭제)"""
        self.memories.append(memory)
        self.relationship.affinity += memory.impact
        self.relationship.affinity = max(-100, min(100, self.relationship.affinity))

        # 용량 초과 시 중요하지 않은 오래된 기억 삭제
        if len(self.memories) > self.memory_capacity:
            non_important = [m for m in self.memories if not m.is_important]
            if non_important:
                self.memories.remove(non_important[0])

    def decide_action(self, threat_level: int) -> str:
        """상황에 따른 행동 결정"""
        # 공포가 높고 용기가 낮으면 도망
        if self.relationship.fear > 70 and self.personality.bravery < 30:
            return "flee"

        # 적대적이고 공격성이 높으면 공격
        if self.disposition == "hostile" and self.personality.aggression > 60:
            return "fight"

        # 플레이어와 친밀하면 도움
        if self.relationship.affinity > 50:
            return "help_player"

        # 기본적으로 숨기
        if threat_level > 50:
            return "hide"

        return "observe"


# ============================================
# 플레이어 상태
# ============================================

class AttributePoints(BaseModel):
    """스탯 포인트"""

    strength: int = Field(default=10, ge=1)      # 근력
    agility: int = Field(default=10, ge=1)       # 민첩
    endurance: int = Field(default=10, ge=1)     # 지구력
    magic: int = Field(default=10, ge=1)         # 마력
    luck: int = Field(default=10, ge=1)          # 행운


class StatusEffect(BaseModel):
    """상태이상"""

    effect_id: str
    name: str
    effect_type: str  # "dot", "debuff", "buff", "special"
    value: int = 0  # 효과 수치
    duration: int | None = None  # None이면 영구
    tick_damage: int = 0  # 턴당 데미지


class PlayerState(BaseModel):
    """플레이어의 현재 상태"""

    name: str = Field(default="이름 없는 승객")
    level: int = Field(default=1, ge=1)
    experience: int = Field(default=0, ge=0)
    exp_to_next_level: int = Field(default=100)

    health: int = Field(default=100, ge=0)
    max_health: int = Field(default=100)
    stamina: int = Field(default=100, ge=0, le=100)

    coins: int = Field(default=0, ge=0)

    attributes: AttributePoints = Field(default_factory=AttributePoints)
    attribute_points: int = Field(default=0)

    position: str = Field(default="3호선_객차_3")
    coordinates: Coordinate = Field(
        default_factory=lambda: SUBWAY_COORDINATES["3호선_객차_3"].model_copy()
    )

    # 스킬 (확장된 버전)
    skills: list[SkillInstance] = Field(default_factory=list)

    # 인벤토리 (확장된 버전)
    inventory: list[ItemInstance] = Field(default_factory=list)
    equipped_weapon: ItemInstance | None = None
    max_inventory_size: int = 20

    # 상태이상 (확장된 버전)
    status_effects: list[StatusEffect] = Field(default_factory=list)
    is_bleeding: bool = Field(default=False)
    is_poisoned: bool = Field(default=False)
    fear_level: int = Field(default=0, ge=0, le=100)

    # 통계
    total_kills: int = 0
    human_kills: int = 0
    monster_kills: int = 0

    def add_item(self, item: ItemInstance) -> bool:
        """아이템 추가, 실패시 False"""
        if len(self.inventory) >= self.max_inventory_size:
            # 스택 가능한 아이템 체크
            if item.stackable:
                for inv_item in self.inventory:
                    if inv_item.item_id == item.item_id and inv_item.stack_count < inv_item.max_stack:
                        inv_item.stack_count += item.stack_count
                        return True
            return False
        self.inventory.append(item)
        return True

    def get_total_damage(self) -> int:
        """총 공격력 계산"""
        base = self.attributes.strength
        if self.equipped_weapon:
            base += self.equipped_weapon.get_total_damage()
        return base

    def apply_status_effects(self) -> int:
        """상태이상 효과 적용, 총 데미지 반환"""
        total_damage = 0
        effects_to_remove = []

        for effect in self.status_effects:
            if effect.tick_damage > 0:
                total_damage += effect.tick_damage

            if effect.duration is not None:
                effect.duration -= 1
                if effect.duration <= 0:
                    effects_to_remove.append(effect)

        for effect in effects_to_remove:
            self.status_effects.remove(effect)

        return total_damage


# ============================================
# 시나리오 상태
# ============================================

class ScenarioState(BaseModel):
    """시나리오 진행 상태"""

    scenario_id: str
    title: str
    difficulty: str
    status: str = "active"
    objective: str
    progress: str = ""
    time_limit: int | None = None
    remaining_time: int | None = None
    reward_coins: int = 0
    reward_exp: int = 0

    # 추가 보상
    bonus_rewards: list[str] = Field(default_factory=list)

    # 숨겨진 목표
    hidden_objectives: list[str] = Field(default_factory=list)
    hidden_objectives_completed: list[str] = Field(default_factory=list)


# ============================================
# 성좌 채널
# ============================================

class ConstellationChannel(BaseModel):
    """성좌 채널 메시지"""

    constellation_name: str
    message: str
    coins_donated: int = 0
    turn: int
    reaction_type: str = "neutral"  # positive, negative, neutral, excited


class ConstellationRelationship(BaseModel):
    """성좌와의 관계"""

    constellation_id: str
    name: str
    favor: int = Field(default=0, ge=-100, le=100)  # 호감도
    total_donated: int = 0  # 총 후원 코인
    is_sponsor: bool = False  # 후원자 여부


# ============================================
# 게임 상태
# ============================================

class GameState(BaseModel):
    """게임의 전체 상태"""

    session_id: str
    player: PlayerState = Field(default_factory=PlayerState)
    turn_count: int = Field(default=0)

    # 시나리오 시스템
    current_scenario: ScenarioState | None = Field(default=None)
    completed_scenarios: list[str] = Field(default_factory=list)

    # NPC 관리 (확장된 버전)
    npcs: list[NPCInstance] = Field(default_factory=list)
    killed_npcs: list[str] = Field(default_factory=list)

    # 성좌 시스템 (확장된 버전)
    constellation_channel: list[ConstellationChannel] = Field(default_factory=list)
    watching_constellations: list[str] = Field(default_factory=list)
    constellation_relationships: list[ConstellationRelationship] = Field(default_factory=list)

    # 발견한 장소
    discovered_locations: list[str] = Field(default_factory=lambda: ["3호선_객차_3"])

    # 이벤트 및 상태
    active_events: list[str] = Field(default_factory=list)
    game_over: bool = Field(default=False)
    scenario_cleared: bool = Field(default=False)

    # 메시지 히스토리
    message_history: list[dict] = Field(default_factory=list)

    # 게임 진행 플래그
    first_kill_completed: bool = Field(default=False)
    first_human_kill: bool = Field(default=False)

    # 지하철 상태
    subway_stopped: bool = Field(default=True)
    emergency_announced: bool = Field(default=False)
    panic_level: int = Field(default=0, ge=0, le=100)

    # 글로벌 이벤트 트래커
    global_events: dict[str, bool] = Field(default_factory=dict)

    def get_npc_by_id(self, npc_id: str) -> NPCInstance | None:
        """ID로 NPC 찾기"""
        for npc in self.npcs:
            if npc.id == npc_id:
                return npc
        return None

    def get_npcs_in_location(self, location: str, alive_only: bool = True) -> list[NPCInstance]:
        """특정 위치의 NPC들 반환"""
        return [
            npc for npc in self.npcs
            if npc.position == location and (not alive_only or npc.is_alive)
        ]

    def process_turn_effects(self) -> dict:
        """턴 종료 시 효과 처리"""
        results = {
            "player_damage": 0,
            "expired_effects": [],
            "npc_actions": [],
        }

        # 플레이어 상태이상 처리
        results["player_damage"] = self.player.apply_status_effects()

        # NPC 행동 결정
        for npc in self.npcs:
            if npc.is_alive:
                action = npc.decide_action(self.panic_level)
                npc.current_goal = action
                results["npc_actions"].append({
                    "npc_id": npc.id,
                    "action": action
                })

        return results
