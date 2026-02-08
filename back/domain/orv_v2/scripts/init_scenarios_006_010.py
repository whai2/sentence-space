#!/usr/bin/env python3
"""
Neo4j 시나리오 그래프 초기화 - 시나리오 006~010

시나리오 006 "버려진 세계" ~ 010 "73번째 마왕" 데이터를 Neo4j에 로드합니다.
"""
import asyncio
import sys
from pathlib import Path

# Add back directory to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository


async def create_scenario_006(repo: Neo4jGraphRepository):
    """시나리오 006: 버려진 세계 / 작은 구원자"""
    print("   [시나리오 006] 버려진 세계 / 작은 구원자 생성 중...")

    # 시나리오 노드 (버려진 세계)
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_006_abandoned_world",
      title: "버려진 세계",
      difficulty: "S급",
      description: "피스 랜드의 지배종을 멸절시켜야 한다. 참가자들이 이계의 재앙이 되어 다른 세계를 멸망시키는 역할 전환이 일어난다. 김독자는 멸살법 지식으로 시나리오 구조를 파악한다.",
      objective: "피스 랜드의 지배종 멸절",
      time_limit_turns: 960,
      reward_coins: 200000,
      failure_penalty: "사망",
      is_main_scenario: true,
      sequence_order: 6
    })
    """)

    # 시나리오 노드 (작은 구원자 - 대안 루트)
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_006_little_savior",
      title: "작은 구원자",
      difficulty: "S급",
      description: "소인종 편에서 재앙들을 처치하는 대안 루트. 성좌 개입으로 추가 선택지가 생성되었다. A급 스킬 '소형화'를 획득할 수 있다.",
      objective: "소인종 편에서 재앙들 처치",
      time_limit_turns: 960,
      reward_coins: 300000,
      failure_penalty: "사망",
      is_main_scenario: true,
      sequence_order: 6
    })
    """)

    # 위치 노드
    await repo.execute_write("""
    CREATE (loc:Location {
      location_id: "피스_랜드",
      name: "피스 랜드",
      description: "소인종이 사는 이계. 참가자들이 재앙으로 작용하는 세계.",
      atmosphere: "환상적이지만 위험한",
      danger_level: 8
    })
    """)

    # 스킬 노드
    await repo.execute_write("""
    CREATE (skill:Skill {
      skill_id: "skill_miniaturization",
      name: "소형화",
      grade: "A급",
      description: "몸의 크기를 줄일 수 있는 스킬. 작은 구원자 루트 선택 시 획득 가능.",
      effect: "크기 축소",
      acquisition_condition: "작은 구원자 클리어",
      cooldown: 0,
      stamina_cost: 50
    })
    """)

    # 규칙 노드
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_006_role_reversal",
      rule_type: "system_rule",
      description: "참가자들이 다른 세계의 재앙이 되는 역할 전환. 멸살법 지식으로 구조 파악 가능.",
      is_hidden: false,
      importance: 9
    })
    """)

    # 트릭 노드
    await repo.execute_write("""
    CREATE (t:Trick {
      trick_id: "trick_006_constellation_intervention",
      name: "성좌 개입 활용",
      description: "성좌의 개입으로 대안 루트(작은 구원자)를 선택할 수 있다. 김독자는 성좌들의 욕망을 이용하여 변수를 창출한다.",
      difficulty_to_discover: 5,
      is_protagonist_knowledge: true,
      narrative_hint: "김독자는 성좌들의 거대 설화를 이용할 수 있다는 것을 알고 있다..."
    })
    """)

    # 관계 생성
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_006_little_savior"})
    MATCH (skill:Skill {skill_id: "skill_miniaturization"})
    CREATE (s)-[:HAS_REWARD {reward_type: "skill", amount: 1}]->(skill)
    """)

    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_006_abandoned_world"})
    MATCH (r:Rule {rule_id: "rule_006_role_reversal"})
    CREATE (s)-[:REQUIRES {requirement_type: "system_rule", is_mandatory: false}]->(r)
    """)

    await repo.execute_write("""
    MATCH (r:Rule {rule_id: "rule_006_role_reversal"})
    MATCH (t:Trick {trick_id: "trick_006_constellation_intervention"})
    CREATE (r)-[:ALTERNATIVE_SOLUTION {difficulty: 5, morality_score: 8}]->(t)
    """)

    print("   ✅ 시나리오 006 완료")


async def create_scenario_008(repo: Neo4jGraphRepository):
    """시나리오 008: 최강의 희생양"""
    print("   [시나리오 008] 최강의 희생양 생성 중...")

    # 시나리오 노드
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_008_strongest_sacrifice",
      title: "최강의 희생양",
      difficulty: "S급",
      description: "괴수 웨이브에서 생존하되, 절반 또는 최강자 1명이 사망해야 한다. 4시간마다 화신 강자 랭킹이 공개되며, 10위부터 1위 순서로 발표된다. 김독자는 최강 화신이었으나 사전에 사망했다.",
      objective: "괴수 웨이브 생존 (추가: 절반 또는 최강자 1명 사망)",
      time_limit_turns: null,
      reward_coins: 150000,
      failure_penalty: "사망",
      is_main_scenario: true,
      sequence_order: 8
    })
    """)

    # 규칙 노드
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_008_sacrifice_condition",
      rule_type: "win_condition",
      description: "괴수 웨이브에서 생존하되, 참가자의 절반 또는 최강자 1명이 사망해야 클리어",
      is_hidden: false,
      importance: 10
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_008_ranking_system",
      rule_type: "system_rule",
      description: "4시간마다 화신 강자 랭킹이 공개된다 (10위→1위 순서). 최강자가 타겟이 된다.",
      is_hidden: false,
      importance: 9
    })
    """)

    # 트릭 노드
    await repo.execute_write("""
    CREATE (t:Trick {
      trick_id: "trick_008_fake_death",
      name: "사전 사망 전략",
      description: "최강자로 지목되기 전에 사전에 사망하여 희생양 조건을 회피한다. 김독자는 이 전략을 사용했다.",
      difficulty_to_discover: 7,
      is_protagonist_knowledge: true,
      narrative_hint: "김독자는 원작에서 이기수가 사용한 전략을 알고 있다. 최강자가 되기 전에..."
    })
    """)

    # 관계 생성
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_008_strongest_sacrifice"})
    MATCH (r1:Rule {rule_id: "rule_008_sacrifice_condition"})
    MATCH (r2:Rule {rule_id: "rule_008_ranking_system"})
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r1)
    CREATE (s)-[:REQUIRES {requirement_type: "system_rule", is_mandatory: false}]->(r2)
    """)

    await repo.execute_write("""
    MATCH (r:Rule {rule_id: "rule_008_ranking_system"})
    MATCH (t:Trick {trick_id: "trick_008_fake_death"})
    CREATE (r)-[:ALTERNATIVE_SOLUTION {difficulty: 7, morality_score: 6}]->(t)
    """)

    print("   ✅ 시나리오 008 완료")


async def create_scenario_009(repo: Neo4jGraphRepository):
    """시나리오 009: 악마의 증명"""
    print("   [시나리오 009] 악마의 증명 생성 중...")

    # 시나리오 노드 (1단계)
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_009_demon_proof",
      title: "악마의 증명",
      difficulty: "A++급",
      description: "암흑성 1층에서 악마종을 사냥하여 증명 9개를 수집해야 한다. 이후 2층으로 진입하면 시나리오가 갱신된다.",
      objective: "암흑성 1층에서 악마종 사냥, 증명 9개 수집",
      time_limit_turns: 552,
      reward_coins: 50000,
      failure_penalty: "사망",
      is_main_scenario: true,
      sequence_order: 9
    })
    """)

    # 위치 노드
    await repo.execute_write("""
    CREATE (loc:Location {
      location_id: "암흑성_1층",
      name: "암흑성 1층",
      description: "악마종이 서식하는 위험한 지역. 증명을 수집해야 2층으로 진입할 수 있다.",
      atmosphere: "어둡고 위협적인",
      danger_level: 8
    })
    """)

    await repo.execute_write("""
    CREATE (loc:Location {
      location_id: "암흑성_2층_낙원",
      name: "암흑성 2층 - 낙원",
      description: "진행 조건 없는 특별한 거점. 성주만이 클리어 조건을 알고 있으며, 화신들의 안정적 거주지가 된다.",
      atmosphere: "평화로운",
      danger_level: 3
    })
    """)

    # 규칙 노드
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_009_collect_proofs",
      rule_type: "win_condition",
      description: "증명 9개를 수집하면 2층 진입 가능",
      is_hidden: false,
      importance: 10
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_009_paradise_secret",
      rule_type: "hidden_trick",
      description: "2층 '낙원'은 진행 조건이 없는 특별한 공간. 성주만 클리어 조건을 알고 있다.",
      is_hidden: true,
      importance: 8
    })
    """)

    # 관계 생성
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_009_demon_proof"})
    MATCH (r1:Rule {rule_id: "rule_009_collect_proofs"})
    MATCH (r2:Rule {rule_id: "rule_009_paradise_secret"})
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r1)
    CREATE (s)-[:REQUIRES {requirement_type: "hidden_knowledge", is_mandatory: false}]->(r2)
    """)

    print("   ✅ 시나리오 009 완료")


async def create_scenario_010(repo: Neo4jGraphRepository):
    """시나리오 010: 73번째 마왕"""
    print("   [시나리오 010] 73번째 마왕 생성 중...")

    # 시나리오 노드
    await repo.execute_write("""
    CREATE (s:Scenario {
      scenario_id: "scenario_010_73rd_demon_king",
      title: "73번째 마왕",
      difficulty: "SS급",
      description: "암흑성 3층 최종 시나리오. 랭킹 10위 내 화신만 참가할 수 있다 (식스맨 카드로 예외 가능). 마왕 조기 사망으로 시나리오가 갱신되어, 보옥 획득 또는 신규 마왕 살해 중 선택해야 한다. 김독자는 자신이 마왕이 되어 희생한다.",
      objective: "보옥을 획득하거나 신규 마왕 살해",
      time_limit_turns: 720,
      reward_coins: 200000,
      failure_penalty: "사망 + 시나리오 추방",
      is_main_scenario: true,
      sequence_order: 10
    })
    """)

    # 위치 노드
    await repo.execute_write("""
    CREATE (loc:Location {
      location_id: "암흑성_3층",
      name: "암흑성 3층",
      description: "마왕이 있는 최종 층. 가장 위험한 지역이며, 마왕전이 벌어진다.",
      atmosphere: "극도로 위험한",
      danger_level: 10
    })
    """)

    # 규칙 노드
    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_010_ranking_limit",
      rule_type: "system_rule",
      description: "랭킹 10위 내 화신만 참가 가능 (식스맨 카드로 예외 가능)",
      is_hidden: false,
      importance: 9
    })
    """)

    await repo.execute_write("""
    CREATE (r:Rule {
      rule_id: "rule_010_demon_king_choice",
      rule_type: "win_condition",
      description: "보옥 획득 또는 신규 마왕 살해 중 선택하여 클리어",
      is_hidden: false,
      importance: 10
    })
    """)

    # 트릭 노드
    await repo.execute_write("""
    CREATE (t:Trick {
      trick_id: "trick_010_become_demon_king",
      name: "스스로 마왕이 되기",
      description: "자신이 마왕이 되어 다른 참가자들을 클리어시키는 희생 전략. 김독자가 선택한 방법.",
      difficulty_to_discover: 9,
      is_protagonist_knowledge: true,
      narrative_hint: "김독자는 결정했다. 자신이 마왕이 되어 모두를 구할 것이라고..."
    })
    """)

    # 관계 생성
    await repo.execute_write("""
    MATCH (s:Scenario {scenario_id: "scenario_010_73rd_demon_king"})
    MATCH (r1:Rule {rule_id: "rule_010_ranking_limit"})
    MATCH (r2:Rule {rule_id: "rule_010_demon_king_choice"})
    CREATE (s)-[:REQUIRES {requirement_type: "system_rule", is_mandatory: false}]->(r1)
    CREATE (s)-[:REQUIRES {requirement_type: "condition", is_mandatory: true}]->(r2)
    """)

    await repo.execute_write("""
    MATCH (r:Rule {rule_id: "rule_010_demon_king_choice"})
    MATCH (t:Trick {trick_id: "trick_010_become_demon_king"})
    CREATE (r)-[:ALTERNATIVE_SOLUTION {difficulty: 9, morality_score: 10}]->(t)
    """)

    print("   ✅ 시나리오 010 완료")


async def main():
    """시나리오 006~010 초기화"""

    print("=" * 60)
    print("Neo4j 시나리오 006~010 초기화 시작")
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
        print("\n[2/2] 시나리오 006~010 생성 중...")
        await create_scenario_006(repo)
        await create_scenario_008(repo)  # 007은 정보 부족으로 스킵
        await create_scenario_009(repo)
        await create_scenario_010(repo)

        # 3. 검증
        print("\n" + "=" * 60)
        print("데이터 검증 중...")
        print("=" * 60)

        # 시나리오 개수 확인
        query = """
        MATCH (s:Scenario)
        WHERE s.scenario_id STARTS WITH 'scenario_'
        RETURN count(s) as count
        """
        result = await repo.execute_query(query)
        scenario_count = result[0]['count'] if result else 0

        print(f"\n✅ 전체 시나리오 개수: {scenario_count}개")

        # 시나리오 목록 출력
        query2 = """
        MATCH (s:Scenario)
        RETURN s.scenario_id as id, s.title as title, s.difficulty as difficulty
        ORDER BY s.sequence_order
        """
        scenarios = await repo.execute_query(query2)
        for sc in scenarios:
            print(f"   - {sc['id']}: {sc['title']} ({sc['difficulty']})")

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
