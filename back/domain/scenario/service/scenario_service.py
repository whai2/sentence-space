"""
시나리오 설명집 서비스

비즈니스 로직 레이어
"""
import json
from pathlib import Path

from domain.scenario.models import ScenarioPackage
from domain.scenario.repository import Neo4jScenarioRepository


class ScenarioService:
    """
    시나리오 설명집 서비스

    시나리오 조회, 관리를 위한 통합 서비스
    """

    def __init__(self, neo4j_repo: Neo4jScenarioRepository):
        self.neo4j_repo = neo4j_repo

    # ============================================
    # 시나리오 조회
    # ============================================

    async def get_scenario(self, scenario_id: str) -> dict | None:
        """시나리오 상세 조회 (연결된 괴수 포함)"""
        return await self.neo4j_repo.get_scenario_with_beasts(scenario_id)

    def list_scenarios(
        self,
        offset: int = 0,
        limit: int = 50,
        type_filter: str | None = None,
    ) -> dict:
        """이 메서드는 async로 호출해야 함 — 라우트에서 await"""
        raise NotImplementedError("Use list_scenarios_async instead")

    async def list_scenarios_async(
        self,
        offset: int = 0,
        limit: int = 50,
        type_filter: str | None = None,
    ) -> dict:
        """시나리오 목록 조회 (페이지네이션)"""
        scenarios, total = await self.neo4j_repo.list_scenarios(
            offset=offset, limit=limit, type_filter=type_filter,
        )
        return {
            "results": scenarios,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total,
        }

    # ============================================
    # 통계 / 그래프
    # ============================================

    async def get_stats(self) -> dict:
        """시나리오 통계"""
        return await self.neo4j_repo.get_stats()

    async def get_graph(self, limit: int = 100) -> dict:
        """시나리오 관계 그래프 (시각화용)"""
        return await self.neo4j_repo.get_scenario_graph(limit)

    # ============================================
    # 초기화
    # ============================================

    async def initialize(self, auto_seed: bool = True) -> dict:
        """서비스 초기화"""
        neo4j_ok = await self.neo4j_repo.verify_connectivity()

        if neo4j_ok:
            await self.neo4j_repo.create_constraints()
            await self.neo4j_repo.create_indexes()

        stats = await self.neo4j_repo.get_stats()
        seed_result = None

        if auto_seed and stats["total"] == 0:
            data_dir = Path(__file__).parent.parent / "data"
            seed_result = await self.load_seed_data(data_dir)
            stats = await self.neo4j_repo.get_stats()

        return {
            "neo4j": neo4j_ok,
            "scenario_count": stats["total"],
            "seed_loaded": seed_result,
        }

    async def load_seed_data(self, data_dir: str | Path, force: bool = False) -> dict:
        """시드 데이터 로드"""
        data_dir = Path(data_dir)
        results = {"loaded": 0, "skipped": 0, "errors": []}

        scenarios_file = data_dir / "scenarios.json"
        if not scenarios_file.exists():
            return results

        with open(scenarios_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # force 모드: 모든 기존 시나리오 데이터 일괄 삭제
        if force:
            cleared = await self.neo4j_repo.clear_all_scenario_data()
            results["cleared"] = cleared

        for scenario_data in data.get("scenarios", []):
            try:
                scenario = ScenarioPackage(**scenario_data)

                # 이미 존재하는지 확인
                existing = await self.neo4j_repo.get_scenario(scenario.id)
                if existing and not force:
                    results["skipped"] += 1
                    continue

                await self.neo4j_repo.create_scenario(scenario)
                results["loaded"] += 1

            except Exception as e:
                results["errors"].append({
                    "id": scenario_data.get("id", "unknown"),
                    "error": str(e)
                })

        return results
