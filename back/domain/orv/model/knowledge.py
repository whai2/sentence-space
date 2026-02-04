from pydantic import BaseModel, Field

from domain.orv.model.state import Coordinate, SUBWAY_COORDINATES


class ScenarioInfo(BaseModel):
    """시나리오 정보"""

    scenario_id: str
    title: str
    difficulty: str  # E, D, C, B, A, S, SS, SSS
    description: str
    objective: str
    time_limit: int | None = None  # 턴 제한 (없으면 None)
    reward_coins: int = 100
    reward_exp: int = 50
    failure_penalty: str = "사망"
    hints: list[str] = Field(default_factory=list)


class SkillInfo(BaseModel):
    """스킬 정보"""

    skill_id: str
    name: str
    grade: str  # 일반, 희귀, 전설, 신화
    description: str
    effect: str
    acquisition_condition: str  # 습득 조건
    cooldown: int = 0  # 쿨다운 (턴)
    stamina_cost: int = 0  # 스태미나 소모


class ConstellationInfo(BaseModel):
    """성좌 정보"""

    name: str
    title: str  # 칭호
    description: str
    personality: str  # 성격/말투
    preferred_actions: list[str] = Field(default_factory=list)  # 선호하는 행동
    disliked_actions: list[str] = Field(default_factory=list)  # 싫어하는 행동
    coin_generosity: int = Field(default=5, ge=1, le=10)  # 코인 후원 관대함


class NPCInfo(BaseModel):
    """NPC 템플릿"""

    npc_type: str
    name_pool: list[str] = Field(default_factory=list)  # 이름 풀
    description: str
    base_health: int = 100
    base_disposition: str = "neutral"  # hostile, neutral, friendly, terrified
    has_weapon_chance: float = 0.1  # 무기 소지 확률
    weapon_pool: list[str] = Field(default_factory=list)
    dialogue_templates: dict[str, list[str]] = Field(default_factory=dict)
    is_important: bool = False


class LocationInfo(BaseModel):
    """장소 정보"""

    name: str
    description: str
    coordinates: Coordinate
    connected_to: list[str] = Field(default_factory=list)
    npcs_count_range: tuple[int, int] = (0, 5)  # NPC 수 범위
    items: list[str] = Field(default_factory=list)
    danger_level: int = Field(default=1, ge=1, le=10)


class WorldKnowledge(BaseModel):
    """전지적 독자 시점 세계관 지식"""

    world_name: str = "전지적 독자 시점"
    world_description: str = """
    [시스템 메시지가 떴다]

    갑자기 지하철이 멈췄다.
    어둠 속에서 푸른 반투명 창이 눈앞에 떠올랐다.

    ━━━━━━━━━━━━━━━━━━━━━━━━━
    [별빛 스트림이 연결되었습니다]
    [<멸망한 세계에서 살아남는 세 가지 방법>의 시나리오가 현실화됩니다]
    ━━━━━━━━━━━━━━━━━━━━━━━━━

    [메인 시나리오 - 생존 적합성 테스트]
    목표: 생명체 하나를 죽이시오.
    제한 시간: 10분
    보상: 100 코인
    ━━━━━━━━━━━━━━━━━━━━━━━━━

    승객들 사이에서 비명이 터져 나온다.
    무슨 장난이냐는 고함, 휴대폰을 꺼내드는 손들.
    하지만 어떤 전화도 연결되지 않는다.

    형광등이 깜빡인다.
    공포에 질린 얼굴들. 누군가 울고 있다. 저 멀리서 작은 동물의 낑낑거리는 소리가 들린다.

    이것은 현실이다.
    그리고 지금부터, 살아남아야 한다.

    ...주변 사람들을 잘 살펴볼 필요가 있다.
    """

    # 초반 시나리오 정보
    scenarios: list[ScenarioInfo] = Field(default_factory=lambda: [
        ScenarioInfo(
            scenario_id="main_scenario_1",
            title="생존 적합성 테스트",
            difficulty="F",
            description="당신의 생존 적합성을 테스트합니다.",
            objective="생명체 하나를 죽이시오.",
            time_limit=10,  # 10분 (10턴)
            reward_coins=100,
            reward_exp=50,
            failure_penalty="테스트 실패 시 사망",
            hints=[],  # 힌트 없음 - 플레이어가 스스로 추론해야 함
        ),
        ScenarioInfo(
            scenario_id="main_scenario_2",
            title="한강 대교",
            difficulty="E",
            description="지하철을 탈출하여 한강을 건너시오.",
            objective="한강 대교를 건너 생존 구역에 도달하시오.",
            time_limit=None,  # 시간 제한 없음
            reward_coins=300,
            reward_exp=150,
            failure_penalty="사망",
            hints=[
                "다리 위에는 위험이 도사리고 있습니다.",
                "혼자보다는 함께가 나을 수 있습니다.",
            ],
        ),
    ])

    # 습득 가능한 스킬
    skills: list[SkillInfo] = Field(default_factory=lambda: [
        SkillInfo(
            skill_id="insight",
            name="통찰",
            grade="희귀",
            description="대상의 정보를 파악합니다.",
            effect="NPC나 상황의 숨겨진 정보를 볼 수 있습니다.",
            acquisition_condition="관찰을 통해 3번 이상 정보를 얻으면 습득",
            cooldown=3,
            stamina_cost=10,
        ),
        SkillInfo(
            skill_id="intimidation",
            name="위협",
            grade="일반",
            description="대상을 위협하여 공포를 줍니다.",
            effect="대상의 행동을 저지하거나 도망가게 만듭니다.",
            acquisition_condition="성공적으로 누군가를 위협하면 습득",
            cooldown=2,
            stamina_cost=15,
        ),
        SkillInfo(
            skill_id="quick_step",
            name="재빠른 발걸음",
            grade="일반",
            description="순간적으로 빠르게 이동합니다.",
            effect="한 턴에 2칸 이동 가능",
            acquisition_condition="전투 중 회피에 성공하면 습득",
            cooldown=3,
            stamina_cost=20,
        ),
        SkillInfo(
            skill_id="persuasion",
            name="설득",
            grade="희귀",
            description="상대방을 설득합니다.",
            effect="적대적인 NPC를 중립 또는 우호적으로 만들 수 있습니다.",
            acquisition_condition="대화로 위기를 모면하면 습득",
            cooldown=5,
            stamina_cost=10,
        ),
        SkillInfo(
            skill_id="cold_blood",
            name="냉혈",
            grade="희귀",
            description="감정을 억제하고 냉정하게 행동합니다.",
            effect="공포도가 증가하지 않습니다. 전투 시 정확도 증가.",
            acquisition_condition="공포스러운 상황에서 침착하게 행동하면 습득",
            cooldown=0,
            stamina_cost=0,
        ),
        SkillInfo(
            skill_id="first_kill",
            name="첫 번째 살인",
            grade="희귀",
            description="당신은 살인자가 되었습니다.",
            effect="인간형 적에게 데미지 10% 증가. 일부 성좌의 관심을 끕니다.",
            acquisition_condition="첫 번째 살인을 저지르면 자동 습득",
            cooldown=0,
            stamina_cost=0,
        ),
    ])

    # 관전하는 성좌들
    constellations: list[ConstellationInfo] = Field(default_factory=lambda: [
        ConstellationInfo(
            name="지독한_살인귀",
            title="지독한 살인귀",
            description="피와 살육을 즐기는 성좌. 잔인한 행동에 열광합니다.",
            personality="광기어린, 흥분하기 쉬운, 폭력적",
            preferred_actions=["살인", "잔인한 행동", "무자비한 처형"],
            disliked_actions=["자비", "협상", "도망"],
            coin_generosity=8,
        ),
        ConstellationInfo(
            name="선악의_중재자",
            title="선악의 중재자",
            description="선과 악의 균형을 지켜보는 성좌. 정의로운 행동을 선호합니다.",
            personality="냉정한, 공정한, 관조적",
            preferred_actions=["정의로운 행동", "약자 보호", "공정한 판단"],
            disliked_actions=["무고한 자 살해", "비겁한 행동"],
            coin_generosity=5,
        ),
        ConstellationInfo(
            name="미친_광대",
            title="미친 광대",
            description="재미를 추구하는 성좌. 예측 불가능한 행동을 좋아합니다.",
            personality="장난스러운, 예측불가, 흥미위주",
            preferred_actions=["예상치 못한 행동", "창의적인 해결", "웃긴 상황"],
            disliked_actions=["뻔한 행동", "지루한 선택"],
            coin_generosity=6,
        ),
        ConstellationInfo(
            name="냉정한_관찰자",
            title="냉정한 관찰자",
            description="모든 것을 관찰하고 기록하는 성좌. 정보 수집을 높이 평가합니다.",
            personality="침착한, 분석적, 호기심 많은",
            preferred_actions=["관찰", "분석", "정보 수집", "전략적 행동"],
            disliked_actions=["무모한 돌격", "정보 없이 행동"],
            coin_generosity=4,
        ),
        ConstellationInfo(
            name="연민의_수호자",
            title="연민의 수호자",
            description="타인을 돕는 행동을 후원하는 성좌.",
            personality="따뜻한, 걱정하는, 보호적",
            preferred_actions=["타인 돕기", "치료", "희생", "협력"],
            disliked_actions=["이기적인 행동", "타인 해치기"],
            coin_generosity=7,
        ),
    ])

    # NPC 템플릿
    npc_templates: list[NPCInfo] = Field(default_factory=lambda: [
        NPCInfo(
            npc_type="회사원",
            name_pool=["김대리", "이과장", "박차장", "최부장", "정사원"],
            description="퇴근길 지하철에 탄 평범한 회사원",
            base_health=80,
            base_disposition="terrified",
            has_weapon_chance=0.05,
            weapon_pool=["우산", "서류가방"],
            dialogue_templates={
                "initial": [
                    "이게 무슨... 무슨 일이야?",
                    "꿈이야? 이건 꿈이지?",
                    "제발... 누가 설명 좀 해줘요!",
                ],
                "panic": [
                    "다 죽는 거야! 우리 다 죽어!",
                    "살려줘! 살려줘요!",
                    "제발요, 가족이 있어요...",
                ],
                "aggressive": [
                    "저리 꺼져! 다가오지 마!",
                    "건드리면 죽여버릴 거야!",
                ],
            },
        ),
        NPCInfo(
            npc_type="학생",
            name_pool=["민수", "지영", "현우", "수진", "동현"],
            description="학원에서 돌아오는 길의 학생",
            base_health=60,
            base_disposition="terrified",
            has_weapon_chance=0.02,
            weapon_pool=["필통", "우산"],
            dialogue_templates={
                "initial": [
                    "엄마... 엄마한테 전화해야 해...",
                    "이게 뭐야... AR인가?",
                    "무서워... 무서워요...",
                ],
                "panic": [
                    "(울음소리)",
                    "집에 가고 싶어요...",
                ],
            },
        ),
        NPCInfo(
            npc_type="노인",
            name_pool=["할아버지", "할머니", "김어르신", "이어르신"],
            description="저녁 나들이를 마치고 돌아가는 노인",
            base_health=50,
            base_disposition="neutral",
            has_weapon_chance=0.1,
            weapon_pool=["지팡이"],
            dialogue_templates={
                "initial": [
                    "이게 무슨 일이래...",
                    "세상에... 세상에...",
                    "젊은이, 이게 무슨 일인가?",
                ],
                "calm": [
                    "허허... 살 만큼 살았지.",
                    "젊은이들이나 살아야지...",
                ],
            },
        ),
        NPCInfo(
            npc_type="건달",
            name_pool=["형님", "깍두기", "칼잡이"],
            description="험상궂은 인상의 남자",
            base_health=120,
            base_disposition="hostile",
            has_weapon_chance=0.6,
            weapon_pool=["접이식 칼", "쇠파이프"],
            dialogue_templates={
                "initial": [
                    "야, 뭘 봐?",
                    "건드리면 죽여버린다.",
                ],
                "aggressive": [
                    "죽고 싶어? 어?",
                    "다 죽여버릴 거야!",
                ],
            },
        ),
        NPCInfo(
            npc_type="군인",
            name_pool=["이병장", "김상병", "박일병"],
            description="휴가 나온 군인",
            base_health=100,
            base_disposition="neutral",
            has_weapon_chance=0.1,  # 휴가중이라 무기 없음
            weapon_pool=["주먹"],
            dialogue_templates={
                "initial": [
                    "침착하세요. 당황하면 안 됩니다.",
                    "일단 상황을 파악해야 합니다.",
                ],
                "leader": [
                    "제가 앞장서겠습니다.",
                    "다들 제 뒤로 오세요.",
                ],
            },
        ),
        NPCInfo(
            npc_type="반려견_주인",
            name_pool=["견주 아줌마", "강아지 주인"],
            description="작은 강아지를 품에 안고 있는 중년 여성. 이동장 가방이 발밑에 놓여 있다.",
            base_health=70,
            base_disposition="terrified",
            has_weapon_chance=0.0,
            weapon_pool=[],
            dialogue_templates={
                "initial": [
                    "(강아지를 꼭 안으며) 쉿, 쉿... 괜찮아, 몽이야...",
                    "제발... 우리 몽이만은...",
                ],
                "panic": [
                    "안 돼! 우리 몽이한테 손대지 마!",
                    "(강아지를 감싸 안으며 울음)",
                ],
                "calm": [
                    "몽이가 무서워하네요... 어쩌면 좋아...",
                    "이 아이만 지킬 수 있다면...",
                ],
                "about_dog": [
                    "우리 몽이예요. 3살 된 포메라니안이에요.",
                    "병원 다녀오는 길이었는데... 이게 무슨...",
                    "이 아이... 이 아이가 제 전부예요.",
                ],
            },
            is_important=True,  # 시나리오 해결과 관련된 중요 NPC
        ),
    ])

    # 지하철 내 장소
    locations: list[LocationInfo] = Field(default_factory=lambda: [
        LocationInfo(
            name="3호선_객차_1",
            description="지하철 1번 객차. 승객이 적은 편이다.",
            coordinates=SUBWAY_COORDINATES["3호선_객차_1"],
            connected_to=["3호선_객차_2", "3호선_운전실"],
            npcs_count_range=(2, 4),
            items=["빈 음료수 캔", "신문"],
            danger_level=2,
        ),
        LocationInfo(
            name="3호선_객차_2",
            description="지하철 2번 객차. 적당한 수의 승객이 있다.",
            coordinates=SUBWAY_COORDINATES["3호선_객차_2"],
            connected_to=["3호선_객차_1", "3호선_객차_3"],
            npcs_count_range=(4, 8),
            items=["우산"],
            danger_level=3,
        ),
        LocationInfo(
            name="3호선_객차_3",
            description="지하철 3번 객차. 플레이어가 시작하는 곳. 승객들이 많다.",
            coordinates=SUBWAY_COORDINATES["3호선_객차_3"],
            connected_to=["3호선_객차_2", "3호선_객차_4"],
            npcs_count_range=(8, 12),
            items=["핸드폰 충전기", "에코백"],
            danger_level=4,
        ),
        LocationInfo(
            name="3호선_객차_4",
            description="지하철 4번 객차. 비명 소리가 들려온다.",
            coordinates=SUBWAY_COORDINATES["3호선_객차_4"],
            connected_to=["3호선_객차_3", "3호선_객차_5"],
            npcs_count_range=(5, 10),
            items=["깨진 유리병"],
            danger_level=5,
        ),
        LocationInfo(
            name="3호선_객차_5",
            description="지하철 5번 객차. 혼란스러운 분위기다.",
            coordinates=SUBWAY_COORDINATES["3호선_객차_5"],
            connected_to=["3호선_객차_4", "3호선_객차_6"],
            npcs_count_range=(4, 8),
            items=["소화기"],
            danger_level=4,
        ),
        LocationInfo(
            name="3호선_객차_6",
            description="지하철 6번 객차. 가장 끝 객차로, 문이 보인다.",
            coordinates=SUBWAY_COORDINATES["3호선_객차_6"],
            connected_to=["3호선_객차_5"],
            npcs_count_range=(2, 5),
            items=["비상 망치"],
            danger_level=3,
        ),
        LocationInfo(
            name="3호선_운전실",
            description="지하철 운전실. 문이 잠겨 있다.",
            coordinates=SUBWAY_COORDINATES["3호선_운전실"],
            connected_to=["3호선_객차_1"],
            npcs_count_range=(0, 1),  # 기관사
            items=["운전 매뉴얼", "무전기"],
            danger_level=1,
        ),
        LocationInfo(
            name="지하철_플랫폼",
            description="지하철 플랫폼. 탈출 지점이다.",
            coordinates=SUBWAY_COORDINATES["지하철_플랫폼"],
            connected_to=["3호선_객차_6"],  # 문이 열리면 연결
            npcs_count_range=(0, 3),
            items=[],
            danger_level=2,
        ),
    ])

    # 게임 규칙
    rules: list[str] = Field(default_factory=lambda: [
        "시나리오를 완료하면 코인과 경험치를 획득합니다",
        "코인으로 스킬을 구매하거나 강화할 수 있습니다",
        "레벨업 시 스탯 포인트를 얻습니다",
        "성좌들이 당신의 행동을 지켜보고 후원합니다",
        "시나리오의 조건을 충족하지 못하면 패널티가 있습니다",
        "NPC를 죽이면 코인을 얻지만, 일부 성좌의 반감을 삽니다",
        "체력이 0이 되면 게임 오버입니다",
        "주변을 잘 살피면 해결책을 찾을 수 있습니다",
    ])

    # 아이템 정보
    items_info: dict[str, str] = Field(default_factory=lambda: {
        "빈 음료수 캔": "투척용으로 사용할 수 있다. 데미지 5",
        "신문": "불을 붙일 수 있다.",
        "우산": "근접 무기로 사용 가능. 데미지 10",
        "핸드폰 충전기": "케이블을 무기로 사용할 수 있다. 데미지 5",
        "에코백": "물건을 담을 수 있다.",
        "깨진 유리병": "날카로운 근접 무기. 데미지 20, 출혈 유발 가능",
        "소화기": "무기로 사용하거나 연막을 만들 수 있다. 데미지 25",
        "비상 망치": "유리를 깨는 데 사용. 무기로도 사용 가능. 데미지 30",
        "운전 매뉴얼": "지하철 조작법이 적혀 있다.",
        "무전기": "외부와 통신을 시도할 수 있다.",
        "접이식 칼": "날카로운 근접 무기. 데미지 25, 출혈 유발",
        "쇠파이프": "묵직한 근접 무기. 데미지 30",
        "지팡이": "근접 무기. 데미지 15",
    })
