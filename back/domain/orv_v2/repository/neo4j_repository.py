"""
Neo4j Graph Database Repository

시나리오 지식 그래프 저장 및 조회
"""
from typing import Any
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from pydantic import BaseModel


class Neo4jGraphRepository:
    """
    Neo4j 그래프 데이터베이스 저장소

    시나리오 지식 그래프 CRUD 및 Cypher 쿼리 실행
    """

    def __init__(self, uri: str, username: str, password: str):
        """
        Args:
            uri: Neo4j Bolt URI (예: bolt://localhost:7687)
            username: Neo4j 사용자명
            password: Neo4j 비밀번호
        """
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri,
            auth=(username, password)
        )

    async def close(self):
        """드라이버 연결 종료"""
        await self.driver.close()

    async def verify_connectivity(self) -> bool:
        """
        Neo4j 연결 확인

        Returns:
            연결 성공 여부
        """
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS num")
                record = await result.single()
                return record["num"] == 1
        except Exception as e:
            print(f"Neo4j 연결 실패: {e}")
            return False

    # ============================================
    # 기본 쿼리 실행
    # ============================================

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None
    ) -> list[dict]:
        """
        Cypher 쿼리 실행

        Args:
            query: Cypher 쿼리 문자열
            parameters: 쿼리 파라미터

        Returns:
            쿼리 결과 레코드 리스트
        """
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None
    ) -> dict:
        """
        Write 트랜잭션 실행

        Args:
            query: Cypher 쿼리 문자열
            parameters: 쿼리 파라미터

        Returns:
            실행 결과 요약
        """
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "relationships_created": summary.counters.relationships_created,
                "properties_set": summary.counters.properties_set,
            }

    # ============================================
    # 시나리오 조회
    # ============================================

    async def get_scenario_by_id(self, scenario_id: str) -> dict | None:
        """
        시나리오 기본 정보 조회

        Args:
            scenario_id: 시나리오 ID

        Returns:
            시나리오 정보 또는 None
        """
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})
        RETURN s
        """
        records = await self.execute_query(query, {"scenario_id": scenario_id})

        if not records:
            return None

        return records[0]["s"]

    async def get_scenario_full_context(self, scenario_id: str) -> dict:
        """
        시나리오 전체 컨텍스트 조회 (등장인물, 규칙, 트릭 등)

        Args:
            scenario_id: 시나리오 ID

        Returns:
            시나리오 전체 정보
        """
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})

        // 등장인물
        OPTIONAL MATCH (s)-[app:APPEARS_IN]->(c:Character)

        // 규칙
        OPTIONAL MATCH (s)-[:REQUIRES]->(r:Rule)

        // 트릭
        OPTIONAL MATCH (r)-[alt:ALTERNATIVE_SOLUTION]->(t:Trick)

        // 위치
        OPTIONAL MATCH (c)-[:LOCATED_IN]->(loc:Location)

        // 시스템 메시지
        OPTIONAL MATCH (msg:SystemMessage)
        WHERE msg.display_timing IN ['scenario_start', 'before_blue_screen']

        // 이벤트
        OPTIONAL MATCH (e:Event)
        WHERE e.trigger_condition CONTAINS 'turn'

        RETURN s,
               collect(DISTINCT {
                   character: c,
                   role: app.role,
                   is_critical: app.is_critical,
                   appearance_turn: app.appearance_turn
               }) as characters,
               collect(DISTINCT r) as rules,
               collect(DISTINCT {
                   trick: t,
                   difficulty: alt.difficulty,
                   morality_score: alt.morality_score
               }) as tricks,
               collect(DISTINCT loc) as locations,
               collect(DISTINCT msg) as messages,
               collect(DISTINCT e) as events
        """

        records = await self.execute_query(query, {"scenario_id": scenario_id})

        if not records:
            return {}

        return records[0]

    async def get_protagonist_tricks(self, scenario_id: str) -> list[dict]:
        """
        주인공 전용 트릭 조회 (김독자만 아는 정보)

        Args:
            scenario_id: 시나리오 ID

        Returns:
            트릭 리스트
        """
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})-[:REQUIRES]->(r:Rule)
        MATCH (r)-[alt:ALTERNATIVE_SOLUTION]->(t:Trick)
        WHERE t.is_protagonist_knowledge = true
        RETURN t.trick_id as trick_id,
               t.name as name,
               t.description as description,
               t.narrative_hint as narrative_hint,
               alt.difficulty as difficulty,
               alt.morality_score as morality_score
        ORDER BY alt.difficulty ASC
        """

        records = await self.execute_query(query, {"scenario_id": scenario_id})
        return records

    async def get_character_relationships(self, scenario_id: str) -> list[dict]:
        """
        캐릭터 간 관계 조회

        Args:
            scenario_id: 시나리오 ID

        Returns:
            캐릭터 관계 리스트
        """
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})-[:APPEARS_IN]->(c1:Character)
        OPTIONAL MATCH (c1)-[rel:CONFLICTS_WITH]->(c2:Character)
        RETURN c1.name as character1,
               c1.role as role1,
               c2.name as character2,
               rel.conflict_type as conflict_type,
               rel.intensity as intensity
        """

        records = await self.execute_query(query, {"scenario_id": scenario_id})
        return records

    async def get_alternative_solutions(self, scenario_id: str) -> list[dict]:
        """
        대안 솔루션 조회 (도덕성 점수 기준 정렬)

        Args:
            scenario_id: 시나리오 ID

        Returns:
            대안 솔루션 리스트
        """
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})-[:REQUIRES]->(r:Rule)
        MATCH (r)-[alt:ALTERNATIVE_SOLUTION]->(t:Trick)
        RETURN t.name as name,
               t.description as description,
               alt.difficulty as difficulty,
               alt.morality_score as morality_score
        ORDER BY alt.morality_score DESC, alt.difficulty ASC
        """

        records = await self.execute_query(query, {"scenario_id": scenario_id})
        return records

    # ============================================
    # 초기화 및 관리
    # ============================================

    async def create_constraints(self):
        """
        제약 조건 생성 (Unique ID)
        """
        constraints = [
            "CREATE CONSTRAINT scenario_id IF NOT EXISTS FOR (s:Scenario) REQUIRE s.scenario_id IS UNIQUE",
            "CREATE CONSTRAINT character_id IF NOT EXISTS FOR (c:Character) REQUIRE c.character_id IS UNIQUE",
            "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.location_id IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT rule_id IF NOT EXISTS FOR (r:Rule) REQUIRE r.rule_id IS UNIQUE",
            "CREATE CONSTRAINT trick_id IF NOT EXISTS FOR (t:Trick) REQUIRE t.trick_id IS UNIQUE",
        ]

        for constraint in constraints:
            await self.execute_write(constraint)

    async def clear_all_data(self):
        """
        모든 데이터 삭제 (주의: 개발용)
        """
        query = "MATCH (n) DETACH DELETE n"
        await self.execute_write(query)

    async def get_node_count(self) -> dict[str, int]:
        """
        노드 타입별 개수 조회

        Returns:
            노드 타입별 개수
        """
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """

        records = await self.execute_query(query)
        return {record["label"]: record["count"] for record in records}

    # ============================================
    # 노드 생성 (초기화 스크립트용)
    # ============================================

    async def create_scenario(self, data: dict) -> dict:
        """시나리오 노드 생성"""
        query = """
        MERGE (s:Scenario {scenario_id: $scenario_id})
        SET s += $properties
        RETURN s
        """
        properties = {k: v for k, v in data.items() if k != "scenario_id"}
        result = await self.execute_query(query, {
            "scenario_id": data["scenario_id"],
            "properties": properties
        })
        return result[0]["s"] if result else {}

    async def create_phase(self, scenario_id: str, data: dict) -> dict:
        """스토리 페이즈 생성 및 시나리오와 연결"""
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})
        MERGE (p:Phase {phase_id: $phase_id})
        SET p += $properties
        MERGE (s)-[:HAS_PHASE]->(p)
        RETURN p
        """
        properties = {k: v for k, v in data.items() if k != "phase_id"}
        result = await self.execute_query(query, {
            "scenario_id": scenario_id,
            "phase_id": data["phase_id"],
            "properties": properties
        })
        return result[0]["p"] if result else {}

    async def create_character(self, scenario_id: str, data: dict) -> dict:
        """캐릭터 노드 생성 및 시나리오와 연결"""
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})
        MERGE (c:Character {character_id: $character_id})
        SET c += $properties
        MERGE (s)-[:HAS_CHARACTER]->(c)
        RETURN c
        """
        properties = {k: v for k, v in data.items() if k != "character_id"}
        result = await self.execute_query(query, {
            "scenario_id": scenario_id,
            "character_id": data["character_id"],
            "properties": properties
        })
        return result[0]["c"] if result else {}

    async def create_event(self, scenario_id: str, data: dict) -> dict:
        """이벤트 노드 생성 및 페이즈와 연결"""
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})
        MATCH (p:Phase {phase_id: $phase_id})
        MERGE (e:Event {event_id: $event_id})
        SET e += $properties
        MERGE (p)-[:CONTAINS_EVENT]->(e)
        RETURN e
        """
        phase_id = data.pop("phase_id")
        properties = {k: v for k, v in data.items() if k != "event_id"}
        result = await self.execute_query(query, {
            "scenario_id": scenario_id,
            "phase_id": phase_id,
            "event_id": data["event_id"],
            "properties": properties
        })
        return result[0]["e"] if result else {}

    async def create_rule(self, scenario_id: str, data: dict) -> dict:
        """규칙 노드 생성 및 시나리오와 연결"""
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})
        MERGE (r:Rule {rule_id: $rule_id})
        SET r += $properties
        MERGE (s)-[:REQUIRES]->(r)
        RETURN r
        """
        properties = {k: v for k, v in data.items() if k != "rule_id"}
        result = await self.execute_query(query, {
            "scenario_id": scenario_id,
            "rule_id": data["rule_id"],
            "properties": properties
        })
        return result[0]["r"] if result else {}

    async def create_trick(self, scenario_id: str, data: dict) -> dict:
        """트릭 노드 생성 및 규칙과 연결"""
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})-[:REQUIRES]->(r:Rule)
        WHERE r.rule_type = 'win_condition'
        MERGE (t:Trick {trick_id: $trick_id})
        SET t += $properties
        MERGE (r)-[:ALTERNATIVE_SOLUTION {
            difficulty: $difficulty,
            morality_score: $morality_score
        }]->(t)
        RETURN t
        """
        properties = {k: v for k, v in data.items()
                     if k not in ["trick_id", "morality_score"]}
        morality_score = data.get("morality_score", 5)

        result = await self.execute_query(query, {
            "scenario_id": scenario_id,
            "trick_id": data["trick_id"],
            "properties": properties,
            "difficulty": data.get("difficulty_to_discover", 5),
            "morality_score": morality_score
        })
        return result[0]["t"] if result else {}

    async def create_location(self, scenario_id: str, data: dict) -> dict:
        """위치 노드 생성 및 시나리오와 연결"""
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})
        MERGE (l:Location {location_id: $location_id})
        SET l += $properties
        MERGE (s)-[:HAS_LOCATION]->(l)
        RETURN l
        """
        properties = {k: v for k, v in data.items() if k != "location_id"}
        result = await self.execute_query(query, {
            "scenario_id": scenario_id,
            "location_id": data["location_id"],
            "properties": properties
        })
        return result[0]["l"] if result else {}


# Legacy class name alias
Neo4jRepository = Neo4jGraphRepository
