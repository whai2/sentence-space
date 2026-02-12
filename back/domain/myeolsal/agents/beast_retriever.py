"""
괴수 RAG 검색 에이전트

Pinecone + Neo4j 통합 검색
OpenAI text-embedding-3-small 임베딩 사용
"""
from typing import Any

from domain.myeolsal.models import BeastEntry
from domain.myeolsal.repository import PineconeBeastRepository, Neo4jMyeolsalRepository


class BeastRetrieverAgent:
    """
    괴수 RAG 검색 에이전트

    벡터 검색(Pinecone) + 관계 검색(Neo4j) 통합
    """

    def __init__(
        self,
        vector_repo: PineconeBeastRepository,
        neo4j_repo: Neo4jMyeolsalRepository,
    ):
        """
        Args:
            vector_repo: Pinecone 벡터 저장소
            neo4j_repo: Neo4j 저장소
        """
        self.vector_repo = vector_repo
        self.neo4j_repo = neo4j_repo

    async def search(
        self,
        query: str,
        n_results: int = 5,
        filters: dict[str, Any] | None = None,
        include_relations: bool = True
    ) -> list[dict]:
        """
        통합 검색

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            filters: 메타데이터 필터 (grade, species 등)
            include_relations: Neo4j 관계 정보 포함 여부

        Returns:
            검색 결과 리스트
        """
        # Pinecone 시맨틱 검색
        search_results = self.vector_repo.search(
            query=query,
            n_results=n_results,
            filters=filters
        )

        # Neo4j 관계 보강 (선택적)
        if include_relations:
            for result in search_results:
                beast_id = result.get("id", "")
                # 청크 ID에서 원본 ID 추출
                if "_desc" in beast_id or "_combat" in beast_id or "_survival" in beast_id:
                    beast_id = beast_id.rsplit("_", 1)[0]

                try:
                    relations = await self.neo4j_repo.get_related_beasts(beast_id)
                    result["relations"] = relations

                    evolution = await self.neo4j_repo.get_evolution_tree(beast_id)
                    result["evolution_tree"] = evolution

                    scenarios = await self.neo4j_repo.get_scenarios_for_beast(beast_id)
                    result["scenarios"] = scenarios
                except Exception:
                    result["relations"] = []
                    result["evolution_tree"] = []
                    result["scenarios"] = []

        return search_results

    async def search_by_grade(self, grade: str, limit: int = 10) -> list[dict]:
        """등급별 검색"""
        return self.vector_repo.search(
            query=f"{grade} 괴수",
            n_results=limit,
            filters={"grade": grade}
        )

    async def search_by_species(self, species: str, limit: int = 10) -> list[dict]:
        """종별 검색"""
        return self.vector_repo.search(
            query=species,
            n_results=limit,
            filters={"species": species}
        )

    async def search_by_weakness(self, weakness: str, limit: int = 10) -> list[dict]:
        """약점 기반 검색"""
        results = self.vector_repo.search(
            query=f"{weakness} 속성에 약한 괴수",
            n_results=limit * 2  # 필터링 후 줄어들 수 있으므로
        )

        # 약점 필터링
        filtered = []
        for r in results:
            weaknesses = r.get("metadata", {}).get("weaknesses", [])
            if weakness in weaknesses:
                filtered.append(r)
            if len(filtered) >= limit:
                break

        return filtered

    async def find_similar(
        self,
        beast: BeastEntry,
        n_results: int = 5,
        exclude_self: bool = True
    ) -> list[dict]:
        """
        유사 괴수 검색

        Args:
            beast: 기준 괴수
            n_results: 결과 수
            exclude_self: 자기 자신 제외 여부

        Returns:
            유사 괴수 리스트
        """
        query_text = beast.get_searchable_text()

        results = self.vector_repo.search(
            query=query_text,
            n_results=n_results + (1 if exclude_self else 0)
        )

        if exclude_self:
            results = [r for r in results if r["id"] != beast.id][:n_results]

        return results

    async def get_combat_info(self, query: str, n_results: int = 3) -> list[dict]:
        """
        전투 정보 검색 (전투 패턴 청크 우선)

        Args:
            query: 검색 쿼리 (예: "어룡 어떻게 상대해?")
            n_results: 결과 수

        Returns:
            전투 관련 정보
        """
        # combat 청크 필터링
        results = self.vector_repo.search(
            query=f"전투 패턴 공략 {query}",
            n_results=n_results * 2,
            filters={"chunk_type": "combat"}
        )

        if len(results) < n_results:
            # combat 청크가 부족하면 일반 검색 추가
            general_results = self.vector_repo.search(
                query=f"전투 패턴 공략 {query}",
                n_results=n_results
            )
            seen_ids = {r["id"] for r in results}
            for r in general_results:
                if r["id"] not in seen_ids:
                    results.append(r)
                    if len(results) >= n_results:
                        break

        return results[:n_results]

    async def get_survival_info(self, query: str, n_results: int = 3) -> list[dict]:
        """
        생존 가이드 검색 (survival 청크 우선)

        Args:
            query: 검색 쿼리 (예: "스틸울프 생존법")
            n_results: 결과 수

        Returns:
            생존 관련 정보
        """
        results = self.vector_repo.search(
            query=f"생존 가이드 대처법 {query}",
            n_results=n_results * 2,
            filters={"chunk_type": "survival"}
        )

        if len(results) < n_results:
            general_results = self.vector_repo.search(
                query=f"생존 가이드 대처법 {query}",
                n_results=n_results
            )
            seen_ids = {r["id"] for r in results}
            for r in general_results:
                if r["id"] not in seen_ids:
                    results.append(r)
                    if len(results) >= n_results:
                        break

        return results[:n_results]

    async def get_evolution_path(self, beast_id: str) -> list[dict]:
        """진화 경로 조회"""
        return await self.neo4j_repo.get_evolution_tree(beast_id)

    async def get_scenario_beasts(self, scenario_id: str) -> list[dict]:
        """시나리오별 괴수 조회"""
        return await self.neo4j_repo.get_beasts_in_scenario(scenario_id)
