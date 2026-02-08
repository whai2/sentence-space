"""
Neo4j 멸살법 저장소

괴수 간 관계 그래프 (진화 계통, 시나리오 연결 등)
"""
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from domain.myeolsal.models import BeastEntry


class Neo4jMyeolsalRepository:
    """
    Neo4j 멸살법 저장소

    괴수 간 관계 그래프 CRUD
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
        """Neo4j 연결 확인"""
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
        """Cypher 쿼리 실행"""
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None
    ) -> dict:
        """Write 트랜잭션 실행"""
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "relationships_created": summary.counters.relationships_created,
                "properties_set": summary.counters.properties_set,
            }

    # ============================================
    # 괴수 노드 CRUD
    # ============================================

    async def create_beast_node(self, beast: BeastEntry) -> dict:
        """괴수 노드 생성"""
        query = """
        MERGE (b:Beast {beast_id: $beast_id})
        SET b.title = $title,
            b.grade = $grade,
            b.species = $species,
            b.danger_class = $danger_class,
            b.layer = $layer,
            b.description = $description
        RETURN b
        """
        result = await self.execute_query(query, {
            "beast_id": beast.id,
            "title": beast.title,
            "grade": beast.grade,
            "species": beast.species,
            "danger_class": beast.danger_class,
            "layer": beast.layer.value,
            "description": beast.description[:500],  # 설명 일부만 저장
        })
        return result[0]["b"] if result else {}

    async def get_beast_by_id(self, beast_id: str) -> dict | None:
        """괴수 노드 조회"""
        query = """
        MATCH (b:Beast {beast_id: $beast_id})
        RETURN b
        """
        result = await self.execute_query(query, {"beast_id": beast_id})
        return result[0]["b"] if result else None

    async def delete_beast_node(self, beast_id: str) -> bool:
        """괴수 노드 삭제 (관계 포함)"""
        query = """
        MATCH (b:Beast {beast_id: $beast_id})
        DETACH DELETE b
        """
        result = await self.execute_write(query, {"beast_id": beast_id})
        return result.get("nodes_deleted", 0) > 0

    # ============================================
    # 진화 관계
    # ============================================

    async def create_evolution_relation(
        self,
        from_beast_id: str,
        to_beast_id: str,
        evolution_condition: str = ""
    ) -> dict:
        """
        진화 관계 생성

        Args:
            from_beast_id: 원래 괴수 ID
            to_beast_id: 진화 후 괴수 ID
            evolution_condition: 진화 조건 설명

        Returns:
            생성 결과
        """
        query = """
        MATCH (b1:Beast {beast_id: $from_id})
        MATCH (b2:Beast {beast_id: $to_id})
        MERGE (b1)-[r:EVOLVES_TO {condition: $condition}]->(b2)
        RETURN r
        """
        return await self.execute_write(query, {
            "from_id": from_beast_id,
            "to_id": to_beast_id,
            "condition": evolution_condition
        })

    async def get_evolution_tree(self, beast_id: str) -> list[dict]:
        """
        진화 계통 조회 (전체 트리)

        Args:
            beast_id: 기준 괴수 ID

        Returns:
            진화 계통 리스트
        """
        query = """
        MATCH path = (start:Beast)-[:EVOLVES_TO*0..5]->(end:Beast)
        WHERE start.beast_id = $beast_id OR end.beast_id = $beast_id
        RETURN [node in nodes(path) | {
            beast_id: node.beast_id,
            title: node.title,
            grade: node.grade
        }] as evolution_chain
        """
        result = await self.execute_query(query, {"beast_id": beast_id})
        return result

    async def get_pre_evolution(self, beast_id: str) -> dict | None:
        """이전 진화 단계 조회"""
        query = """
        MATCH (pre:Beast)-[:EVOLVES_TO]->(b:Beast {beast_id: $beast_id})
        RETURN pre
        """
        result = await self.execute_query(query, {"beast_id": beast_id})
        return result[0]["pre"] if result else None

    async def get_next_evolution(self, beast_id: str) -> list[dict]:
        """다음 진화 단계 조회"""
        query = """
        MATCH (b:Beast {beast_id: $beast_id})-[:EVOLVES_TO]->(next:Beast)
        RETURN next
        """
        result = await self.execute_query(query, {"beast_id": beast_id})
        return [r["next"] for r in result]

    # ============================================
    # 시나리오 연결
    # ============================================

    async def link_to_scenario(
        self,
        beast_id: str,
        scenario_id: str,
        appearance_type: str = "normal"
    ) -> dict:
        """
        괴수-시나리오 연결

        Args:
            beast_id: 괴수 ID
            scenario_id: 시나리오 ID
            appearance_type: 출현 유형 (normal, boss, hidden)

        Returns:
            생성 결과
        """
        query = """
        MATCH (b:Beast {beast_id: $beast_id})
        MERGE (s:Scenario {scenario_id: $scenario_id})
        MERGE (b)-[r:APPEARS_IN {type: $appearance_type}]->(s)
        RETURN r
        """
        return await self.execute_write(query, {
            "beast_id": beast_id,
            "scenario_id": scenario_id,
            "appearance_type": appearance_type
        })

    async def get_beasts_in_scenario(self, scenario_id: str) -> list[dict]:
        """시나리오에 출현하는 괴수 목록"""
        query = """
        MATCH (b:Beast)-[r:APPEARS_IN]->(s:Scenario {scenario_id: $scenario_id})
        RETURN b, r.type as appearance_type
        ORDER BY b.grade
        """
        result = await self.execute_query(query, {"scenario_id": scenario_id})
        return [{"beast": r["b"], "type": r["appearance_type"]} for r in result]

    async def get_scenarios_for_beast(self, beast_id: str) -> list[dict]:
        """괴수가 출현하는 시나리오 목록"""
        query = """
        MATCH (b:Beast {beast_id: $beast_id})-[r:APPEARS_IN]->(s:Scenario)
        RETURN s, r.type as appearance_type
        """
        result = await self.execute_query(query, {"beast_id": beast_id})
        return [{"scenario": r["s"], "type": r["appearance_type"]} for r in result]

    # ============================================
    # 관련 괴수 관계
    # ============================================

    async def create_related_relation(
        self,
        beast_id_1: str,
        beast_id_2: str,
        relation_type: str = "related"
    ) -> dict:
        """
        관련 괴수 관계 생성

        Args:
            beast_id_1: 첫 번째 괴수 ID
            beast_id_2: 두 번째 괴수 ID
            relation_type: 관계 유형 (related, same_species, counterpart)

        Returns:
            생성 결과
        """
        query = """
        MATCH (b1:Beast {beast_id: $id1})
        MATCH (b2:Beast {beast_id: $id2})
        MERGE (b1)-[r:RELATED_TO {type: $type}]-(b2)
        RETURN r
        """
        return await self.execute_write(query, {
            "id1": beast_id_1,
            "id2": beast_id_2,
            "type": relation_type
        })

    async def get_related_beasts(self, beast_id: str) -> list[dict]:
        """관련 괴수 조회"""
        query = """
        MATCH (b:Beast {beast_id: $beast_id})-[r]-(related:Beast)
        RETURN related, type(r) as relation_type, r.type as sub_type
        """
        result = await self.execute_query(query, {"beast_id": beast_id})
        return result

    # ============================================
    # 종/등급별 그룹 조회
    # ============================================

    async def get_beasts_by_species(self, species: str) -> list[dict]:
        """종별 괴수 목록"""
        query = """
        MATCH (b:Beast {species: $species})
        RETURN b
        ORDER BY b.grade
        """
        result = await self.execute_query(query, {"species": species})
        return [r["b"] for r in result]

    async def get_beasts_by_grade(self, grade: str) -> list[dict]:
        """등급별 괴수 목록"""
        query = """
        MATCH (b:Beast {grade: $grade})
        RETURN b
        ORDER BY b.species, b.title
        """
        result = await self.execute_query(query, {"grade": grade})
        return [r["b"] for r in result]

    # ============================================
    # 초기화 및 관리
    # ============================================

    async def create_constraints(self):
        """제약 조건 생성"""
        constraints = [
            "CREATE CONSTRAINT beast_id IF NOT EXISTS FOR (b:Beast) REQUIRE b.beast_id IS UNIQUE",
        ]
        for constraint in constraints:
            try:
                await self.execute_write(constraint)
            except Exception:
                pass  # 이미 존재하는 경우 무시

    async def create_indexes(self):
        """인덱스 생성"""
        indexes = [
            "CREATE INDEX beast_grade IF NOT EXISTS FOR (b:Beast) ON (b.grade)",
            "CREATE INDEX beast_species IF NOT EXISTS FOR (b:Beast) ON (b.species)",
        ]
        for index in indexes:
            try:
                await self.execute_write(index)
            except Exception:
                pass

    async def clear_all_beasts(self):
        """모든 괴수 데이터 삭제 (주의: 개발용)"""
        query = "MATCH (b:Beast) DETACH DELETE b"
        await self.execute_write(query)

    async def get_node_count(self) -> dict[str, int]:
        """노드 통계"""
        query = """
        MATCH (n)
        WHERE n:Beast OR n:Scenario
        RETURN labels(n)[0] as label, count(n) as count
        """
        result = await self.execute_query(query)
        return {r["label"]: r["count"] for r in result}

    async def get_full_graph(self, limit: int = 100) -> dict:
        """
        전체 그래프 조회 (시각화용)

        Returns:
            nodes와 edges 리스트
        """
        query = """
        MATCH (b:Beast)
        OPTIONAL MATCH (b)-[r]->(other)
        RETURN b, collect({
            target: other.beast_id,
            type: type(r),
            properties: properties(r)
        }) as relations
        LIMIT $limit
        """
        result = await self.execute_query(query, {"limit": limit})

        nodes = []
        edges = []
        seen_nodes = set()

        for record in result:
            beast = record["b"]
            if beast["beast_id"] not in seen_nodes:
                nodes.append({
                    "id": beast["beast_id"],
                    "label": beast["title"],
                    "grade": beast["grade"],
                    "species": beast["species"]
                })
                seen_nodes.add(beast["beast_id"])

            for rel in record["relations"]:
                if rel["target"]:
                    edges.append({
                        "source": beast["beast_id"],
                        "target": rel["target"],
                        "type": rel["type"],
                        "properties": rel["properties"]
                    })

        return {"nodes": nodes, "edges": edges}
