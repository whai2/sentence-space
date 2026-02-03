from pydantic import BaseModel, Field

from domain.world.model.state import Coordinate, SEOUL_COORDINATES


class BugInfo(BaseModel):
    """벌레 정보"""

    name: str
    description: str
    danger_level: int = Field(ge=1, le=10)
    weakness: str  # 공략법
    attack_pattern: str
    appears_when: str | None = None  # 출현 조건
    spawn_locations: list[str] = Field(default_factory=list)  # 출현 가능 장소
    detection_range: float = 500  # 감지 거리 (미터)
    chase_speed: float = 0.0015  # 추격 속도 (위도/경도 단위)
    attracted_by_blood: bool = False  # 피에 이끌리는지


class DiscoverableInfo(BaseModel):
    """발견 가능한 정보"""

    id: str
    title: str
    content: str
    location: str  # 발견 가능한 장소
    trigger: str  # 발견 조건 (예: "주변을 살핀다", "바닥을 조사한다")
    useful_for: str  # 이 정보가 유용한 상황


class LocationInfo(BaseModel):
    """장소 정보"""

    name: str
    description: str
    coordinates: Coordinate  # 서울 좌표
    radius: float = 500  # 해당 지역 반경 (미터)
    dangers: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)
    connected_to: list[str] = Field(default_factory=list)
    discoverable: list[str] = Field(default_factory=list)  # 발견 가능한 정보 ID들


class WorldKnowledge(BaseModel):
    """세계관 지식 - 불변 데이터"""

    world_name: str = "붉은 사막"
    world_description: str = """
    플레이어는 거대한 모래폭풍에 쫓기고 있다.
    뒤를 돌아볼 수 없다. 뒤에는 죽음뿐이다.
    앞에는 끝없는 붉은 사막. 어딘가에 지하 도시가 있다고 들었다.
    그곳만이 유일한 피난처다.

    사막에는 모래 속에 숨은 것들이 있다. 피 냄새를 맡으면 몰려온다.
    """

    destination: str = "지하_도시"

    bugs: list[BugInfo] = Field(default_factory=lambda: [
        BugInfo(
            name="모래 전갈",
            description="모래 속에 숨어있다가 진동을 감지하면 튀어나온다",
            danger_level=3,
            weakness="움직임을 멈추고 기다리면 흥미를 잃고 떠난다",
            attack_pattern="꼬리의 독침으로 공격한다",
            spawn_locations=["모래_평원", "모래_폭풍_지역"],
            detection_range=300,
            chase_speed=0.001,
        ),
        BugInfo(
            name="피딱정벌레",
            description="피 냄새를 맡으면 무리를 지어 쫓아온다",
            danger_level=5,
            weakness="불을 무서워한다. 횃불이나 불로 쫓아낼 수 있다",
            attack_pattern="무리 지어 달려들어 물어뜯는다",
            appears_when="bleeding",
            spawn_locations=["모래_평원", "바위_지대"],
            detection_range=1000,  # 피 냄새 감지 거리가 더 김
            chase_speed=0.002,
            attracted_by_blood=True,
        ),
        BugInfo(
            name="개미귀신",
            description="깔때기 모양의 함정을 파고 기다리는 거대한 벌레",
            danger_level=7,
            weakness="함정의 가장자리를 천천히 돌아가면 탈출할 수 있다",
            attack_pattern="함정에 빠지면 모래를 뿜어 끌어들인다",
            appears_when="random_trap",
            spawn_locations=["바위_지대", "모래_폭풍_지역"],
            detection_range=100,  # 함정형이라 감지 거리가 짧음
            chase_speed=0,  # 이동하지 않음 (함정형)
        ),
    ])

    # 발견 가능한 정보들 - 환경 관찰 기반
    discoverable_info: list[DiscoverableInfo] = Field(default_factory=lambda: [
        DiscoverableInfo(
            id="sand_flow_direction",
            title="모래의 흐름",
            content="바닥의 모래가 미세하게 한 방향으로 구른다. 북동쪽으로 아주 약간 경사져 있는 것 같다. 그 방향에 뭔가 거대한 공동이 있어 모래가 빠져나가는 걸지도 모른다.",
            location="사막_입구",
            trigger="바닥의 모래를 유심히 관찰한다",
            useful_for="지하 도시 방향 파악",
        ),
        DiscoverableInfo(
            id="scorpion_behavior",
            title="전갈의 습성",
            content="전갈이 진동에 반응한다는 것을 알았다. 움직임을 완전히 멈추자 전갈이 흥미를 잃고 모래 속으로 사라졌다. 진동을 감지하지 못하면 공격하지 않는 것 같다.",
            location="모래_평원",
            trigger="전갈의 움직임을 관찰한다",
            useful_for="모래 전갈 대처법",
        ),
        DiscoverableInfo(
            id="beetle_fire_fear",
            title="벌레들의 반응",
            content="마른 풀에 불꽃이 튀자 주변의 작은 벌레들이 순식간에 흩어졌다. 이 사막의 벌레들은 불을 본능적으로 두려워하는 것 같다.",
            location="모래_평원",
            trigger="마른 풀이나 불씨를 관찰한다",
            useful_for="피딱정벌레 대처법",
        ),
        DiscoverableInfo(
            id="flint_stones",
            title="부싯돌 발견",
            content="바위 틈에서 날카로운 돌멩이들을 발견했다. 서로 부딪히면 불꽃이 튄다. 이걸로 불을 피울 수 있을 것 같다.",
            location="바위_지대",
            trigger="바위 틈을 살펴본다",
            useful_for="불 피우기 재료",
        ),
        DiscoverableInfo(
            id="antlion_trap_pattern",
            title="깔때기 함정의 패턴",
            content="모래 위에 원형으로 움푹 패인 곳들이 보인다. 가장자리의 모래가 불안정하게 미끄러진다. 중심으로 빨려들면 탈출하기 어려울 것 같다. 가장자리를 천천히 돌아가면 모래가 무너지지 않을지도 모른다.",
            location="바위_지대",
            trigger="모래 웅덩이를 관찰한다",
            useful_for="개미귀신 대처법",
        ),
        DiscoverableInfo(
            id="wind_pattern",
            title="바람의 방향",
            content="모래폭풍이 잠시 멎은 틈에 바람의 패턴을 느꼈다. 바람이 특정 방향에서 빨려 들어가듯 불어온다. 그쪽에 커다란 틈이 있는 것 같다.",
            location="모래_폭풍_지역",
            trigger="바람의 방향을 느껴본다",
            useful_for="균열 지대 방향",
        ),
        DiscoverableInfo(
            id="ground_vibration",
            title="땅의 진동",
            content="발밑에서 미세한 진동이 느껴진다. 깊은 곳에서 뭔가가 움직이는 것 같다. 진동이 더 강한 쪽으로 가면 지하로 통하는 길을 찾을 수 있을지도 모른다.",
            location="균열_지대",
            trigger="땅에 손을 대고 느껴본다",
            useful_for="지하 도시 입구 찾기",
        ),
        DiscoverableInfo(
            id="air_temperature",
            title="공기의 온도차",
            content="균열 중 하나에서 서늘한 공기가 올라온다. 지하에서 불어오는 바람이다. 이 균열이 지하로 통하는 입구일 것이다.",
            location="균열_지대",
            trigger="균열에서 나오는 공기를 느껴본다",
            useful_for="지하 도시 입구 발견",
        ),
    ])

    locations: list[LocationInfo] = Field(default_factory=lambda: [
        LocationInfo(
            name="사막_입구",
            description="붉은 사막의 시작점. 뒤로는 척박한 황무지가 보인다.",
            coordinates=SEOUL_COORDINATES["사막_입구"],
            radius=400,
            connected_to=["모래_평원"],
            discoverable=["sand_flow_direction"],
        ),
        LocationInfo(
            name="모래_평원",
            description="끝없이 펼쳐진 붉은 모래. 가끔 모래 언덕이 보인다.",
            coordinates=SEOUL_COORDINATES["모래_평원"],
            radius=800,  # 넓은 지역
            dangers=["모래 전갈"],
            connected_to=["사막_입구", "바위_지대", "모래_폭풍_지역"],
            discoverable=["scorpion_behavior", "beetle_fire_fear"],
        ),
        LocationInfo(
            name="바위_지대",
            description="거대한 붉은 바위들이 솟아있다. 그늘에서 쉴 수 있다.",
            coordinates=SEOUL_COORDINATES["바위_지대"],
            radius=500,
            items=["날카로운 돌", "부싯돌"],
            connected_to=["모래_평원", "균열_지대"],
            discoverable=["flint_stones", "antlion_trap_pattern"],
        ),
        LocationInfo(
            name="모래_폭풍_지역",
            description="모래 폭풍이 자주 발생하는 위험 지역.",
            coordinates=SEOUL_COORDINATES["모래_폭풍_지역"],
            radius=600,
            dangers=["모래 전갈", "개미귀신"],
            connected_to=["모래_평원", "균열_지대"],
            discoverable=["wind_pattern"],
        ),
        LocationInfo(
            name="균열_지대",
            description="땅에 깊은 균열이 나있다. 지하로 통하는 입구가 보인다.",
            coordinates=SEOUL_COORDINATES["균열_지대"],
            radius=400,
            connected_to=["바위_지대", "모래_폭풍_지역", "지하_도시"],
            discoverable=["ground_vibration", "air_temperature"],
        ),
        LocationInfo(
            name="지하_도시",
            description="드디어 도착한 지하 도시. 고대의 건축물이 눈앞에 펼쳐진다.",
            coordinates=SEOUL_COORDINATES["지하_도시"],
            radius=300,
            connected_to=["균열_지대"],
        ),
    ])

    rules: list[str] = Field(default_factory=lambda: [
        "피를 흘리면(bleeding=True) 피딱정벌레가 출현할 확률이 높아진다",
        "threat_level이 높을수록 위험한 상황이 발생할 확률이 높아진다",
        "전투에서 피해를 입으면 bleeding 상태가 될 수 있다",
        "지하_도시에 도달하면 게임 클리어",
        "플레이어가 이미 알고 있는 정보(knowledge)는 게임에 활용될 수 있다",
    ])
