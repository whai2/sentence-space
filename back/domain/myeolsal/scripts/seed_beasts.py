"""
멸살법 시드 데이터 로드 스크립트

Canon 괴수 데이터를 ChromaDB와 Neo4j에 로드
"""
import asyncio
import json
from pathlib import Path

# 프로젝트 루트를 path에 추가
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from domain.myeolsal.models import BeastEntry
from domain.myeolsal.container import (
    get_chroma_repository,
    get_neo4j_repository,
    get_embeddings,
)


async def load_canon_beasts():
    """Canon 괴수 데이터 로드"""
    data_dir = Path(__file__).parent.parent / "data"
    beasts_file = data_dir / "canon_beasts.json"

    if not beasts_file.exists():
        print(f"Error: {beasts_file} not found")
        return

    # 저장소 초기화
    chroma_repo = get_chroma_repository()
    neo4j_repo = get_neo4j_repository()
    embeddings = get_embeddings()

    # Neo4j 연결 확인 및 제약 조건 생성
    if await neo4j_repo.verify_connectivity():
        await neo4j_repo.create_constraints()
        await neo4j_repo.create_indexes()
        print("Neo4j 연결 성공, 제약 조건 생성 완료")
    else:
        print("Warning: Neo4j 연결 실패, 관계 데이터는 저장되지 않습니다")

    # 기존 데이터 확인
    existing_count = chroma_repo.count()
    if existing_count > 0:
        print(f"기존 데이터 {existing_count}개 발견")
        response = input("기존 데이터를 삭제하고 다시 로드하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            chroma_repo.clear()
            await neo4j_repo.clear_all_beasts()
            print("기존 데이터 삭제 완료")
        else:
            print("기존 데이터 유지, 새 데이터만 추가합니다")

    # 데이터 로드
    with open(beasts_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    beasts = data.get("beasts", [])
    print(f"\n총 {len(beasts)}개의 괴수를 로드합니다...")

    success = 0
    errors = []

    for beast_data in beasts:
        try:
            # BeastEntry 생성
            beast = BeastEntry(**beast_data)

            # 임베딩 생성
            text = beast.get_searchable_text()
            embedding = await embeddings.aembed_query(text)

            # ChromaDB 저장
            chroma_repo.add_beast(beast, embedding)

            # Neo4j 저장
            await neo4j_repo.create_beast_node(beast)

            # 시나리오 연결
            for scenario_id in beast.appearance_scenarios:
                await neo4j_repo.link_to_scenario(beast.id, scenario_id)

            success += 1
            print(f"  ✓ {beast.title} ({beast.grade} {beast.species})")

        except Exception as e:
            errors.append({
                "id": beast_data.get("id", "unknown"),
                "error": str(e)
            })
            print(f"  ✗ {beast_data.get('id', 'unknown')}: {e}")

    # 진화 관계 생성
    print("\n진화 관계 생성 중...")
    evolution_pairs = [
        ("beast_bug_egg_9", "beast_ground_bug_8"),
        ("beast_ground_bug_8", "beast_giant_bug_6"),
        ("beast_giant_bug_6", "beast_bug_queen_3"),
        ("beast_steel_wolf_7", "beast_black_steel_wolf_5"),
        ("beast_sea_dragon_7", "beast_queen_mirbad_5"),
        ("beast_poison_spider_7", "beast_spider_queen_4"),
    ]

    for from_id, to_id in evolution_pairs:
        try:
            await neo4j_repo.create_evolution_relation(from_id, to_id)
            print(f"  ✓ {from_id} → {to_id}")
        except Exception as e:
            print(f"  ✗ {from_id} → {to_id}: {e}")

    # 결과 출력
    print(f"\n========== 로드 완료 ==========")
    print(f"성공: {success}개")
    print(f"실패: {len(errors)}개")

    if errors:
        print("\n실패 목록:")
        for err in errors:
            print(f"  - {err['id']}: {err['error']}")

    # 통계 출력
    stats = chroma_repo.get_stats()
    print(f"\n========== 저장소 통계 ==========")
    print(f"총 괴수 수: {stats['total_count']}")
    print(f"등급 분포: {stats['grade_distribution']}")
    print(f"종 분포: {stats['species_distribution']}")


async def check_data():
    """저장된 데이터 확인"""
    chroma_repo = get_chroma_repository()
    neo4j_repo = get_neo4j_repository()

    print("========== ChromaDB 상태 ==========")
    stats = chroma_repo.get_stats()
    print(f"총 괴수 수: {stats['total_count']}")
    print(f"등급 분포: {stats['grade_distribution']}")
    print(f"종 분포: {stats['species_distribution']}")

    print("\n========== Neo4j 상태 ==========")
    if await neo4j_repo.verify_connectivity():
        node_counts = await neo4j_repo.get_node_count()
        print(f"노드 수: {node_counts}")
    else:
        print("Neo4j 연결 실패")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="멸살법 시드 데이터 관리")
    parser.add_argument("command", choices=["load", "check"], help="실행할 명령")

    args = parser.parse_args()

    if args.command == "load":
        asyncio.run(load_canon_beasts())
    elif args.command == "check":
        asyncio.run(check_data())
