#!/usr/bin/env python3
"""
Neo4j 시나리오 그래프 초기화 - 시나리오 002~005

시나리오 002 "조우" ~ 005 "범람의 재앙" 데이터를 Neo4j에 로드합니다.
"""
import asyncio
import sys
from pathlib import Path

# Add back directory to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository


async def create_scenario_002(repo: Neo4jGraphRepository):
    """시나리오 002: 조우"""
    print("   [시나리오 002] 조우 생성 중...")

    # 시나리오 노드
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_002_encounter",
      title: "조우",
      difficulty: "E급",
      description: "터널을 통과하여 첫 거점 지역의 생존자와 만나야 한다. 이동 중 다양한 위험 요소가 존재하며, 생존자와의 첫 만남이 향후 진행에 중요한 영향을 미친다.",
      objective: "터널을 주파해 첫 거점 지역의 생존자와 만나시오",
      time_limit_turns: null,
      reward_coins: 500,
      failure_penalty: "불명",
      is_main_scenario: true,
      sequence_order: 2
    })
    """)

    # 위치 노드
    await repo.execute_write("""
    CREATE (loc:Location {
      location_id: "지하철_터널",
      name: "지하철 터널",
      description: "어둡고 위험한 지하철 터널. 생존자들이 이동하는 주요 경로이며, 괴물이 출몰할 수 있다.",
      atmosphere: "어둡고 위험한",
      danger_level: 5
    })
    """)

    await repo.execute_write("""
    CREATE (loc:Location {
      location_id: "첫_거점_지역",
      name: "첫 거점 지역",
      description: "생존자들이 모여 있는 첫 번째 거점. 충무로역으로 추정된다.",
      atmosphere: "혼잡한",
      danger_level: 3
    })
    """)

    # 규칙 노드
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_002_encounter_condition",
      rule_type: "win_condition",
      description: "생존자와 만나면 클리어",
      is_hidden: false,
      importance: 10
    })
    """)

    # 관계 생성
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_002_encounter"})
    MATCH (r:Rule {rule_id: "rule_002_encounter_condition"})
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r)
    """)

    print("   ✅ 시나리오 002 완료")


async def create_scenario_003(repo: Neo4jGraphRepository):
    """시나리오 003: 그린 존"""
    print("   [시나리오 003] 그린 존 생성 중...")

    # 시나리오 노드
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_003_green_zone",
      title: "그린 존",
      difficulty: "C급",
      description: "그린 존을 차지하여 7일간 자정마다 몰려드는 괴물로부터 살아남아야 한다. 시간이 지날수록 안전 지역이 축소되며, 4일차에 변칙 상황이 발생한다.",
      objective: "그린 존을 차지하여 자정마다 몰려드는 괴물로부터 살아남으시오",
      time_limit_turns: 168,
      reward_coins: 1000,
      failure_penalty: "사망",
      is_main_scenario: true,
      sequence_order: 3
    })
    """)

    # 위치 노드
    await repo.execute_write("""
    CREATE (loc:Location {
      location_id: "충무로역_그린존",
      name: "충무로역 그린 존",
      description: "7일간 괴물의 공격으로부터 방어해야 하는 안전 지역. 시간이 지날수록 범위가 축소된다.",
      atmosphere: "긴박한",
      danger_level: 6
    })
    """)

    # 규칙 노드
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_003_survive_7_days",
      rule_type: "win_condition",
      description: "7일간 그린 존에서 생존하면 클리어",
      is_hidden: false,
      importance: 10
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_003_zone_shrinking",
      rule_type: "system_rule",
      description: "시간 경과에 따라 안전 지역이 축소된다. 4일차에 특별한 변칙이 발생한다.",
      is_hidden: false,
      importance: 8
    })
    """)

    # 관계 생성
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_003_green_zone"})
    MATCH (r1:Rule {rule_id: "rule_003_survive_7_days"})
    MATCH (r2:Rule {rule_id: "rule_003_zone_shrinking"})
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r1)
    CREATE (s)-[:REQUIRES {requirement_type: "system_rule", is_mandatory: false}]->(r2)
    """)

    print("   ✅ 시나리오 003 완료")


async def create_scenario_004(repo: Neo4jGraphRepository):
    """시나리오 004: 깃발 쟁탈전"""
    print("   [시나리오 004] 깃발 쟁탈전 생성 중...")

    # 시나리오 노드
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_004_flag_war",
      title: "깃발 쟁탈전",
      difficulty: "C급",
      description: "12일 동안 표적 역인 창신역의 깃발 꽂이를 점거해야 한다. 대표를 선출하고 세력 간 영역 쟁탈전을 벌인다. 깃발 탈취 시스템이 도입된다.",
      objective: "표적 역의 깃발 꽂이를 점거하기 (창신역)",
      time_limit_turns: 288,
      reward_coins: 2000,
      failure_penalty: "전원 사망",
      is_main_scenario: true,
      sequence_order: 4
    })
    """)

    # 위치 노드
    await repo.execute_write("""
    CREATE (loc:Location {
      location_id: "창신역",
      name: "창신역",
      description: "깃발 쟁탈전의 표적 역. 깃발 꽂이가 있으며, 이곳을 점거하는 것이 목표다.",
      atmosphere: "전쟁터",
      danger_level: 7
    })
    """)

    # 규칙 노드
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_004_flag_capture",
      rule_type: "win_condition",
      description: "표적 역의 깃발 꽂이를 점거하면 클리어",
      is_hidden: false,
      importance: 10
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_004_commander_system",
      rule_type: "system_rule",
      description: "대표를 선출하여 세력을 이끈다. 세력 간 영역 쟁탈과 깃발 탈취가 가능하다.",
      is_hidden: false,
      importance: 8
    })
    """)

    # 관계 생성
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_004_flag_war"})
    MATCH (r1:Rule {rule_id: "rule_004_flag_capture"})
    MATCH (r2:Rule {rule_id: "rule_004_commander_system"})
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r1)
    CREATE (s)-[:REQUIRES {requirement_type: "system_rule", is_mandatory: false}]->(r2)
    """)

    print("   ✅ 시나리오 004 완료")


async def create_scenario_005(repo: Neo4jGraphRepository):
    """시나리오 005: 범람의 재앙"""
    print("   [시나리오 005] 범람의 재앙 생성 중...")

    # 시나리오 노드
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_005_flood_disaster",
      title: "범람의 재앙",
      difficulty: "SS급",
      description: "5개 재앙 중 최강인 범람의 재앙 신유승을 처치해야 한다. 사전에 4개의 재앙이 처리되어 시나리오에 조기 진입했다. 매우 높은 난이도의 전투 시나리오.",
      objective: "범람의 재앙 신유승을 처치하시오",
      time_limit_turns: null,
      reward_coins: 100000,
      failure_penalty: "사망",
      is_main_scenario: true,
      sequence_order: 5
    })
    """)

    # 캐릭터 노드
    await repo.execute_write("""
    CREATE (c:Character {
      character_id: "shin_yoosung_disaster",
      name: "신유승 (범람의 재앙)",
      character_type: "disaster",
      description: "5개 재앙 중 최강. 어린 소녀의 모습을 하고 있지만 압도적인 힘을 가진 재앙급 존재. 감정이 폭주하여 파괴적인 힘을 발휘한다.",
      personality_traits: ["파괴적", "강력함", "감정 불안정"],
      appearance: "어린 소녀, 하지만 재앙급 힘",
      role: "boss",
      base_health: 10000,
      base_disposition: "hostile"
    })
    """)

    # 스킬 노드
    await repo.execute_write("""
    CREATE (skill:Skill {
      skill_id: "skill_lie_detection",
      name: "거짓 간파",
      grade: "B급",
      description: "상대방의 거짓말을 간파할 수 있는 스킬. 범람의 재앙 클리어 시 획득 가능한 보상.",
      effect: "거짓말 탐지",
      acquisition_condition: "범람의 재앙 클리어",
      cooldown: 0,
      stamina_cost: 0
    })
    """)

    # 규칙 노드
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_005_defeat_disaster",
      rule_type: "win_condition",
      description: "범람의 재앙 신유승을 처치하면 클리어",
      is_hidden: false,
      importance: 10
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_005_disaster_system",
      rule_type: "hidden_trick",
      description: "5개 재앙 중 4개를 미리 처리하여 범람의 재앙만 남겨둘 수 있다. 김독자는 원작 지식으로 이를 알고 있다.",
      is_hidden: true,
      importance: 9
    })
    """)

    # 트릭 노드
    await repo.execute_write("""
    CREATE (t:Trick {
      trick_id: "trick_005_disaster_reduction",
      name: "재앙 사전 처리",
      description: "5개 재앙 중 4개를 미리 처리하여 범람의 재앙만 남겨두는 전략. 김독자는 원작 지식으로 이 방법을 알고 있다.",
      difficulty_to_discover: 3,
      is_protagonist_knowledge: true,
      narrative_hint: "김독자는 '멸망한 세계에서 살아남는 세 가지 방법'을 떠올렸다. 이기수는 5개 재앙 중 4개를 미리 처리했다..."
    })
    """)

    # 관계 생성
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_005_flood_disaster"})
    MATCH (c:Character {character_id: "shin_yoosung_disaster"})
    CREATE (s)-[:APPEARS_IN {role: "boss", is_critical: true, appearance_turn: 1}]->(c)
    """)

    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_005_flood_disaster"})
    MATCH (skill:Skill {skill_id: "skill_lie_detection"})
    CREATE (s)-[:HAS_REWARD {reward_type: "skill", amount: 1}]->(skill)
    """)

    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_005_flood_disaster"})
    MATCH (r1:Rule {rule_id: "rule_005_defeat_disaster"})
    MATCH (r2:Rule {rule_id: "rule_005_disaster_system"})
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r1)
    CREATE (s)-[:REQUIRES {requirement_type: "hidden_knowledge", is_mandatory: false}]->(r2)
    """)

    await repo.execute_write("""
    MATCH (r:Rule {rule_id: "rule_005_disaster_system"})
    MATCH (t:Trick {trick_id: "trick_005_disaster_reduction"})
    CREATE (r)-[:ALTERNATIVE_SOLUTION {difficulty: 3, morality_score: 7}]->(t)
    """)

    print("   ✅ 시나리오 005 완료")


async def main():
    """시나리오 002~005 초기화"""

    print("=" * 60)
    print("Neo4j 시나리오 002~005 초기화 시작")
    print("=" * 60)

    # Neo4j 연결
    repo = Neo4jGraphRepository(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )

    try:
        # 1. 연결 확인
        print("\n[1/2] Neo4j 연결 확인 중...")
        is_connected = await repo.verify_connectivity()
        if not is_connected:
            print("❌ Neo4j 연결 실패. Docker Compose가 실행 중인지 확인하세요.")
            return
        print("✅ Neo4j 연결 성공")

        # 2. 시나리오 생성
        print("\n[2/2] 시나리오 002~005 생성 중...")
        await create_scenario_002(repo)
        await create_scenario_003(repo)
        await create_scenario_004(repo)
        await create_scenario_005(repo)

        # 3. 검증
        print("\n" + "=" * 60)
        print("데이터 검증 중...")
        print("=" * 60)

        # 시나리오 개수 확인
        query = """
        MATCH (s:Scenario)
        WHERE s.scenario_id STARTS WITH 'scenario_00'
        RETURN count(s) as count
        """
        result = await repo.execute_query(query)
        scenario_count = result[0]['count'] if result else 0

        print(f"\n✅ 전체 시나리오 개수: {scenario_count}개")
        print("   - scenario_001: 가치 증명")
        print("   - scenario_002: 조우")
        print("   - scenario_003: 그린 존")
        print("   - scenario_004: 깃발 쟁탈전")
        print("   - scenario_005: 범람의 재앙")

        print("\n" + "=" * 60)
        print("✅ 초기화 완료!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await repo.close()
        print("\n✅ Neo4j 연결 종료")


if __name__ == "__main__":
    asyncio.run(main())
