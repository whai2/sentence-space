"""
Neo4j 시나리오 저장소

시나리오 패키지 CRUD 및 괴수 연결 그래프
"""
import json
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from domain.scenario.models import ScenarioPackage


class Neo4jScenarioRepository:
    """
    Neo4j 시나리오 저장소

    시나리오 노드 CRUD 및 관계 그래프 조회
    """

    def __init__(self, uri: str, username: str, password: str):
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri,
            auth=(username, password)
        )

    async def close(self):
        await self.driver.close()

    async def verify_connectivity(self) -> bool:
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
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None
    ) -> dict:
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "relationships_created": summary.counters.relationships_created,
                "properties_set": summary.counters.properties_set,
            }

    # ============================================
    # 시나리오 CRUD
    # ============================================

    async def create_scenario(self, scenario: ScenarioPackage) -> dict:
        """시나리오 노드 생성/업데이트"""
        query = """
        MERGE (s:Scenario {scenario_id: $scenario_id})
        SET s.title = $title,
            s.name = $name,
            s.type = $type,
            s.data = $data
        RETURN s
        """
        return await self.execute_write(query, {
            "scenario_id": scenario.id,
            "title": scenario.title,
            "name": scenario.name,
            "type": scenario.scenario_rule.type,
            "data": json.dumps(scenario.model_dump(mode="json"), ensure_ascii=False),
        })

    async def get_scenario(self, scenario_id: str) -> dict | None:
        """시나리오 단건 조회"""
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})
        WHERE s.data IS NOT NULL
        RETURN s
        """
        result = await self.execute_query(query, {"scenario_id": scenario_id})
        if not result:
            return None

        node = result[0]["s"]
        if node.get("data"):
            return json.loads(node["data"])
        return dict(node)

    async def list_scenarios(
        self,
        offset: int = 0,
        limit: int = 50,
        type_filter: str | None = None
    ) -> tuple[list[dict], int]:
        """시나리오 목록 조회 (페이지네이션)"""
        where_clause = "WHERE s.data IS NOT NULL"
        params: dict[str, Any] = {"offset": offset, "limit": limit}

        if type_filter:
            where_clause += " AND s.type = $type_filter"
            params["type_filter"] = type_filter

        # 총 개수
        count_query = f"""
        MATCH (s:Scenario)
        {where_clause}
        RETURN count(s) AS total
        """
        count_result = await self.execute_query(count_query, params)
        total = count_result[0]["total"] if count_result else 0

        # 페이지네이션
        list_query = f"""
        MATCH (s:Scenario)
        {where_clause}
        RETURN s
        ORDER BY s.scenario_id
        SKIP $offset LIMIT $limit
        """
        result = await self.execute_query(list_query, params)

        scenarios = []
        for record in result:
            node = record["s"]
            if node.get("data"):
                scenarios.append(json.loads(node["data"]))
            else:
                scenarios.append(dict(node))

        return scenarios, total

    async def get_scenario_with_beasts(self, scenario_id: str) -> dict | None:
        """시나리오 + 연결된 괴수 목록 조회"""
        scenario = await self.get_scenario(scenario_id)
        if not scenario:
            return None

        # 연결된 괴수 조회
        beast_query = """
        MATCH (b:Beast)-[r:APPEARS_IN]->(s:Scenario {scenario_id: $scenario_id})
        RETURN b.beast_id AS beast_id, b.title AS title, b.grade AS grade,
               b.species AS species, r.type AS appearance_type
        ORDER BY b.grade
        """
        beasts = await self.execute_query(beast_query, {"scenario_id": scenario_id})

        scenario["linked_beasts"] = beasts
        return scenario

    async def get_scenario_graph(self, limit: int = 100) -> dict:
        """시나리오 관계 그래프 (시각화용)"""
        query = """
        MATCH (s:Scenario)
        WHERE s.data IS NOT NULL
        OPTIONAL MATCH (b:Beast)-[r:APPEARS_IN]->(s)
        RETURN s, b, r
        LIMIT $limit
        """
        result = await self.execute_query(query, {"limit": limit})

        nodes = {}
        edges = []

        for record in result:
            s_node = record["s"]
            scenario_id = s_node.get("scenario_id", "")

            if scenario_id and scenario_id not in nodes:
                nodes[scenario_id] = {
                    "id": scenario_id,
                    "label": s_node.get("title", scenario_id),
                    "type": "Scenario",
                    "properties": {
                        "name": s_node.get("name", ""),
                        "scenario_type": s_node.get("type", ""),
                    }
                }

            b_node = record.get("b")
            if b_node:
                beast_id = b_node.get("beast_id", "")
                if beast_id and beast_id not in nodes:
                    nodes[beast_id] = {
                        "id": beast_id,
                        "label": b_node.get("title", beast_id),
                        "type": "Beast",
                        "properties": {
                            "grade": b_node.get("grade", ""),
                            "species": b_node.get("species", ""),
                        }
                    }

                rel = record.get("r")
                if rel and beast_id:
                    edges.append({
                        "from": beast_id,
                        "to": scenario_id,
                        "type": "APPEARS_IN",
                        "properties": {"appearance_type": rel.get("type", "normal")}
                    })

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    async def get_stats(self) -> dict:
        """시나리오 통계"""
        query = """
        MATCH (s:Scenario)
        WHERE s.data IS NOT NULL
        RETURN s.type AS type, count(s) AS count
        """
        result = await self.execute_query(query)
        type_distribution = {r["type"]: r["count"] for r in result if r["type"]}

        total_query = """
        MATCH (s:Scenario)
        WHERE s.data IS NOT NULL
        RETURN count(s) AS total
        """
        total_result = await self.execute_query(total_query)
        total = total_result[0]["total"] if total_result else 0

        return {
            "total": total,
            "type_distribution": type_distribution,
        }

    async def delete_scenario(self, scenario_id: str) -> bool:
        """시나리오 삭제 (노드의 data 속성만 제거, 괴수 연결은 유지)"""
        query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})
        REMOVE s.data, s.title, s.name, s.type
        RETURN s
        """
        result = await self.execute_query(query, {"scenario_id": scenario_id})
        return len(result) > 0

    async def clear_all_scenario_data(self) -> int:
        """모든 시나리오의 data 속성 일괄 제거"""
        query = """
        MATCH (s:Scenario)
        WHERE s.data IS NOT NULL
        REMOVE s.data, s.title, s.name, s.type
        RETURN count(s) AS cleared
        """
        result = await self.execute_query(query)
        return result[0]["cleared"] if result else 0

    # ============================================
    # 인덱스 / 제약조건
    # ============================================

    async def create_constraints(self):
        """유니크 제약조건 생성"""
        try:
            await self.execute_write(
                "CREATE CONSTRAINT scenario_id_unique IF NOT EXISTS "
                "FOR (s:Scenario) REQUIRE s.scenario_id IS UNIQUE"
            )
        except Exception as e:
            print(f"Scenario 제약조건 생성 실패 (이미 존재할 수 있음): {e}")

    async def create_indexes(self):
        """인덱스 생성"""
        try:
            await self.execute_write(
                "CREATE INDEX scenario_type_idx IF NOT EXISTS "
                "FOR (s:Scenario) ON (s.type)"
            )
        except Exception as e:
            print(f"Scenario 인덱스 생성 실패: {e}")
