"""
런 세계관 서비스

세계관 질의, 검색, 데이터 관리를 오케스트레이션
"""
import json
from pathlib import Path

from domain.run.agents.lore_retriever import LoreRetrieverAgent
from domain.run.graph.workflow import RunWorkflow
from domain.run.models.entities import (
    EntityType,
    RunCharacter,
    RunConcept,
    RunEntity,
    RunEvent,
    RunWorldSetting,
)
from domain.run.repository.neo4j_repository import Neo4jRunRepository
from domain.run.repository.pinecone_repository import PineconeRunRepository
from domain.run.scripts.fetch_notion import (
    parse_characters,
    parse_concept,
    parse_events,
    parse_worldbuilding,
    save_json,
)

DATA_DIR = Path(__file__).parent.parent / "data"


class RunService:
    """
    런 세계관 서비스

    - query: 자연어 질의 (워크플로우 실행)
    - search: 직접 시맨틱 검색
    - get_entity: 엔티티 상세 + 관계
    - seed_from_notion: Notion 데이터 → DB 로드
    """

    def __init__(
        self,
        vector_repo: PineconeRunRepository,
        neo4j_repo: Neo4jRunRepository,
        retriever: LoreRetrieverAgent,
        workflow: RunWorkflow,
    ):
        self.vector_repo = vector_repo
        self.neo4j_repo = neo4j_repo
        self.retriever = retriever
        self.workflow = workflow

    # === 질의 ===

    async def query(self, question: str) -> dict:
        """자연어 질의 → 워크플로우 실행"""
        return await self.workflow.run(question)

    # === 검색 ===

    async def search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """시맨틱 검색"""
        return await self.retriever.search(
            query=query,
            n_results=limit,
            entity_types=entity_types,
            include_relations=True,
        )

    async def get_entity(self, entity_id: str) -> dict | None:
        """엔티티 상세 조회 + 관계"""
        entity = self.vector_repo.get_by_id(entity_id)
        if not entity:
            return None

        try:
            relations = await self.neo4j_repo.get_related_entities(entity_id)
            entity["relations"] = relations
        except Exception:
            entity["relations"] = []

        return entity

    # === 그래프 ===

    async def get_graph(self, limit: int = 100) -> dict:
        """시각화용 그래프 데이터"""
        try:
            return await self.neo4j_repo.get_full_graph(limit)
        except Exception:
            return {"nodes": [], "edges": []}

    # === 통계 ===

    def get_stats(self) -> dict:
        """저장소 통계"""
        pinecone_stats = self.vector_repo.get_stats()
        return {"pinecone": pinecone_stats}

    # === 초기화 ===

    async def initialize(self, auto_seed: bool = False) -> dict:
        """서비스 초기화"""
        result = {"neo4j": False, "pinecone_count": 0}

        # Neo4j 연결 및 인덱스 생성
        try:
            if await self.neo4j_repo.verify_connectivity():
                await self.neo4j_repo.create_constraints()
                await self.neo4j_repo.create_indexes()
                result["neo4j"] = True
        except Exception:
            pass

        # Pinecone 상태 확인
        result["pinecone_count"] = self.vector_repo.count()

        # 자동 시드 (JSON 파일이 있고 Pinecone이 비어있을 때)
        if auto_seed and result["pinecone_count"] == 0:
            json_files = list(DATA_DIR.glob("*.json"))
            if json_files:
                seed_result = await self.seed_from_json()
                result["seed"] = seed_result

        return result

    # === 데이터 로드 ===

    async def seed_from_notion_data(self, notion_data: dict) -> dict:
        """
        Notion MCP에서 가져온 데이터를 파싱하여 DB에 로드

        Args:
            notion_data: {
                "worldbuilding": str (마크다운),
                "characters": str (마크다운),
                "events": str (마크다운),
                "concepts": [{"title": str, "content": str, "url": str}, ...]
            }
        """
        stats = {"loaded": 0, "errors": 0, "details": {}}

        # 1. 세계관 설정
        if "worldbuilding" in notion_data:
            settings = parse_worldbuilding(notion_data["worldbuilding"])
            save_json(settings, "world_settings.json")
            count = await self._load_world_settings(settings)
            stats["details"]["world_settings"] = count
            stats["loaded"] += count

        # 2. 인물
        if "characters" in notion_data:
            characters = parse_characters(notion_data["characters"])
            save_json(characters, "characters.json")
            count = await self._load_characters(characters)
            stats["details"]["characters"] = count
            stats["loaded"] += count

        # 3. 사건
        if "events" in notion_data:
            events = parse_events(notion_data["events"])
            save_json(events, "events.json")
            count = await self._load_events(events)
            stats["details"]["events"] = count
            stats["loaded"] += count

        # 4. 개념
        if "concepts" in notion_data:
            concepts = []
            for c in notion_data["concepts"]:
                concept = parse_concept(c["title"], c["content"], c.get("url", ""))
                concepts.append(concept)
            save_json(concepts, "concepts.json")
            count = await self._load_concepts(concepts)
            stats["details"]["concepts"] = count
            stats["loaded"] += count

        # 5. 관계 생성
        try:
            await self._create_relationships(notion_data)
        except Exception as e:
            stats["relationship_errors"] = str(e)

        return stats

    async def seed_from_json(self) -> dict:
        """기존 JSON 파일에서 DB에 로드"""
        stats = {"loaded": 0, "details": {}}

        for filename, loader in [
            ("world_settings.json", self._load_world_settings),
            ("characters.json", self._load_characters),
            ("events.json", self._load_events),
            ("concepts.json", self._load_concepts),
        ]:
            filepath = DATA_DIR / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                count = await loader(data)
                stats["details"][filename] = count
                stats["loaded"] += count

        return stats

    # === 내부 로드 함수 ===

    async def _load_world_settings(self, settings: list[dict]) -> int:
        """세계관 설정 로드"""
        count = 0
        for data in settings:
            try:
                entity = RunWorldSetting(
                    id=data["id"],
                    title=data["title"],
                    content=data.get("content", ""),
                    category=data.get("category", ""),
                    tags=data.get("tags", []),
                    sub_items=data.get("sub_items", []),
                )
                self.vector_repo.add_entity(entity, extra_metadata={"category": entity.category})
                count += 1
                try:
                    await self.neo4j_repo.create_world_setting(data)
                except Exception:
                    pass  # Neo4j 미연결 시 무시
            except Exception as e:
                print(f"  [Run] WorldSetting 로드 실패: {data.get('title', '?')} - {e}")
        return count

    async def _load_characters(self, characters: list[dict]) -> int:
        """인물 로드 (2청크: 기본정보 + 타임라인)"""
        count = 0
        for data in characters:
            try:
                entity = RunCharacter(
                    id=data["id"],
                    title=data["title"],
                    content=data.get("content", ""),
                    role=data.get("role", ""),
                    traits=data.get("traits", []),
                    abilities=data.get("abilities", []),
                    affiliations=data.get("affiliations", []),
                    timeline=data.get("timeline", []),
                    status=data.get("status", ""),
                    tags=data.get("tags", []),
                )
                chunks = [("bio", entity.get_searchable_text())]
                if entity.timeline:
                    chunks.append(("timeline", entity.get_timeline_text()))
                self.vector_repo.add_entity_chunks(entity, chunks)
                count += 1
                try:
                    await self.neo4j_repo.create_character(data)
                except Exception:
                    pass
            except Exception as e:
                print(f"  [Run] Character 로드 실패: {data.get('title', '?')} - {e}")
        return count

    async def _load_events(self, events: list[dict]) -> int:
        """사건 로드"""
        count = 0
        for data in events:
            try:
                entity = RunEvent(
                    id=data["id"],
                    title=data["title"],
                    content=data.get("content", ""),
                    time_period=data.get("time_period", ""),
                    location=data.get("location", ""),
                    participants=data.get("participants", []),
                    concepts_used=data.get("concepts_used", []),
                    outcome=data.get("outcome", ""),
                    order_index=data.get("order_index", 0),
                    tags=data.get("tags", []),
                )
                self.vector_repo.add_entity(entity, extra_metadata={
                    "time_period": entity.time_period,
                    "location": entity.location,
                })
                count += 1
                try:
                    await self.neo4j_repo.create_event(data)
                except Exception:
                    pass
            except Exception as e:
                print(f"  [Run] Event 로드 실패: {data.get('title', '?')} - {e}")
        return count

    async def _load_concepts(self, concepts: list[dict]) -> int:
        """개념 로드"""
        count = 0
        for data in concepts:
            try:
                entity = RunConcept(
                    id=data["id"],
                    title=data["title"],
                    content=data.get("content", ""),
                    definition=data.get("definition", ""),
                    purpose=data.get("purpose", ""),
                    world_position=data.get("world_position", ""),
                    related_concepts=data.get("related_concepts", []),
                    tags=data.get("tags", []),
                    source_url=data.get("source_url", ""),
                )
                self.vector_repo.add_entity(entity)
                count += 1
                try:
                    await self.neo4j_repo.create_concept(data)
                except Exception:
                    pass
            except Exception as e:
                print(f"  [Run] Concept 로드 실패: {data.get('title', '?')} - {e}")
        return count

    async def _create_relationships(self, notion_data: dict) -> None:
        """엔티티 간 관계 생성"""
        # 사건 시간순 관계 (FOLLOWS)
        events_file = DATA_DIR / "events.json"
        if events_file.exists():
            with open(events_file, "r", encoding="utf-8") as f:
                events = json.load(f)

            sorted_events = sorted(events, key=lambda e: e.get("order_index", 0))
            for i in range(len(sorted_events) - 1):
                try:
                    await self.neo4j_repo.create_event_follows(
                        sorted_events[i]["id"],
                        sorted_events[i + 1]["id"],
                    )
                except Exception:
                    pass

        # 인물-인물 관계 (KNOWS) — 하드코딩된 핵심 관계
        character_relations = [
            ("run_char_주인공", "run_char_테스", "employer"),
            ("run_char_주인공", "run_char_카우트", "employer"),
            ("run_char_주인공", "run_char_지원", "team_member"),
            ("run_char_주인공", "run_char_아버지", "adopted_child"),
            ("run_char_아버지", "run_char_세르게이", "same_organization"),
            ("run_char_세르게이", "run_char_도윤", "same_organization"),
        ]
        for char1, char2, rel_type in character_relations:
            try:
                await self.neo4j_repo.create_knows(char1, char2, rel_type)
            except Exception:
                pass
