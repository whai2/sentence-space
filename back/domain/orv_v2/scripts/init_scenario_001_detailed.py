"""
시나리오 #1 "가치증명" 상세 지식 그래프 초기화

나무위키 분석 결과를 바탕으로 Neo4j에 상세한 스토리 구조 저장
"""
import asyncio
from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository
from server.config import get_settings


async def init_scenario_001_detailed():
    """시나리오 1 "가치증명" 상세 초기화"""

    settings = get_settings()
    neo4j_uri = getattr(settings, "neo4j_uri", "bolt://localhost:7687")
    neo4j_username = getattr(settings, "neo4j_username", "neo4j")
    neo4j_password = getattr(settings, "neo4j_password", "password")

    repo = Neo4jGraphRepository(
        uri=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password
    )

    # ============================================
    # 1. 시나리오 노드 생성
    # ============================================

    scenario_data = {
        "scenario_id": "scenario_1",
        "title": "가치 증명",
        "difficulty": "D급",
        "objective": "생명체 1개 이상 살해",
        "time_limit_minutes": 10,  # 원래 30분 → 도깨비 개입으로 10분
        "reward_coins": 2700,
        "reward_exp": 100,
        "description": "시나리오 할당 구역 내 모든 인간들은 제한 시간 내 최소 1개 이상의 생명체를 살해해야 한다. 시간 내 목표 달성 실패 시 즉시 사망."
    }

    await repo.create_scenario(scenario_data)

    # ============================================
    # 2. 스토리 페이즈 (7단계) 생성
    # ============================================

    phases = [
        {
            "phase_id": "phase_1",
            "phase_name": "일상의 균열",
            "description": "김독자가 멸살법 최종화를 읽고, 지하철이 급정거한다.",
            "target_turn_start": 0,
            "target_turn_end": 2,
            "completion_condition": "지하철 정지",
            "narrative_tone": "calm",
            "order": 1
        },
        {
            "phase_id": "phase_2",
            "phase_name": "도깨비 출현 & 채널 개방",
            "description": "도깨비 비형이 등장하고, 성좌들이 지켜보는 가운데 시나리오가 시작된다.",
            "target_turn_start": 3,
            "target_turn_end": 5,
            "completion_condition": "시나리오 도착",
            "narrative_tone": "tense",
            "order": 2
        },
        {
            "phase_id": "phase_3",
            "phase_name": "정보 수집 및 규칙 파악",
            "description": "김독자는 게임의 규칙을 찾으려 하고, 이현성이 통제를 시도한다. 태풍여고 영상이 전송되며 시간이 10분으로 단축된다.",
            "target_turn_start": 6,
            "target_turn_end": 8,
            "completion_condition": "규칙 이해",
            "narrative_tone": "tense",
            "order": 3
        },
        {
            "phase_id": "phase_4",
            "phase_name": "첫 갈등",
            "description": "김남운이 할머니를 폭행하고, 집단린치가 발생한다.",
            "target_turn_start": 9,
            "target_turn_end": 11,
            "completion_condition": "폭력 발생",
            "narrative_tone": "desperate",
            "order": 4
        },
        {
            "phase_id": "phase_5",
            "phase_name": "김독자의 개입",
            "description": "김독자가 메뚜기 상자를 발견하고, 시나리오의 허점을 찾는다.",
            "target_turn_start": 12,
            "target_turn_end": 14,
            "completion_condition": "메뚜기 발견",
            "narrative_tone": "hopeful",
            "order": 5
        },
        {
            "phase_id": "phase_6",
            "phase_name": "김독자 vs 김남운 대결",
            "description": "김독자와 김남운이 메뚜기를 두고 대결한다. 스킬 대결 후 김독자가 메뚜기 알을 대량 살해한다.",
            "target_turn_start": 15,
            "target_turn_end": 17,
            "completion_condition": "대결 종료",
            "narrative_tone": "tense",
            "order": 6
        },
        {
            "phase_id": "phase_7",
            "phase_name": "시나리오 종료",
            "description": "시간이 경과하고 다수가 사망한다. 생존자는 5명으로 확정된다.",
            "target_turn_start": 18,
            "target_turn_end": 20,
            "completion_condition": "시나리오 완료",
            "narrative_tone": "calm",
            "order": 7
        }
    ]

    for phase in phases:
        await repo.create_phase("scenario_1", phase)

    # ============================================
    # 3. 주요 캐릭터 생성
    # ============================================

    characters = [
        {
            "character_id": "kim_dokja",
            "name": "김독자",
            "character_type": "protagonist",
            "description": "멸살법을 10년간 읽은 유일한 독자. 원작 지식을 보유하고 있어 다른 사람들과 다른 선택을 한다.",
            "role": "게임의 규칙을 찾는 자",
            "personality_traits": ["냉정함", "전략적 사고", "생존 우선", "도덕적"],
            "appearance": "평범한 회사원 외모"
        },
        {
            "character_id": "dokkaebi_bihyung",
            "name": "비형",
            "character_type": "dokkaebi",
            "description": "시나리오를 진행하는 도깨비. 한글 패치를 완료하고 인간들에게 시나리오를 부여한다.",
            "role": "scenario_host",
            "personality_traits": ["장난기", "잔인함", "규칙 준수"],
            "appearance": "작은 뿔을 가진 인간형 도깨비"
        },
        {
            "character_id": "kim_namwoon",
            "name": "김남운",
            "character_type": "antagonist",
            "description": "중2병 소년. 멸망을 기다려온 타입으로 빠른 적응력을 보인다.",
            "role": "potential_threat",
            "personality_traits": ["폭력적", "냉혈", "적응력 높음"],
            "appearance": "고등학생 외모"
        },
        {
            "character_id": "yoo_sangah",
            "name": "유상아",
            "character_type": "ally",
            "description": "김독자의 회사 동료. 정직원으로 승진했다.",
            "role": "ally",
            "personality_traits": ["착함", "신중함"],
            "appearance": "회사원"
        },
        {
            "character_id": "lee_hyunsung",
            "name": "이현성",
            "character_type": "support",
            "description": "군 중위. 원작의 조연. 상황을 통제하려 한다.",
            "role": "leader_attempt",
            "personality_traits": ["책임감", "리더십", "정의로움"],
            "appearance": "군인"
        },
        {
            "character_id": "han_myungoh",
            "name": "한명오",
            "character_type": "civilian",
            "description": "회사 부장. 할머니를 보호하려 했다.",
            "role": "moral_compass",
            "personality_traits": ["도덕적", "용기"],
            "appearance": "중년 남성"
        }
    ]

    for char in characters:
        await repo.create_character("scenario_1", char)

    # ============================================
    # 4. 주요 이벤트 생성
    # ============================================

    events = [
        {
            "event_id": "event_1_subway_stop",
            "phase_id": "phase_1",
            "description": "지하철이 급정거한다.",
            "key_characters": ["kim_dokja"],
            "narrative_hints": ["지하철이 멈췄다.", "사람들은 아직 아무것도 모른다."]
        },
        {
            "event_id": "event_2_dokkaebi_appear",
            "phase_id": "phase_2",
            "description": "도깨비 비형이 등장한다.",
            "key_characters": ["dokkaebi_bihyung"],
            "narrative_hints": ["작은 뿔을 가진 생명체가 나타났다.", "한글 패치가 완료되었습니다."]
        },
        {
            "event_id": "event_3_channel_open",
            "phase_id": "phase_2",
            "description": "#BI-7623 채널이 개방되고 성좌들이 입장한다.",
            "key_characters": ["dokkaebi_bihyung"],
            "narrative_hints": ["[#BI-7623 채널이 개방되었습니다.]", "무수한 시선이 느껴진다."]
        },
        {
            "event_id": "event_4_scenario_arrive",
            "phase_id": "phase_2",
            "description": "모든 탑승자에게 시나리오가 도착한다.",
            "key_characters": ["dokkaebi_bihyung"],
            "narrative_hints": ["푸른 창이 눈앞에 떴다.", "[메인 시나리오 #1 - 가치 증명]"]
        },
        {
            "event_id": "event_5_rule_discovery",
            "phase_id": "phase_3",
            "description": "김독자가 게임의 규칙을 찾자고 제안한다.",
            "key_characters": ["kim_dokja"],
            "narrative_hints": ["'모든 게임에는 규칙이 있다.'", "김독자는 냉정하게 생각했다."]
        },
        {
            "event_id": "event_6_time_reduction",
            "phase_id": "phase_3",
            "description": "도깨비가 시간을 10분으로 단축한다.",
            "key_characters": ["dokkaebi_bihyung"],
            "narrative_hints": ["이건 테러와 같은 장난이 아니라.", "남은 시간이 10분으로 줄어들었다."]
        },
        {
            "event_id": "event_7_violence_start",
            "phase_id": "phase_4",
            "description": "김남운이 할머니를 폭행하기 시작한다.",
            "key_characters": ["kim_namwoon"],
            "narrative_hints": ["비명소리가 들렸다.", "김남운의 눈에는 광기가 서려 있었다."]
        },
        {
            "event_id": "event_8_cricket_discovery",
            "phase_id": "phase_5",
            "description": "김독자가 메뚜기 상자를 발견한다.",
            "key_characters": ["kim_dokja"],
            "narrative_hints": ["상자 안에서 무언가가 움직였다.", "'이걸로 되는 건가?'"]
        },
        {
            "event_id": "event_9_confrontation",
            "phase_id": "phase_6",
            "description": "김독자와 김남운이 대결한다.",
            "key_characters": ["kim_dokja", "kim_namwoon"],
            "narrative_hints": ["칼날이 번쩍였다.", "스킬 [흑화]가 발동되었다."]
        },
        {
            "event_id": "event_10_cricket_kill",
            "phase_id": "phase_6",
            "description": "김독자가 메뚜기 알을 대량 살해한다.",
            "key_characters": ["kim_dokja"],
            "narrative_hints": ["[생명체를 살해했습니다.]", "메시지가 연속으로 떴다."]
        },
        {
            "event_id": "event_11_scenario_end",
            "phase_id": "phase_7",
            "description": "시나리오가 종료되고 생존자가 확정된다.",
            "key_characters": ["kim_dokja", "yoo_sangah", "han_myungoh", "lee_hyunsung"],
            "narrative_hints": ["[시나리오가 종료되었습니다.]", "침묵이 흘렀다."]
        }
    ]

    for event in events:
        await repo.create_event("scenario_1", event)

    # ============================================
    # 5. 규칙 (Rules) 생성
    # ============================================

    rules = [
        {
            "rule_id": "rule_win_condition",
            "rule_type": "win_condition",
            "description": "제한 시간 내 생명체 1개 이상 살해",
            "is_hidden": False,
            "importance": 10
        },
        {
            "rule_id": "rule_fail_condition",
            "rule_type": "fail_condition",
            "description": "제한 시간 내 살해 미달성 시 즉시 사망",
            "is_hidden": False,
            "importance": 10
        },
        {
            "rule_id": "rule_hidden_trick",
            "rule_type": "hidden_trick",
            "description": "살해 대상은 '인간'으로 제한되지 않음. 모든 생명체 포함.",
            "is_hidden": True,
            "importance": 9
        },
        {
            "rule_id": "rule_time_limit",
            "rule_type": "system_rule",
            "description": "제한 시간 10분 (원래 30분이었으나 도깨비 개입으로 단축)",
            "is_hidden": False,
            "importance": 8
        }
    ]

    for rule in rules:
        await repo.create_rule("scenario_1", rule)

    # ============================================
    # 6. 트릭 (Tricks) - 김독자만 아는 지식
    # ============================================

    tricks = [
        {
            "trick_id": "trick_cricket",
            "name": "메뚜기 상자 활용",
            "description": "객차 안에 있는 메뚜기 상자를 이용하여 '생명체' 조건을 충족할 수 있다. 메뚜기 알도 생명체로 인정된다.",
            "difficulty_to_discover": 7,
            "is_protagonist_knowledge": True,
            "narrative_hint": "김독자는 원작 지식으로 메뚜기 상자의 존재를 알고 있었다.",
            "morality_score": 9
        },
        {
            "trick_id": "trick_rule_loophole",
            "name": "규칙의 허점",
            "description": "시나리오는 '생명체 살해'만 요구하며, 인간 살해를 강제하지 않는다.",
            "difficulty_to_discover": 8,
            "is_protagonist_knowledge": True,
            "narrative_hint": "'생명체'라고 했지, '인간'이라고는 하지 않았다.",
            "morality_score": 10
        },
        {
            "trick_id": "trick_lee_hyunsung",
            "name": "이현성의 정체",
            "description": "이현성은 원작의 조연으로, 나중에 중요한 동료가 된다.",
            "difficulty_to_discover": 5,
            "is_protagonist_knowledge": True,
            "narrative_hint": "김독자는 이현성을 알고 있었다.",
            "morality_score": 7
        }
    ]

    for trick in tricks:
        await repo.create_trick("scenario_1", trick)

    # ============================================
    # 7. 위치 (Locations) 생성
    # ============================================

    locations = [
        {
            "location_id": "loc_subway_car_3",
            "name": "3호선 객차 3",
            "description": "김독자가 탑승한 객차. 약 40명의 승객이 있다.",
            "atmosphere": "밀폐되고 압박감 있는 공간",
            "danger_level": 8
        }
    ]

    for loc in locations:
        await repo.create_location("scenario_1", loc)

    print("✅ 시나리오 #1 '가치증명' 상세 지식 그래프 초기화 완료!")

    # 연결 종료
    await repo.close()


if __name__ == "__main__":
    asyncio.run(init_scenario_001_detailed())
