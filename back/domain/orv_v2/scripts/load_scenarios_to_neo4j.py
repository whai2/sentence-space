"""
파싱된 나무위키 시나리오를 Neo4j에 저장

parsed_scenarios.json 파일을 읽어서 Neo4j 지식 그래프에 저장
"""
import asyncio
import json
from pathlib import Path
from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository
from server.config import get_settings


async def load_scenarios_to_neo4j():
    """파싱된 시나리오들을 Neo4j에 저장"""

    print("=" * 60)
    print("📥 나무위키 시나리오 → Neo4j 저장")
    print("=" * 60)

    # 1. Neo4j 연결
    print("\n1️⃣ Neo4j 연결 중...")
    settings = get_settings()
    neo4j_uri = getattr(settings, "neo4j_uri", "bolt://localhost:7687")
    neo4j_username = getattr(settings, "neo4j_username", "neo4j")
    neo4j_password = getattr(settings, "neo4j_password", "password")

    repo = Neo4jGraphRepository(
        uri=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password
    )

    # 연결 확인
    is_connected = await repo.verify_connectivity()
    if not is_connected:
        print("❌ Neo4j 연결 실패")
        return

    print("✅ Neo4j 연결 성공")

    # 2. 파싱된 시나리오 파일 읽기
    print("\n2️⃣ 파싱된 시나리오 파일 읽기...")
    script_dir = Path(__file__).parent.parent.parent
    input_file = script_dir / "data" / "namuwiki_orv" / "processed" / "parsed_scenarios.json"

    if not input_file.exists():
        print(f"❌ 파일이 없습니다: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    scenarios = data['scenarios']
    print(f"✅ {len(scenarios)}개 시나리오 로드 완료")
    print(f"   - 메인: {data['main_scenarios']}개")
    print(f"   - 서브: {data['sub_scenarios']}개")
    print(f"   - 히든: {data['hidden_scenarios']}개")

    # 3. 기존 Scenario 노드 삭제 (초기화)
    print("\n3️⃣ 기존 시나리오 노드 삭제 중...")
    delete_query = "MATCH (s:Scenario) DETACH DELETE s"
    await repo.execute_query(delete_query)
    print("✅ 기존 시나리오 노드 삭제 완료")

    # 4. Neo4j에 시나리오 저장
    print("\n4️⃣ Neo4j에 시나리오 저장 중...")

    import re

    saved_count = 0
    for i, scenario in enumerate(scenarios, 1):
        # scenario_id를 title 기반으로 unique하게 생성
        # 제목을 알파벳+숫자로 변환
        safe_title = re.sub(r'[^a-zA-Z0-9가-힣]', '_', scenario['title'])
        scenario_type = scenario['type']
        scenario_number = scenario.get('scenario_number')

        # ID 생성 전략:
        # - 메인 시나리오: scenario_{number} (간단한 형식)
        # - 서브/히든: {type}_{title}
        if scenario_number and scenario_type == 'main':
            scenario_id = f"scenario_{scenario_number}"
        else:
            scenario_id = f"{scenario_type}_{safe_title}"

        # 시나리오 노드 생성 데이터 준비
        scenario_data = {
            "scenario_id": scenario_id,
            "scenario_number": scenario.get('scenario_number'),
            "title": scenario['title'],
            "type": scenario['type'],
            "difficulty": scenario.get('difficulty'),
            "clear_condition": scenario.get('clear_condition'),
            "time_limit": scenario.get('time_limit'),
            "reward": scenario.get('reward'),
            "failure_penalty": scenario.get('failure_penalty'),
            "description": scenario.get('description'),
        }

        # 추가 필드 (있으면 포함)
        if 'time_limit_minutes' in scenario:
            scenario_data['time_limit_minutes'] = scenario['time_limit_minutes']
        if 'time_limit_hours' in scenario:
            scenario_data['time_limit_hours'] = scenario['time_limit_hours']
        if 'time_limit_days' in scenario:
            scenario_data['time_limit_days'] = scenario['time_limit_days']
        if 'reward_coins' in scenario:
            scenario_data['reward_coins'] = scenario['reward_coins']

        # Neo4j에 시나리오 노드 생성
        await repo.create_scenario(scenario_data)

        saved_count += 1

        # 진행 상황 표시
        if i % 5 == 0 or i == len(scenarios):
            print(f"   진행: {i}/{len(scenarios)}")

    print(f"✅ {saved_count}개 시나리오 저장 완료!")

    # 5. 통계 출력
    print("\n5️⃣ Neo4j 통계:")

    # 타입별 개수 조회
    query = """
    MATCH (s:Scenario)
    RETURN s.type as type, count(s) as count
    ORDER BY type
    """
    result = await repo.execute_query(query)

    for record in result:
        type_name = record['type']
        count = record['count']
        print(f"   - {type_name}: {count}개")

    # 연결 종료
    await repo.close()

    print("\n" + "=" * 60)
    print("✨ Neo4j 저장 완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(load_scenarios_to_neo4j())
