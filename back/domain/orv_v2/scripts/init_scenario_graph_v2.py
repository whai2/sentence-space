#!/usr/bin/env python3
"""
Neo4j 시나리오 그래프 초기화 스크립트 v2

시나리오 001 "가치 증명" 데이터를 Neo4j에 로드합니다.
Cypher 파일을 읽는 대신 Python에서 직접 쿼리를 실행합니다.
"""
import asyncio
import sys
from pathlib import Path

# Add back directory to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository


async def create_scenario_graph(repo: Neo4jGraphRepository):
    """시나리오 001 그래프 생성"""

    # 1. 시나리오 노드
    print("   [1/9] 시나리오 노드 생성...")
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_001_proof_of_value",
      title: "가치 증명",
      difficulty: "F급",
      description: "별빛 스트림이 연결되고 첫 번째 메인 시나리오가 시작된다. 생명체 하나를 죽여 생존 적합성을 증명해야 한다. 대부분의 사람들은 서로를 죽이려 하지만, 김독자는 원작 지식으로 더 나은 방법을 알고 있다.",
      objective: "생명체를 1개 이상 죽이시오",
      time_limit_turns: 30,
      reward_coins: 300,
      failure_penalty: "사망",
      is_main_scenario: true,
      sequence_order: 1
    })
    """)

    # 2. 캐릭터 노드
    print("   [2/9] 캐릭터 노드 생성...")
    await repo.execute_write("""
    CREATE (biryu:Character {
      character_id: "dokkaebi_biryu",
      name: "비류",
      character_type: "dokkaebi",
      description: "첫 번째 시나리오를 주관하는 하급 도깨비. 작고 까만 몸에 뿔이 하나 달려있다. 공평함을 중시하며 규칙을 엄격히 적용한다. 시나리오 실패자에게는 잔인하지만, 성공자에게는 정당한 보상을 준다.",
      personality_traits: ["공평함", "잔인함", "규칙 중시", "장난스러움"],
      appearance: "작고 까만 몸, 머리에 뿔 하나, 빨간 눈",
      role: "scenario_host",
      base_health: -1,
      base_disposition: "neutral"
    })
    """)

    await repo.execute_write("""
    CREATE (dog_owner:Character {
      character_id: "dog_owner_01",
      name: "견주 아줌마",
      character_type: "civilian",
      description: "작은 강아지(몽이)를 품에 안고 있는 중년 여성. 강아지가 그녀의 전부이며, 절박하게 보호하려 한다. 누군가 강아지를 해치려 하면 격렬히 저항할 것이다.",
      personality_traits: ["보호본능", "절박함", "애정", "방어적"],
      appearance: "중년 여성, 품에 작은 포메라니안을 안고 있음, 불안한 표정",
      role: "potential_victim",
      base_health: 70,
      base_disposition: "terrified"
    })
    """)

    # 3. 아이템 노드 (생명체)
    print("   [3/9] 아이템 노드 생성...")
    await repo.execute_write("""
    CREATE (dog:Item {
      item_id: "creature_dog_mongi",
      name: "몽이",
      item_type: "creature",
      description: "3살 포메라니안. 작고 귀여운 강아지. 생명체이므로 시나리오 조건을 만족시킬 수 있지만, 죽이면 도덕적 문제와 견주의 적대감을 유발한다.",
      base_damage: 0,
      is_alive: true,
      rarity: "common"
    })
    """)

    await repo.execute_write("""
    CREATE (bug_egg:Item {
      item_id: "creature_bug_egg",
      name: "벌레 알",
      item_type: "creature",
      description: "객차 구석 좌석 밑에 있는 작은 벌레 알. 생명체로 간주되며, 쉽게 죽일 수 있다. 대부분의 사람들은 이것을 생각하지 못하지만, 김독자는 원작 지식으로 이 방법을 알고 있다.",
      base_damage: 0,
      is_alive: true,
      rarity: "common"
    })
    """)

    # 4. 위치 노드
    print("   [4/9] 위치 노드 생성...")
    await repo.execute_write("""
    CREATE (car2:Location {
      location_id: "3호선_객차_2",
      name: "3호선 객차 2",
      description: "객차 3의 앞쪽 칸. 다른 승객들이 있다.",
      atmosphere: "긴장된",
      danger_level: 4
    })
    """)

    await repo.execute_write("""
    CREATE (car3:Location {
      location_id: "3호선_객차_3",
      name: "3호선 객차 3",
      description: "지하철 3호선의 세 번째 객차. 플레이어 김독자가 시작하는 위치. 승객들로 붐비며, 시나리오 공지 후 혼란과 공포에 빠진다. 좌석 밑 구석에는 벌레 알이 숨어있다.",
      atmosphere: "혼란스러운",
      danger_level: 4
    })
    """)

    await repo.execute_write("""
    CREATE (car4:Location {
      location_id: "3호선_객차_4",
      name: "3호선 객차 4",
      description: "객차 3의 뒤쪽 칸. 다른 승객들이 있다.",
      atmosphere: "긴장된",
      danger_level: 4
    })
    """)

    # 5. 이벤트 노드
    print("   [5/9] 이벤트 노드 생성...")
    await repo.execute_write("""
    CREATE (e:Event {
      event_id: "event_scenario_announcement",
      event_type: "scenario_start",
      name: "시나리오 공지",
      description: "비류가 객차에 등장하여 푸른 창을 띄우며 첫 번째 시나리오를 공지한다. 모든 승객이 동시에 이 메시지를 본다.",
      trigger_condition: "turn == 1",
      timing: "immediate"
    })
    """)

    await repo.execute_write("""
    CREATE (e:Event {
      event_id: "event_blue_screen_display",
      event_type: "system_message",
      name: "푸른 창 표시",
      description: "시스템 메시지가 푸른 반투명 창으로 모든 사람 앞에 표시된다. 이 창은 시나리오 정보를 담고 있다.",
      trigger_condition: "scenario_start == true",
      timing: "immediate"
    })
    """)

    await repo.execute_write("""
    CREATE (e:Event {
      event_id: "event_panic_outbreak",
      event_type: "crowd_reaction",
      name: "집단 공황",
      description: "시나리오 공지 직후 승객들 사이에 공포와 혼란이 퍼진다. 일부는 울부짖고, 일부는 무기를 찾기 시작한다.",
      trigger_condition: "turn >= 2",
      timing: "delayed"
    })
    """)

    # 6. 규칙 노드
    print("   [6/9] 규칙 노드 생성...")
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_win_condition",
      rule_type: "win_condition",
      description: "생명체 1개 이상을 죽이면 클리어",
      is_hidden: false,
      importance: 10
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_life_definition",
      rule_type: "hidden_trick",
      description: "생명체의 범위: 인간, 동물(강아지, 고양이 등), 벌레, 벌레 알 등 모든 살아있는 존재. 스타 스트림은 벌레 알도 생명체로 인정한다.",
      is_hidden: true,
      importance: 9
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_time_limit",
      rule_type: "fail_condition",
      description: "30분(30턴) 내에 클리어하지 못하면 사망",
      is_hidden: false,
      importance: 10
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_dokkaebi_neutrality",
      rule_type: "system_rule",
      description: "도깨비는 시나리오 진행자이며, 플레이어를 직접 공격하거나 돕지 않는다. 단지 관찰하고 판정한다.",
      is_hidden: false,
      importance: 7
    })
    """)

    # 7. 트릭 노드
    print("   [7/9] 트릭 노드 생성...")
    await repo.execute_write("""
    CREATE (t:Trick {
      trick_id: "trick_bug_kill",
      name: "벌레로 클리어",
      description: "대부분의 사람들은 인간을 죽여야 한다고 생각하지만, 벌레나 벌레 알을 죽여도 클리어할 수 있다. 김독자만이 원작 '멸망한 세계에서 살아남는 세 가지 방법'의 지식으로 이를 알고 있다. 원작에서 주인공 이기수가 벌레를 죽여 첫 시나리오를 통과했다.",
      difficulty_to_discover: 2,
      is_protagonist_knowledge: true,
      narrative_hint: "김독자는 '멸망한 세계에서 살아남는 세 가지 방법'의 첫 장면을 떠올렸다. 이기수는 어떻게 살아남았지? 벌레... 벌레를 죽였다."
    })
    """)

    await repo.execute_write("""
    CREATE (t:Trick {
      trick_id: "trick_dog_kill",
      name: "강아지로 클리어",
      description: "강아지를 죽여서 클리어할 수 있지만, 도덕적으로 큰 문제가 있으며 견주와의 치명적 갈등을 유발한다. 또한 다른 승객들의 적대감을 살 수 있다.",
      difficulty_to_discover: 3,
      is_protagonist_knowledge: false,
      narrative_hint: "품에 강아지를 안고 있는 여성이 보인다. 그 강아지도... 생명체다."
    })
    """)

    # 8. 시스템 메시지 노드
    print("   [8/9] 시스템 메시지 노드 생성...")
    await repo.execute_write("""
    CREATE (msg:SystemMessage {
      message_id: "msg_blue_screen_01",
      message_type: "blue_screen",
      content: "[메인 시나리오 #1 - 가치 증명]\\n\\n목표: 생명체를 1개 이상 죽이시오\\n제한 시간: 30분\\n보상: 300 코인\\n실패: 사망",
      display_timing: "scenario_start",
      is_important: true
    })
    """)

    await repo.execute_write("""
    CREATE (msg:SystemMessage {
      message_id: "msg_dokkaebi_announcement",
      message_type: "notification",
      content: "낄낄낄! 여러분, 환영합니다! 이제부터 첫 번째 시나리오를 시작하겠습니다!",
      display_timing: "before_blue_screen",
      is_important: true
    })
    """)

    await repo.execute_write("""
    CREATE (msg:SystemMessage {
      message_id: "msg_timer_warning",
      message_type: "warning",
      content: "남은 시간: 5분",
      display_timing: "turn_25",
      is_important: true
    })
    """)

    # 9. 스킬 노드
    print("   [9/9] 스킬 노드 생성...")
    await repo.execute_write("""
    CREATE (skill:Skill {
      skill_id: "skill_first_kill",
      name: "첫 번째 살인",
      grade: "희귀",
      description: "생명체를 처음 죽인 자에게 부여되는 스킬. 인간형 적에게 주는 데미지가 증가한다.",
      effect: "인간형 적에게 데미지 10% 증가",
      acquisition_condition: "첫 번째 생명체 살해 (어떤 생명체든)",
      cooldown: 0,
      stamina_cost: 0
    })
    """)

    print("   ✅ 모든 노드 생성 완료")


async def create_relationships(repo: Neo4jGraphRepository):
    """관계 생성"""

    print("   [1/10] 시나리오-캐릭터 관계...")
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_001_proof_of_value"})
    MATCH (biryu:Character {character_id: "dokkaebi_biryu"})
    CREATE (s)-[:APPEARS_IN {role: "host", is_critical: true, appearance_turn: 1}]->(biryu)
    """)

    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_001_proof_of_value"})
    MATCH (dog_owner:Character {character_id: "dog_owner_01"})
    CREATE (s)-[:APPEARS_IN {role: "potential_victim", is_critical: false, appearance_turn: 1}]->(dog_owner)
    """)

    print("   [2/10] 시나리오-규칙 관계...")
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_001_proof_of_value"})
    MATCH (r1:Rule {rule_id: "rule_win_condition"})
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r1)
    """)

    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_001_proof_of_value"})
    MATCH (r2:Rule {rule_id: "rule_life_definition"})
    CREATE (s)-[:REQUIRES {requirement_type: "hidden_knowledge", is_mandatory: false}]->(r2)
    """)

    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_001_proof_of_value"})
    MATCH (r3:Rule {rule_id: "rule_time_limit"})
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r3)
    """)

    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_001_proof_of_value"})
    MATCH (r4:Rule {rule_id: "rule_dokkaebi_neutrality"})
    CREATE (s)-[:REQUIRES {requirement_type: "system_rule", is_mandatory: false}]->(r4)
    """)

    print("   [3/10] 시나리오-보상 관계...")
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_001_proof_of_value"})
    MATCH (skill:Skill {skill_id: "skill_first_kill"})
    CREATE (s)-[:HAS_REWARD {reward_type: "skill", amount: 1}]->(skill)
    """)

    print("   [4/10] 이벤트 트리거 관계...")
    await repo.execute_write("""
    MATCH (e1:Event {event_id: "event_scenario_announcement"})
    MATCH (e2:Event {event_id: "event_blue_screen_display"})
    CREATE (e1)-[:TRIGGERS {condition: "turn == 1", delay_turns: 0, probability: 1.0}]->(e2)
    """)

    await repo.execute_write("""
    MATCH (e2:Event {event_id: "event_blue_screen_display"})
    MATCH (e3:Event {event_id: "event_panic_outbreak"})
    CREATE (e2)-[:TRIGGERS {condition: "immediate", delay_turns: 0, probability: 1.0}]->(e3)
    """)

    print("   [5/10] 이벤트-규칙 공개 관계...")
    await repo.execute_write("""
    MATCH (e2:Event {event_id: "event_blue_screen_display"})
    MATCH (r1:Rule {rule_id: "rule_win_condition"})
    CREATE (e2)-[:REVEALS {reveal_timing: "immediately", visibility: "all"}]->(r1)
    """)

    await repo.execute_write("""
    MATCH (e2:Event {event_id: "event_blue_screen_display"})
    MATCH (r3:Rule {rule_id: "rule_time_limit"})
    CREATE (e2)-[:REVEALS {reveal_timing: "immediately", visibility: "all"}]->(r3)
    """)

    print("   [6/10] 캐릭터-위치 관계...")
    await repo.execute_write("""
    MATCH (dog_owner:Character {character_id: "dog_owner_01"})
    MATCH (car3:Location {location_id: "3호선_객차_3"})
    CREATE (dog_owner)-[:LOCATED_IN {spawn_probability: 1.0, initial_state: "terrified"}]->(car3)
    """)

    await repo.execute_write("""
    MATCH (biryu:Character {character_id: "dokkaebi_biryu"})
    MATCH (car3:Location {location_id: "3호선_객차_3"})
    CREATE (biryu)-[:LOCATED_IN {spawn_probability: 1.0, initial_state: "observing"}]->(car3)
    """)

    print("   [7/10] 아이템-위치 관계...")
    await repo.execute_write("""
    MATCH (dog:Item {item_id: "creature_dog_mongi"})
    MATCH (car3:Location {location_id: "3호선_객차_3"})
    CREATE (dog)-[:LOCATED_IN {spawn_probability: 1.0, initial_state: "held_by_owner"}]->(car3)
    """)

    await repo.execute_write("""
    MATCH (bug_egg:Item {item_id: "creature_bug_egg"})
    MATCH (car3:Location {location_id: "3호선_객차_3"})
    CREATE (bug_egg)-[:LOCATED_IN {spawn_probability: 0.8, initial_state: "hidden"}]->(car3)
    """)

    print("   [8/10] 위치 연결 관계...")
    await repo.execute_write("""
    MATCH (car2:Location {location_id: "3호선_객차_2"})
    MATCH (car3:Location {location_id: "3호선_객차_3"})
    CREATE (car3)-[:CONNECTED_TO {direction: "forward", distance: 1, is_locked: false}]->(car2)
    """)

    await repo.execute_write("""
    MATCH (car3:Location {location_id: "3호선_객차_3"})
    MATCH (car4:Location {location_id: "3호선_객차_4"})
    CREATE (car3)-[:CONNECTED_TO {direction: "backward", distance: 1, is_locked: false}]->(car4)
    """)

    await repo.execute_write("""
    MATCH (car2:Location {location_id: "3호선_객차_2"})
    MATCH (car3:Location {location_id: "3호선_객차_3"})
    CREATE (car2)-[:CONNECTED_TO {direction: "backward", distance: 1, is_locked: false}]->(car3)
    """)

    await repo.execute_write("""
    MATCH (car3:Location {location_id: "3호선_객차_3"})
    MATCH (car4:Location {location_id: "3호선_객차_4"})
    CREATE (car4)-[:CONNECTED_TO {direction: "forward", distance: 1, is_locked: false}]->(car3)
    """)

    print("   [9/10] 규칙-트릭 관계...")
    await repo.execute_write("""
    MATCH (r2:Rule {rule_id: "rule_life_definition"})
    MATCH (t1:Trick {trick_id: "trick_bug_kill"})
    CREATE (r2)-[:ALTERNATIVE_SOLUTION {difficulty: 1, morality_score: 8}]->(t1)
    """)

    await repo.execute_write("""
    MATCH (r2:Rule {rule_id: "rule_life_definition"})
    MATCH (t2:Trick {trick_id: "trick_dog_kill"})
    CREATE (r2)-[:ALTERNATIVE_SOLUTION {difficulty: 3, morality_score: 2}]->(t2)
    """)

    print("   [10/10] 캐릭터 충돌 관계...")
    await repo.execute_write("""
    MATCH (dog_owner:Character {character_id: "dog_owner_01"})
    MATCH (dog:Item {item_id: "creature_dog_mongi"})
    CREATE (dog_owner)-[:CONFLICTS_WITH {conflict_type: "life_or_death", intensity: 10}]->(dog)
    """)

    print("   ✅ 모든 관계 생성 완료")


async def main():
    """시나리오 그래프 초기화"""

    print("=" * 60)
    print("Neo4j 시나리오 그래프 초기화 시작 (v2)")
    print("=" * 60)

    # Neo4j 연결
    repo = Neo4jGraphRepository(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )

    try:
        # 1. 연결 확인
        print("\n[1/5] Neo4j 연결 확인 중...")
        is_connected = await repo.verify_connectivity()
        if not is_connected:
            print("❌ Neo4j 연결 실패. Docker Compose가 실행 중인지 확인하세요.")
            print("   → docker-compose up -d neo4j")
            return
        print("✅ Neo4j 연결 성공")

        # 2. 기존 데이터 삭제 (개발용)
        print("\n[2/5] 기존 데이터 삭제 중...")
        await repo.clear_all_data()
        print("✅ 기존 데이터 삭제 완료")

        # 3. 제약 조건 생성
        print("\n[3/5] 제약 조건 생성 중...")
        await repo.create_constraints()
        print("✅ 제약 조건 생성 완료")

        # 4. 노드 생성
        print("\n[4/5] 시나리오 001 노드 생성 중...")
        await create_scenario_graph(repo)

        # 5. 관계 생성
        print("\n[5/5] 시나리오 001 관계 생성 중...")
        await create_relationships(repo)

        # 6. 데이터 검증
        print("\n" + "=" * 60)
        print("데이터 검증 중...")
        print("=" * 60)
        node_counts = await repo.get_node_count()

        print("\n노드 타입별 개수:")
        for label, count in sorted(node_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {label:20s}: {count:3d}개")

        # 시나리오 정보 조회
        print("\n" + "=" * 60)
        print("시나리오 정보 확인:")
        print("=" * 60)
        scenario = await repo.get_scenario_by_id("scenario_001_proof_of_value")
        if scenario:
            print(f"  - 제목: {scenario.get('title')}")
            print(f"  - 난이도: {scenario.get('difficulty')}")
            print(f"  - 목표: {scenario.get('objective')}")
            print(f"  - 제한 시간: {scenario.get('time_limit_turns')}턴")

        # 주인공 전용 트릭 조회
        tricks = await repo.get_protagonist_tricks("scenario_001_proof_of_value")
        if tricks:
            print("\n" + "=" * 60)
            print("주인공 전용 트릭:")
            print("=" * 60)
            for trick in tricks:
                print(f"  - {trick['name']}")
                print(f"    설명: {trick['description'][:60]}...")
                print(f"    난이도: {trick['difficulty']}, 도덕성: {trick['morality_score']}/10")

        print("\n" + "=" * 60)
        print("✅ 초기화 완료!")
        print("=" * 60)
        print("\nNeo4j 브라우저에서 확인:")
        print("  → http://localhost:7474")
        print("\n쿼리 예시:")
        print("  MATCH (n) RETURN n LIMIT 25")
        print("  MATCH (s:Scenario)-[:REQUIRES]->(r:Rule)-[:ALTERNATIVE_SOLUTION]->(t:Trick)")
        print("  RETURN s, r, t")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 연결 종료
        await repo.close()
        print("\n✅ Neo4j 연결 종료")


if __name__ == "__main__":
    asyncio.run(main())
