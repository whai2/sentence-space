"""
Neo4j 전체 그래프 조회
"""
import asyncio
from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository
from server.config import get_settings


async def show_full_graph():
    """Neo4j 전체 그래프 구조 출력"""

    settings = get_settings()
    neo4j_uri = getattr(settings, "neo4j_uri", "bolt://localhost:7687")
    neo4j_username = getattr(settings, "neo4j_username", "neo4j")
    neo4j_password = getattr(settings, "neo4j_password", "password")

    repo = Neo4jGraphRepository(
        uri=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password
    )

    print("=" * 80)
    print("🔍 Neo4j 전체 그래프 조회")
    print("=" * 80)

    # 1. 노드 통계
    print("\n📊 노드 통계:")
    node_count_query = """
    MATCH (n)
    RETURN labels(n) as label, count(n) as count
    ORDER BY count DESC
    """
    node_stats = await repo.execute_query(node_count_query)

    total_nodes = 0
    for record in node_stats:
        label = record['label'][0] if record['label'] else 'No Label'
        count = record['count']
        total_nodes += count
        print(f"  - {label}: {count}개")

    print(f"\n총 노드 수: {total_nodes}개")

    # 2. 관계 통계
    print("\n🔗 관계 통계:")
    rel_count_query = """
    MATCH ()-[r]->()
    RETURN type(r) as rel_type, count(r) as count
    ORDER BY count DESC
    """
    rel_stats = await repo.execute_query(rel_count_query)

    total_rels = 0
    for record in rel_stats:
        rel_type = record['rel_type']
        count = record['count']
        total_rels += count
        print(f"  - {rel_type}: {count}개")

    print(f"\n총 관계 수: {total_rels}개")

    # 3. Scenario 노드 상세 정보
    print("\n" + "=" * 80)
    print("📖 Scenario 노드 상세:")
    print("=" * 80)

    scenario_query = """
    MATCH (s:Scenario)
    RETURN s
    ORDER BY s.scenario_number
    LIMIT 10
    """
    scenarios = await repo.execute_query(scenario_query)

    for i, record in enumerate(scenarios, 1):
        s = record['s']
        print(f"\n{i}. [{s.get('type')}] {s.get('title')}")
        print(f"   ID: {s.get('scenario_id')}")
        print(f"   난이도: {s.get('difficulty')}")
        print(f"   클리어 조건: {s.get('clear_condition', 'N/A')[:80]}...")
        print(f"   보상: {s.get('reward')}")

    # 4. 관계 구조 출력
    print("\n" + "=" * 80)
    print("🔗 그래프 관계 구조:")
    print("=" * 80)

    # Scenario와 연결된 모든 관계 조회
    graph_structure_query = """
    MATCH (s:Scenario)-[r]->(n)
    RETURN s.title as scenario_title, type(r) as relationship, labels(n)[0] as target_label, count(n) as count
    ORDER BY scenario_title, relationship
    LIMIT 20
    """
    structures = await repo.execute_query(graph_structure_query)

    if structures:
        current_scenario = None
        for record in structures:
            scenario = record['scenario_title']
            rel = record['relationship']
            target = record['target_label']
            count = record['count']

            if scenario != current_scenario:
                print(f"\n📌 {scenario}")
                current_scenario = scenario

            print(f"   └─ {rel} → {target} ({count}개)")
    else:
        print("\n⚠️  Scenario 노드와 연결된 관계가 없습니다.")
        print("   → 나무위키 데이터만 저장되어 있고, Phase/Character/Event는 수동으로 추가해야 합니다.")

    # 5. 샘플 전체 그래프 (제한적)
    print("\n" + "=" * 80)
    print("🌐 전체 그래프 샘플 (최대 50개 노드):")
    print("=" * 80)

    full_graph_query = """
    MATCH (n)
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT 50
    """
    graph_data = await repo.execute_query(full_graph_query)

    print(f"\n조회된 항목 수: {len(graph_data)}개")

    # 노드와 관계를 간단히 출력
    nodes_seen = set()
    relationships_seen = []

    for record in graph_data:
        n = record.get('n')
        r = record.get('r')
        m = record.get('m')

        if n:
            node_id = n.element_id
            if node_id not in nodes_seen:
                nodes_seen.add(node_id)
                labels = list(n.labels)
                props = dict(n)
                title = props.get('title') or props.get('name') or props.get('scenario_id') or 'Unknown'
                print(f"\n🔵 ({labels[0] if labels else 'Node'}) {title}")

        if r and m:
            rel_type = r.type
            m_labels = list(m.labels)
            m_props = dict(m)
            m_title = m_props.get('title') or m_props.get('name') or m_props.get('scenario_id') or 'Unknown'
            print(f"   └─ {rel_type} → ({m_labels[0] if m_labels else 'Node'}) {m_title}")

    print("\n" + "=" * 80)
    print("✅ 그래프 조회 완료!")
    print("=" * 80)
    print("\n💡 Neo4j Browser에서 전체 그래프를 시각적으로 보려면:")
    print("   http://localhost:7474")
    print("   쿼리: MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100")

    await repo.close()


if __name__ == "__main__":
    asyncio.run(show_full_graph())
