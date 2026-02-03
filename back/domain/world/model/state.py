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


# 서울 주요 지점 좌표 - 붉은 사막 매핑
SEOUL_COORDINATES = {
    "사막_입구": Coordinate(lat=37.4979, lng=127.0276),      # 강남역
    "모래_평원": Coordinate(lat=37.5133, lng=127.1001),      # 잠실
    "바위_지대": Coordinate(lat=37.5512, lng=126.9882),      # 남산
    "모래_폭풍_지역": Coordinate(lat=37.5254, lng=126.9264), # 여의도
    "균열_지대": Coordinate(lat=37.5171, lng=126.9950),      # 한강 (용산)
    "지하_도시": Coordinate(lat=37.5100, lng=127.0010),      # 지하 (이태원 지하)
}


class PlayerState(BaseModel):
    """플레이어의 현재 상태"""

    health: int = Field(default=100, ge=0, le=100)
    bleeding: bool = Field(default=False)
    position: str = Field(default="사막_입구")
    coordinates: Coordinate = Field(
        default_factory=lambda: SEOUL_COORDINATES["사막_입구"].model_copy()
    )
    inventory: list[str] = Field(default_factory=list)


class QuestState(BaseModel):
    """퀘스트 상태"""

    quest_id: str
    title: str
    status: str = "active"  # active, completed, failed
    progress: str = ""  # 현재 진행 상황 설명


class KnowledgeItem(BaseModel):
    """발견한 정보/지식"""

    id: str
    title: str
    content: str
    discovered_at: str  # 발견 장소
    turn_discovered: int  # 발견 턴


class BugInstance(BaseModel):
    """활성화된 벌레 인스턴스"""

    id: str  # 고유 ID
    bug_type: str  # BugInfo.name과 매칭
    coordinates: Coordinate
    state: str = "patrol"  # patrol, chasing, idle
    target_player: bool = False  # 플레이어 추적 중인지

    def move_towards(self, target: Coordinate, speed: float = 0.001) -> None:
        """목표 좌표를 향해 이동 (speed는 위도/경도 단위)"""
        direction_lat = target.lat - self.coordinates.lat
        direction_lng = target.lng - self.coordinates.lng

        # 정규화
        distance = math.sqrt(direction_lat**2 + direction_lng**2)
        if distance > 0:
            self.coordinates.lat += (direction_lat / distance) * speed
            self.coordinates.lng += (direction_lng / distance) * speed

    def patrol_random(self, center: Coordinate, radius: float = 0.005) -> None:
        """중심 좌표 주변을 랜덤하게 순찰"""
        import random

        angle = random.uniform(0, 2 * math.pi)
        self.coordinates.lat = center.lat + radius * math.sin(angle) * random.uniform(0.1, 1)
        self.coordinates.lng = center.lng + radius * math.cos(angle) * random.uniform(0.1, 1)


class SandstormState(BaseModel):
    """모래폭풍 추격 상태"""

    distance: int = Field(default=1500)  # 플레이어와의 거리 (미터)
    speed: int = Field(default=80)  # 턴당 접근 속도 (미터)
    is_active: bool = Field(default=True)


class GameState(BaseModel):
    """게임의 전체 상태"""

    session_id: str
    player: PlayerState = Field(default_factory=PlayerState)
    turn_count: int = Field(default=0)
    threat_level: int = Field(default=0, ge=0, le=10)
    discovered_locations: list[str] = Field(default_factory=lambda: ["사막_입구"])
    active_events: list[str] = Field(default_factory=list)
    game_over: bool = Field(default=False)
    reached_destination: bool = Field(default=False)
    message_history: list[dict] = Field(default_factory=list)

    # 모래폭풍 추격 시스템
    sandstorm: SandstormState = Field(default_factory=SandstormState)

    # 첫 조우 여부 (튜토리얼용)
    first_encounter_resolved: bool = Field(default=False)

    # 퀘스트 시스템
    quests: list[QuestState] = Field(default_factory=lambda: [
        QuestState(
            quest_id="main_quest",
            title="지하 도시를 찾아라",
            status="active",
            progress="모래폭풍을 피해 도망치는 중. 앞으로 나아가야 한다.",
        )
    ])

    # 정보/지식 시스템
    knowledge: list[KnowledgeItem] = Field(default_factory=list)

    # 벌레 인스턴스 시스템
    active_bugs: list[BugInstance] = Field(default_factory=list)
