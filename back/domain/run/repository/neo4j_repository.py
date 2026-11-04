"""
Neo4j 런 세계관 저장소

인물, 개념, 사건, 세계관 설정 간의 관계를 그래프로 관리
"""
from typing import Any

from neo4j import AsyncGraphDatabase


class Neo4jRunRepository:
    """
    런 세계관 Neo4j 그래프 저장소

    노드: RunCharacter, RunConcept, RunEvent, RunWorldSetting
    관계: PARTICIPATES_IN, KNOWS, USED_IN, RELATED_TO, FOLLOWS, AFFILIATED_WITH 등
    """

    def __init__(self, uri: str, username: str, password: str):
        self._driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

    async def close(self):
        await self._driver.close()

    async def verify_connectivity(self) -> bool:
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def execute_query(self, query: str, parameters: dict | None = None) -> list[dict]:
        """읽기 쿼리 실행"""
        async with self._driver.session() as session:
            result = await session.run(query, parameters or {})
            return [record.data() async for record in result]

    async def execute_write(self, query: str, parameters: dict | None = None) -> dict:
        """쓰기 쿼리 실행"""
        async with self._driver.session() as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "relationships_created": summary.counters.relationships_created,
            }

    # === 노드 CRUD ===

    async def create_character(self, data: dict) -> dict:
        """인물 노드 생성/업데이트"""
        query = """
        MERGE (c:RunCharacter {id: $id})
        SET c.title = $title,
            c.role = $role,
            c.status = $status,
            c.affiliations = $affiliations
        RETURN c
        """
        return await self.execute_write(query, {
            "id": data["id"],
            "title": data["title"],
            "role": data.get("role", ""),
            "status": data.get("status", ""),
            "affiliations": data.get("affiliations", []),
        })

    async def create_concept(self, data: dict) -> dict:
        """개념 노드 생성/업데이트"""
        query = """
        MERGE (c:RunConcept {id: $id})
        SET c.title = $title,
            c.definition = $definition,
            c.tags = $tags
        RETURN c
        """
        return await self.execute_write(query, {
            "id": data["id"],
            "title": data["title"],
            "definition": data.get("definition", "")[:500],
            "tags": data.get("tags", []),
        })

    async def create_event(self, data: dict) -> dict:
        """사건 노드 생성/업데이트"""
        query = """
        MERGE (e:RunEvent {id: $id})
        SET e.title = $title,
            e.time_period = $time_period,
            e.location = $location,
            e.order_index = $order_index
        RETURN e
        """
        return await self.execute_write(query, {
            "id": data["id"],
            "title": data["title"],
            "time_period": data.get("time_period", ""),
            "location": data.get("location", ""),
            "order_index": data.get("order_index", 0),
        })

    async def create_world_setting(self, data: dict) -> dict:
        """세계관 설정 노드 생성/업데이트"""
        query = """
        MERGE (w:RunWorldSetting {id: $id})
        SET w.title = $title,
            w.category = $category
        RETURN w
        """
        return await self.execute_write(query, {
            "id": data["id"],
            "title": data["title"],
            "category": data.get("category", ""),
        })

    async def delete_node(self, node_id: str) -> bool:
        """노드 삭제 (모든 관계 포함)"""
        query = """
        MATCH (n {id: $id})
        DETACH DELETE n
        """
        result = await self.execute_write(query, {"id": node_id})
        return result.get("nodes_created", 0) >= 0

    # === 관계 생성 ===

    async def create_participates_in(self, character_id: str, event_id: str, role: str = "") -> dict:
        """인물 → 사건 참여 관계"""
        query = """
        MATCH (c:RunCharacter {id: $char_id})
        MATCH (e:RunEvent {id: $event_id})
        MERGE (c)-[r:PARTICIPATES_IN]->(e)
        SET r.role = $role
        RETURN type(r) as type
        """
        return await self.execute_write(query, {
            "char_id": character_id,
            "event_id": event_id,
            "role": role,
        })

    async def create_knows(self, char1_id: str, char2_id: str, relation_type: str = "knows") -> dict:
        """인물 ↔ 인물 관계"""
        query = """
        MATCH (c1:RunCharacter {id: $id1})
        MATCH (c2:RunCharacter {id: $id2})
        MERGE (c1)-[r:KNOWS]->(c2)
        SET r.relation_type = $type
        RETURN type(r) as type
        """
        return await self.execute_write(query, {
            "id1": char1_id,
            "id2": char2_id,
            "type": relation_type,
        })

    async def create_concept_used_in(self, concept_id: str, event_id: str) -> dict:
        """개념 → 사건 사용 관계"""
        query = """
        MATCH (c:RunConcept {id: $concept_id})
        MATCH (e:RunEvent {id: $event_id})
        MERGE (c)-[r:USED_IN]->(e)
        RETURN type(r) as type
        """
        return await self.execute_write(query, {
            "concept_id": concept_id,
            "event_id": event_id,
        })

    async def create_concept_related(self, concept1_id: str, concept2_id: str) -> dict:
        """개념 ↔ 개념 관련 관계"""
        query = """
        MATCH (c1:RunConcept {id: $id1})
        MATCH (c2:RunConcept {id: $id2})
        MERGE (c1)-[r:RELATED_TO]->(c2)
        RETURN type(r) as type
        """
        return await self.execute_write(query, {"id1": concept1_id, "id2": concept2_id})

    async def create_event_follows(self, prev_event_id: str, next_event_id: str) -> dict:
        """사건 → 사건 시간순 관계"""
        query = """
        MATCH (e1:RunEvent {id: $prev_id})
        MATCH (e2:RunEvent {id: $next_id})
        MERGE (e1)-[r:FOLLOWS]->(e2)
        RETURN type(r) as type
        """
        return await self.execute_write(query, {
            "prev_id": prev_event_id,
            "next_id": next_event_id,
        })

    async def create_affiliated_with(self, character_id: str, setting_id: str) -> dict:
        """인물 → 조직 소속 관계"""
        query = """
        MATCH (c:RunCharacter {id: $char_id})
        MATCH (w:RunWorldSetting {id: $setting_id})
        MERGE (c)-[r:AFFILIATED_WITH]->(w)
        RETURN type(r) as type
        """
        return await self.execute_write(query, {
            "char_id": character_id,
            "setting_id": setting_id,
        })

    # === 조회 ===

    async def get_related_entities(self, entity_id: str) -> list[dict]:
        """엔티티와 연결된 모든 노드 조회"""
        query = """
        MATCH (n {id: $id})-[r]-(m)
        RETURN m.id as id, m.title as title, labels(m)[0] as label,
               type(r) as relation_type,
               CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END as direction
        """
        return await self.execute_query(query, {"id": entity_id})

    async def get_character_timeline(self, character_id: str) -> list[dict]:
        """인물의 사건 시간순 조회"""
        query = """
        MATCH (c:RunCharacter {id: $id})-[:PARTICIPATES_IN]->(e:RunEvent)
        RETURN e.id as id, e.title as title, e.time_period as time_period,
               e.location as location, e.order_index as order_index
        ORDER BY e.order_index
        """
        return await self.execute_query(query, {"id": character_id})

    async def get_concept_usage(self, concept_id: str) -> dict:
        """개념이 사용된 사건 + 관련 개념 조회"""
        events_query = """
        MATCH (c:RunConcept {id: $id})-[:USED_IN]->(e:RunEvent)
        RETURN e.id as id, e.title as title, e.time_period as time_period
        ORDER BY e.order_index
        """
        related_query = """
        MATCH (c:RunConcept {id: $id})-[:RELATED_TO]-(other:RunConcept)
        RETURN other.id as id, other.title as title
        """
        events = await self.execute_query(events_query, {"id": concept_id})
        related = await self.execute_query(related_query, {"id": concept_id})
        return {"events": events, "related_concepts": related}

    async def get_event_context(self, event_id: str) -> dict:
        """사건의 전체 컨텍스트 (참여자, 관련 개념, 전후 사건)"""
        participants_q = """
        MATCH (c:RunCharacter)-[:PARTICIPATES_IN]->(e:RunEvent {id: $id})
        RETURN c.id as id, c.title as title, c.role as role
        """
        concepts_q = """
        MATCH (c:RunConcept)-[:USED_IN]->(e:RunEvent {id: $id})
        RETURN c.id as id, c.title as title
        """
        prev_q = """
        MATCH (prev:RunEvent)-[:FOLLOWS]->(e:RunEvent {id: $id})
        RETURN prev.id as id, prev.title as title
        """
        next_q = """
        MATCH (e:RunEvent {id: $id})-[:FOLLOWS]->(next:RunEvent)
        RETURN next.id as id, next.title as title
        """
        participants = await self.execute_query(participants_q, {"id": event_id})
        concepts = await self.execute_query(concepts_q, {"id": event_id})
        prev_events = await self.execute_query(prev_q, {"id": event_id})
        next_events = await self.execute_query(next_q, {"id": event_id})

        return {
            "participants": participants,
            "concepts": concepts,
            "prev_events": prev_events,
            "next_events": next_events,
        }

    async def get_full_graph(self, limit: int = 100) -> dict:
        """시각화용 전체 그래프 데이터"""
        nodes_query = """
        MATCH (n)
        WHERE n:RunCharacter OR n:RunConcept OR n:RunEvent OR n:RunWorldSetting
        RETURN n.id as id, n.title as title, labels(n)[0] as label
        LIMIT $limit
        """
        edges_query = """
        MATCH (a)-[r]->(b)
        WHERE (a:RunCharacter OR a:RunConcept OR a:RunEvent OR a:RunWorldSetting)
          AND (b:RunCharacter OR b:RunConcept OR b:RunEvent OR b:RunWorldSetting)
        RETURN a.id as source, b.id as target, type(r) as relation_type
        LIMIT $limit
        """
        nodes = await self.execute_query(nodes_query, {"limit": limit})
        edges = await self.execute_query(edges_query, {"limit": limit * 2})
        return {"nodes": nodes, "edges": edges}

    # === 초기화 ===

    async def create_constraints(self) -> None:
        """유니크 제약 조건 생성"""
        for label in ("RunCharacter", "RunConcept", "RunEvent", "RunWorldSetting"):
            try:
                await self.execute_write(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )
            except Exception:
                pass

    async def create_indexes(self) -> None:
        """검색 인덱스 생성"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:RunCharacter) ON (n.title)",
            "CREATE INDEX IF NOT EXISTS FOR (n:RunConcept) ON (n.title)",
            "CREATE INDEX IF NOT EXISTS FOR (n:RunEvent) ON (n.time_period)",
            "CREATE INDEX IF NOT EXISTS FOR (n:RunEvent) ON (n.order_index)",
            "CREATE INDEX IF NOT EXISTS FOR (n:RunWorldSetting) ON (n.category)",
        ]
        for idx in indexes:
            try:
                await self.execute_write(idx)
            except Exception:
                pass

    async def clear_all(self) -> None:
        """런 관련 노드 전체 삭제 (개발용)"""
        await self.execute_write("""
            MATCH (n)
            WHERE n:RunCharacter OR n:RunConcept OR n:RunEvent OR n:RunWorldSetting
            DETACH DELETE n
        """)

    async def get_node_count(self) -> dict:
        """노드 수 통계"""
        counts = {}
        for label in ("RunCharacter", "RunConcept", "RunEvent", "RunWorldSetting"):
            result = await self.execute_query(f"MATCH (n:{label}) RETURN count(n) as cnt")
            counts[label] = result[0]["cnt"] if result else 0
        return counts
