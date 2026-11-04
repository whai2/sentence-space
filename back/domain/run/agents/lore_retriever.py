"""
런 세계관 검색 에이전트

Pinecone 시맨틱 검색 + Neo4j 관계 보강을 결합하여
세계관 질의에 대한 풍부한 컨텍스트를 제공한다.
"""
from domain.run.repository.neo4j_repository import Neo4jRunRepository
from domain.run.repository.pinecone_repository import PineconeRunRepository


class LoreRetrieverAgent:
    """
    세계관 검색 에이전트

    벡터 검색으로 관련 엔티티를 찾고,
    그래프 관계로 컨텍스트를 보강한다.
    """

    def __init__(
        self,
        vector_repo: PineconeRunRepository,
        neo4j_repo: Neo4jRunRepository,
    ):
        self.vector_repo = vector_repo
        self.neo4j_repo = neo4j_repo

    async def search(
        self,
        query: str,
        n_results: int = 5,
        entity_types: list[str] | None = None,
        include_relations: bool = True,
    ) -> list[dict]:
        """
        통합 검색: 벡터 검색 + 관계 보강

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            entity_types: 필터링할 엔티티 타입 (예: ["concept", "character"])
            include_relations: Neo4j 관계 보강 여부
        """
        # 필터 구성
        filters = None
        if entity_types and len(entity_types) == 1:
            filters = {"entity_type": entity_types[0]}

        # Pinecone 시맨틱 검색
        results = self.vector_repo.search(query, n_results=n_results, filters=filters)

        # entity_types 필터가 여러 개일 때 후처리
        if entity_types and len(entity_types) > 1:
            results = [r for r in results if r.get("metadata", {}).get("entity_type") in entity_types]

        # Neo4j 관계 보강
        if include_relations:
            for result in results:
                entity_id = result["id"]
                try:
                    relations = await self.neo4j_repo.get_related_entities(entity_id)
                    result["relations"] = relations
                except Exception:
                    result["relations"] = []

        return results

    async def get_character_context(self, character_id: str) -> dict | None:
        """인물 전체 컨텍스트 (기본정보 + 타임라인 + 관계)"""
        entity = self.vector_repo.get_by_id(character_id)
        if not entity:
            return None

        try:
            timeline = await self.neo4j_repo.get_character_timeline(character_id)
            relations = await self.neo4j_repo.get_related_entities(character_id)
        except Exception:
            timeline = []
            relations = []

        return {
            **entity,
            "timeline": timeline,
            "relations": relations,
        }

    async def get_concept_detail(self, concept_id: str) -> dict | None:
        """개념 상세 (정의 + 관련 개념 + 사용된 사건)"""
        entity = self.vector_repo.get_by_id(concept_id)
        if not entity:
            return None

        try:
            usage = await self.neo4j_repo.get_concept_usage(concept_id)
        except Exception:
            usage = {"events": [], "related_concepts": []}

        return {
            **entity,
            "usage": usage,
        }

    async def get_event_detail(self, event_id: str) -> dict | None:
        """사건 상세 (내용 + 참여자 + 관련 개념 + 전후 사건)"""
        entity = self.vector_repo.get_by_id(event_id)
        if not entity:
            return None

        try:
            context = await self.neo4j_repo.get_event_context(event_id)
        except Exception:
            context = {"participants": [], "concepts": [], "prev_events": [], "next_events": []}

        return {
            **entity,
            "context": context,
        }

    async def search_by_type(
        self,
        query: str,
        entity_type: str,
        n_results: int = 5,
    ) -> list[dict]:
        """특정 타입으로 검색"""
        return await self.search(
            query=query,
            n_results=n_results,
            entity_types=[entity_type],
            include_relations=False,
        )
