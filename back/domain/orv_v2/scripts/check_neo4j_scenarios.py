"""
Neo4j에 저장된 시나리오 확인
"""
import asyncio
from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository
from server.config import get_settings


async def check_scenarios():
    """Neo4j에 저장된 시나리오 확인"""

    settings = get_settings()
    neo4j_uri = getattr(settings, "neo4j_uri", "bolt://localhost:7687")
    neo4j_username = getattr(settings, "neo4j_username", "neo4j")
    neo4j_password = getattr(settings, "neo4j_password", "password")

    repo = Neo4jGraphRepository(
        uri=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password
    )

    print("=" * 60)
    print("🔍 Neo4j 시나리오 확인")
    print("=" * 60)

    # 모든 시나리오 조회
    query = """
    MATCH (s:Scenario)
    RETURN s.scenario_id as id, s.title as title, s.type as type, s.scenario_number as number
    ORDER BY s.scenario_number, s.title
    """

    result = await repo.execute_query(query)

    print(f"\n총 {len(result)}개 시나리오:")
    print()

    for i, record in enumerate(result, 1):
        scenario_id = record['id']
        title = record['title']
        type_val = record['type']
        number = record['number']

        print(f"{i}. [{type_val}] #{number} {title} (id: {scenario_id})")

    await repo.close()


if __name__ == "__main__":
    asyncio.run(check_scenarios())
