"""
스토리 프리셋 - 시나리오별 초기 복선 및 아크 템플릿

수동 정의 방식으로 각 시나리오에 맞는 복선을 사전 설정합니다.
"""

from domain.orv.model import (
    PlotPoint,
    PlotPointType,
    PlotPointStatus,
    StoryArc,
    StoryPhase,
)


# ============================================================================
# 시나리오 1: 지하철 3호선 - 초기 복선
# ============================================================================

SCENARIO_1_INITIAL_PLOT_POINTS: list[PlotPoint] = [
    # 환경 힌트: 시나리오 해결의 간접적 단서 (강아지 관련)
    PlotPoint(
        plot_point_id="pp_dog_hint_1",
        point_type=PlotPointType.FORESHADOWING,
        seed_description="어딘가에서 들리는 낑낑거리는 소리",
        seed_narrative="공포스러운 비명 사이로, 어딘가에서 작은 동물이 낑낑거리는 소리가 희미하게 들린다.",
        payoff_description="강아지를 안고 있는 승객을 발견",
        turn_planted=1,
        min_turns_before_payoff=1,
        max_turns_before_payoff=10,
        importance=6,
        related_location="3호선_객차_3",
        keywords=["소리", "동물", "낑낑", "강아지", "살피", "주변"],
    ),
    PlotPoint(
        plot_point_id="pp_dog_hint_2",
        point_type=PlotPointType.CHARACTER_SEED,
        seed_description="뭔가를 품에 안고 있는 여성",
        seed_narrative="객차 한쪽 구석에 중년 여성이 웅크리고 있다. 품에 뭔가를 꼭 안고 있는 것 같다.",
        payoff_description="여성이 강아지를 안고 있다는 것을 발견",
        turn_planted=1,
        min_turns_before_payoff=1,
        max_turns_before_payoff=8,
        importance=7,
        keywords=["여성", "품", "안고", "대화", "관찰", "살피"],
    ),
    PlotPoint(
        plot_point_id="pp_life_definition",
        point_type=PlotPointType.MYSTERY,
        seed_description="'생명체'의 정의에 대한 의문",
        seed_narrative="'생명체 하나를 죽이시오.' 시스템 창의 문구가 머릿속을 맴돈다. 생명체... 그게 꼭 사람이어야 할까?",
        payoff_description="생명체의 범위가 넓다는 것을 깨달음",
        turn_planted=1,
        min_turns_before_payoff=2,
        max_turns_before_payoff=15,
        importance=7,
        keywords=["생명체", "죽이", "시나리오", "의미", "정의", "범위", "동물"],
    ),
    PlotPoint(
        plot_point_id="pp_dog_owner_desperation",
        point_type=PlotPointType.THEME_ECHO,
        seed_description="강아지 주인의 절박함",
        seed_narrative="'제발... 우리 몽이만은...' 여성의 떨리는 목소리가 들린다. 그녀에게는 그 강아지가 전부인 것 같다.",
        payoff_description="도덕적 딜레마 - 강아지를 죽일 것인가",
        turn_planted=2,
        min_turns_before_payoff=2,
        max_turns_before_payoff=12,
        importance=8,
        related_npc_ids=["dog_owner"],
        keywords=["강아지", "몽이", "주인", "여성", "지키", "보호"],
    ),

    # CHEKHOV_GUN: 나중에 반드시 사용될 아이템/디테일
    PlotPoint(
        plot_point_id="pp_emergency_hammer",
        point_type=PlotPointType.CHEKHOV_GUN,
        seed_description="6호차에 비상 망치가 있다",
        seed_narrative="저 멀리 6호차 벽면에 빨간 비상 망치가 보인다.",
        payoff_description="비상 망치로 창문을 깨고 탈출구 생성",
        turn_planted=1,
        min_turns_before_payoff=5,
        max_turns_before_payoff=25,
        importance=8,
        related_location="3호선_객차_6",
        related_item_ids=["emergency_hammer"],
        keywords=["망치", "비상", "탈출", "창문", "깨"],
    ),
    PlotPoint(
        plot_point_id="pp_emergency_exit",
        point_type=PlotPointType.CHEKHOV_GUN,
        seed_description="기관실 옆 비상 탈출구",
        seed_narrative="열차 앞쪽 기관실 근처에 비상 탈출 표시가 희미하게 보인다.",
        payoff_description="비상 탈출구를 통해 터널로 탈출",
        turn_planted=1,
        min_turns_before_payoff=8,
        max_turns_before_payoff=30,
        importance=9,
        related_location="3호선_기관실",
        keywords=["탈출구", "비상", "기관실", "터널"],
    ),

    # CHARACTER_SEED: 캐릭터 특성/배경 힌트
    PlotPoint(
        plot_point_id="pp_soldier_leadership",
        point_type=PlotPointType.CHARACTER_SEED,
        seed_description="이병장의 군인 리더십",
        seed_narrative="군복을 입은 남자가 침착하게 주변을 살피며 상황을 파악하고 있다.",
        payoff_description="이병장이 생존자들을 이끌고 조직적인 탈출 시도",
        turn_planted=2,
        min_turns_before_payoff=4,
        max_turns_before_payoff=15,
        importance=7,
        related_npc_ids=["soldier_1"],
        keywords=["이병장", "군인", "리더", "지휘", "조직"],
    ),
    PlotPoint(
        plot_point_id="pp_student_secret",
        point_type=PlotPointType.CHARACTER_SEED,
        seed_description="여고생의 숨겨진 능력",
        seed_narrative="교복을 입은 소녀가 무언가를 중얼거리며 손가락으로 허공에 글자를 쓰고 있다.",
        payoff_description="여고생이 숨겨진 스킬 발현",
        turn_planted=2,
        min_turns_before_payoff=6,
        max_turns_before_payoff=20,
        importance=6,
        related_npc_ids=["student_1"],
        keywords=["여고생", "학생", "스킬", "능력"],
    ),

    # FORESHADOWING: 미래 이벤트 암시
    PlotPoint(
        plot_point_id="pp_insect_wave",
        point_type=PlotPointType.FORESHADOWING,
        seed_description="더 큰 벌레 떼의 존재",
        seed_narrative="터널 깊은 곳에서 들려오는 소리가 점점 커지고 있다. 마치 수천 마리가 다가오는 듯...",
        payoff_description="대규모 벌레 떼 습격",
        turn_planted=3,
        min_turns_before_payoff=5,
        max_turns_before_payoff=15,
        importance=8,
        keywords=["벌레", "소리", "터널", "떼"],
    ),
    PlotPoint(
        plot_point_id="pp_constellation_interest",
        point_type=PlotPointType.FORESHADOWING,
        seed_description="성좌들의 관심",
        seed_narrative="어딘가에서 당신을 지켜보는 수많은 시선이 느껴진다.",
        payoff_description="강력한 성좌의 직접 개입",
        turn_planted=1,
        min_turns_before_payoff=3,
        max_turns_before_payoff=12,
        importance=7,
        keywords=["성좌", "시선", "후원", "관심"],
    ),

    # MYSTERY: 미해결 질문
    PlotPoint(
        plot_point_id="pp_why_scenario",
        point_type=PlotPointType.MYSTERY,
        seed_description="왜 시나리오가 시작되었나",
        seed_narrative="갑자기 시작된 이 악몽 같은 상황... 도대체 왜?",
        payoff_description="시나리오 시스템의 본질 일부 드러남",
        turn_planted=1,
        min_turns_before_payoff=10,
        max_turns_before_payoff=50,
        importance=5,
        keywords=["시나리오", "시작", "이유", "왜"],
    ),

    # THEME_ECHO: 주제 강화
    PlotPoint(
        plot_point_id="pp_survival_choice",
        point_type=PlotPointType.THEME_ECHO,
        seed_description="생존을 위한 선택의 무게",
        seed_narrative="누군가를 구하기 위해 다른 누군가를 버려야 할 수도 있다는 생각이 스쳐 지나간다.",
        payoff_description="실제로 어려운 선택의 순간이 찾아옴",
        turn_planted=3,
        min_turns_before_payoff=5,
        max_turns_before_payoff=20,
        importance=6,
        keywords=["선택", "생존", "희생", "구하"],
    ),
]


def create_scenario_1_arc(
    start_turn: int = 0,
    with_plot_points: bool = True,
) -> StoryArc:
    """
    시나리오 1 (지하철 3호선)용 스토리 아크 생성.

    Args:
        start_turn: 아크 시작 턴
        with_plot_points: 초기 복선 포함 여부

    Returns:
        설정된 StoryArc
    """
    arc = StoryArc(
        arc_id="scenario_1_main",
        title="지하철 3호선 생존",
        description="갑자기 시작된 시나리오. 지하철 안에서 벌레 괴물들과 싸우며 생존해야 한다.",
        start_turn=start_turn,
        current_phase=StoryPhase.EXPOSITION,
        custom_tone_guidance={
            # 커스텀 톤 가이드 (기본값 오버라이드)
            "exposition": "지하철 내부의 일상적인 분위기에서 시작. 점차 이상함을 느끼게 유도.",
            "inciting_incident": "시나리오 시작과 함께 혼돈. 첫 번째 괴물 등장의 충격.",
            "rising_action": "생존을 위한 분투. NPC들과의 관계 형성. 새로운 위협 등장.",
            "midpoint": "중요한 발견 또는 반전. 탈출 가능성 또는 더 큰 위험 인지.",
            "complications": "상황 악화. NPC 사망 가능. 자원 부족. 내부 갈등.",
            "crisis": "절체절명의 위기. 모든 것이 불가능해 보이는 순간.",
            "climax": "최종 탈출 시도 또는 보스 대결.",
            "falling_action": "탈출 성공/실패 직후. 생존자 확인.",
            "resolution": "시나리오 완료. 보상. 다음으로의 전환.",
        },
    )

    # 초기 복선 추가
    if with_plot_points:
        for pp in SCENARIO_1_INITIAL_PLOT_POINTS:
            # 복선 복사 (원본 수정 방지)
            arc.add_plot_point(pp.model_copy(deep=True))

    return arc


# ============================================================================
# 복선 템플릿 (동적 생성용)
# ============================================================================


def create_npc_death_foreshadowing(
    npc_id: str,
    npc_name: str,
    turn: int,
    danger_hint: str,
) -> PlotPoint:
    """NPC 사망 복선 생성"""
    return PlotPoint(
        plot_point_id=f"pp_death_foreshadow_{npc_id}",
        point_type=PlotPointType.FORESHADOWING,
        seed_description=f"{npc_name}의 위험 암시",
        seed_narrative=danger_hint,
        payoff_description=f"{npc_name}이(가) 위기에 처하거나 사망",
        turn_planted=turn,
        min_turns_before_payoff=2,
        max_turns_before_payoff=8,
        importance=7,
        related_npc_ids=[npc_id],
        keywords=[npc_name, "위험", "죽음", "희생"],
    )


def create_item_discovery_chekhov(
    item_id: str,
    item_name: str,
    location: str,
    turn: int,
    hint_narrative: str,
    use_description: str,
) -> PlotPoint:
    """아이템 발견 체호프의 총 생성"""
    return PlotPoint(
        plot_point_id=f"pp_chekhov_{item_id}",
        point_type=PlotPointType.CHEKHOV_GUN,
        seed_description=f"{location}에 {item_name}이(가) 있다",
        seed_narrative=hint_narrative,
        payoff_description=use_description,
        turn_planted=turn,
        min_turns_before_payoff=3,
        max_turns_before_payoff=15,
        importance=6,
        related_location=location,
        related_item_ids=[item_id],
        keywords=[item_name, "아이템", "발견", "사용"],
    )


def create_npc_secret_seed(
    npc_id: str,
    npc_name: str,
    secret_type: str,
    hint_narrative: str,
    revelation: str,
    turn: int,
    importance: int = 6,
) -> PlotPoint:
    """NPC 비밀 복선 생성"""
    return PlotPoint(
        plot_point_id=f"pp_secret_{npc_id}",
        point_type=PlotPointType.CHARACTER_SEED,
        seed_description=f"{npc_name}의 숨겨진 {secret_type}",
        seed_narrative=hint_narrative,
        payoff_description=revelation,
        turn_planted=turn,
        min_turns_before_payoff=4,
        max_turns_before_payoff=18,
        importance=importance,
        related_npc_ids=[npc_id],
        keywords=[npc_name, secret_type, "비밀", "숨겨진"],
    )
