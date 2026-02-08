#!/usr/bin/env python3
"""
Neo4j 시나리오 그래프 초기화 스크립트

시나리오 001 "가치 증명" 데이터를 Neo4j에 로드합니다.
"""
import asyncio
import sys
from pathlib import Path

# Add back directory to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository


async def main():
    """시나리오 그래프 초기화"""

    print("=" * 60)
    print("Neo4j 시나리오 그래프 초기화 시작")
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

        # 4. Cypher 스크립트 실행
        print("\n[4/5] 시나리오 001 데이터 로드 중...")

        # Cypher 파일 경로
        cypher_file = project_root / "domain" / "orv_v2" / "data" / "scenarios" / "scenario_001_seed.cypher"

        if not cypher_file.exists():
            print(f"❌ Cypher 파일을 찾을 수 없습니다: {cypher_file}")
            return

        # Cypher 스크립트 읽기
        cypher_script = cypher_file.read_text(encoding="utf-8")

        # 관계 생성 섹션 분리 (// ====... 관계 생성 으로 시작)
        parts = cypher_script.split("// ============================================")

        # 노드 생성 부분 찾기 (처음부터 "관계 생성" 전까지)
        node_creation_parts = []
        relationship_creation_parts = []

        for i, part in enumerate(parts):
            if "관계 생성" in part or i >= len(parts) - 5:  # 마지막 5개 섹션은 관계
                if part.strip() and not part.strip().startswith("//"):
                    relationship_creation_parts.append(part)
            else:
                node_creation_parts.append(part)

        # 노드 생성 실행
        node_script = "// ============================================".join(node_creation_parts)
        # 주석과 빈 줄 정리
        node_lines = [line for line in node_script.split("\n")
                     if line.strip() and not line.strip().startswith("//")]
        node_script_cleaned = "\n".join(node_lines)

        if node_script_cleaned:
            result = await repo.execute_write(node_script_cleaned)
            print(f"   - 노드 생성: {result.get('nodes_created', 0)}개")

        # 관계 생성 실행 (각 섹션을 개별적으로)
        total_relationships = 0
        relationship_script = "// ============================================".join(relationship_creation_parts)

        # === 로 시작하는 각 섹션을 분리
        sections = [s.strip() for s in relationship_script.split("// ===") if s.strip()]

        for section in sections:
            # 주석 제거
            lines = [line for line in section.split("\n")
                    if line.strip() and not line.strip().startswith("//")
                    and not line.strip().startswith("RETURN")]

            section_cleaned = "\n".join(lines)

            if section_cleaned and "CREATE" in section_cleaned:
                try:
                    result = await repo.execute_write(section_cleaned)
                    total_relationships += result.get('relationships_created', 0)
                except Exception as e:
                    print(f"   ⚠️  관계 생성 중 오류: {str(e)[:100]}")

        print(f"   - 관계 생성: {total_relationships}개")

        print("✅ 시나리오 001 데이터 로드 완료")

        # 5. 데이터 검증
        print("\n[5/5] 데이터 검증 중...")
        node_counts = await repo.get_node_count()

        print("✅ 데이터 검증 완료")
        print("\n" + "=" * 60)
        print("노드 타입별 개수:")
        print("=" * 60)
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
