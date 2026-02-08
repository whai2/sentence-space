"""
기본 게임 모델 정의

MongoDB 문서 구조와 1:1 매핑되는 Pydantic 모델
"""
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# 좌표 및 위치
# ============================================

class Coordinate(BaseModel):
    """위도/경도 좌표"""
    lat: float
    lng: float


# ============================================
# 아이템
# ============================================

class ItemInstance(BaseModel):
    """플레이어 인벤토리 아이템"""
    item_id: str
    name: str
    item_type: str  # weapon, consumable, material, key_item
    base_damage: int = 0
    description: str = ""


# ============================================
# 스킬
# ============================================

class SkillInstance(BaseModel):
    """플레이어 스킬"""
    skill_id: str
    name: str
    level: int = 1
    cooldown: int = 0  # 현재 쿨다운 (턴)
    description: str = ""


# ============================================
# 플레이어 속성
# ============================================

class AttributePoints(BaseModel):
    """플레이어 스탯"""
    strength: int = 10
    agility: int = 10
    endurance: int = 10
    magic: int = 10
    luck: int = 10


class PlayerState(BaseModel):
    """플레이어 상태 (MongoDB game_sessions.player)"""
    name: str = "이름 없는 승객"
    level: int = 1

    # 체력/스태미나
    health: int = 100
    max_health: int = 100
    stamina: int = 100

    # 경험치/코인
    coins: int = 0
    experience: int = 0
    exp_to_next_level: int = 100

    # 위치
    position: str = "3호선_객차_3"
    coordinates: Coordinate = Field(
        default_factory=lambda: Coordinate(lat=37.5030, lng=127.0246)
    )

    # 스탯
    attributes: AttributePoints = Field(default_factory=AttributePoints)

    # 인벤토리
    inventory: list[ItemInstance] = Field(default_factory=list)
    skills: list[SkillInstance] = Field(default_factory=list)


# ============================================
# NPC
# ============================================

class NPCRelationship(BaseModel):
    """플레이어와 NPC의 관계"""
    affinity: int = 0  # -100 ~ 100
    trust: int = 0     # -100 ~ 100
    fear: int = 0      # 0 ~ 100


class NPCPersonality(BaseModel):
    """NPC 성격"""
    bravery: int = 50       # 0 ~ 100
    aggression: int = 50    # 0 ~ 100
    empathy: int = 50       # 0 ~ 100


class NPCState(BaseModel):
    """NPC 상태 (MongoDB npcs)"""
    npc_id: str
    name: str
    npc_type: str  # civilian, student, office_worker, etc.
    description: str

    # 위치
    position: str
    coordinates: Coordinate

    # 체력
    health: int = 100
    max_health: int = 100
    is_alive: bool = True

    # 장비
    has_weapon: bool = False

    # 감정/태도
    disposition: str = "neutral"  # hostile, neutral, friendly, terrified
    emotional_state: str = "calm"  # calm, panicked, angry, dead

    # 관계/성격
    relationship: NPCRelationship = Field(default_factory=NPCRelationship)
    personality: NPCPersonality = Field(default_factory=NPCPersonality)

    # 메타
    created_at: datetime = Field(default_factory=datetime.utcnow)
    died_at: datetime | None = None


# ============================================
# 현재 시나리오 상태
# ============================================

class CurrentScenario(BaseModel):
    """현재 진행 중인 시나리오 (MongoDB game_sessions.current_scenario)"""
    scenario_id: str
    title: str
    status: str = "active"  # active, completed, failed
    remaining_time: int | None = None
    progress: str = ""


# ============================================
# 게임 모드
# ============================================

class GameMode(str, Enum):
    """게임 모드"""
    AUTO_NARRATIVE = "auto_narrative"  # LLM이 자동으로 스토리 진행
    INTERACTIVE = "interactive"        # 사용자 입력 대기


# ============================================
# 게임 세션 전체 상태
# ============================================

class GameState(BaseModel):
    """
    게임 세션 전체 상태 (MongoDB game_sessions)

    이 모델은 MongoDB 문서와 1:1 매핑됨
    """
    session_id: str

    # 플레이어
    player: PlayerState

    # 현재 시나리오
    current_scenario: CurrentScenario | None = None

    # 게임 진행
    turn_count: int = 0
    completed_scenarios: list[str] = Field(default_factory=list)
    first_kill_completed: bool = False
    panic_level: int = 0
    game_over: bool = False

    # 게임 모드 (Auto-Narrative vs Interactive)
    game_mode: GameMode = GameMode.AUTO_NARRATIVE
    scenario_phase: str | None = None  # "intro", "active", "completed"

    # 메타
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump_for_mongodb(self) -> dict:
        """MongoDB 저장용 dict 변환"""
        data = self.model_dump()
        # datetime을 ISODate로 변환
        data["created_at"] = self.created_at
        data["updated_at"] = self.updated_at
        return data
