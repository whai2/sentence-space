"""
Graph Visualization API Routes

Neo4j 지식 그래프 시각화를 위한 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from domain.orv_v2.container.container import get_neo4j_repository


router = APIRouter(prefix="/api/graph", tags=["graph"])


class GraphNode(BaseModel):
    """그래프 노드"""
    id: str
    label: str
    type: str
    properties: dict


class GraphEdge(BaseModel):
    """그래프 엣지"""
    id: str
    from_id: str
    to_id: str
    type: str
    properties: dict


class GraphData(BaseModel):
    """전체 그래프 데이터"""
    nodes: list[GraphNode]
    edges: list[GraphEdge]


@router.get("/scenarios", response_model=GraphData)
async def get_scenario_graph(scenario_id: str | None = None):
    """
    시나리오 지식 그래프 조회

    Args:
        scenario_id: 특정 시나리오 ID (없으면 전체)

    Returns:
        노드와 엣지 데이터
    """
    repo = get_neo4j_repository()

    try:
        if scenario_id:
            # 특정 시나리오와 관련된 노드만
            # 노드 조회
            nodes_query = """
            MATCH (s:Scenario {scenario_id: $scenario_id})
            OPTIONAL MATCH (s)-[]-(n)
            WITH s, collect(DISTINCT n) as related_nodes
            RETURN
                s.scenario_id as id,
                s.title as title,
                labels(s)[0] as type,
                properties(s) as props
            UNION
            MATCH (s:Scenario {scenario_id: $scenario_id})-[]-(n)
            RETURN
                coalesce(n.character_id, n.location_id, n.rule_id, n.trick_id, n.skill_id, n.item_id, n.event_id, toString(id(n))) as id,
                coalesce(n.name, n.title, labels(n)[0]) as title,
                labels(n)[0] as type,
                properties(n) as props
            """

            # 관계 조회
            edges_query = """
            MATCH (s:Scenario {scenario_id: $scenario_id})-[r]-(n)
            RETURN
                toString(id(r)) as rel_id,
                coalesce(s.scenario_id, toString(id(startNode(r)))) as from_id,
                coalesce(n.character_id, n.location_id, n.rule_id, n.trick_id, n.skill_id, n.item_id, n.event_id, toString(id(endNode(r)))) as to_id,
                type(r) as rel_type,
                properties(r) as props
            UNION
            MATCH (s:Scenario {scenario_id: $scenario_id})-[]-(n1)-[r]-(n2)
            WHERE n2 <> s
            RETURN
                toString(id(r)) as rel_id,
                coalesce(n1.character_id, n1.location_id, n1.rule_id, n1.trick_id, n1.skill_id, n1.item_id, n1.event_id, toString(id(startNode(r)))) as from_id,
                coalesce(n2.character_id, n2.location_id, n2.rule_id, n2.trick_id, n2.skill_id, n2.item_id, n2.event_id, toString(id(endNode(r)))) as to_id,
                type(r) as rel_type,
                properties(r) as props
            """

            node_results = await repo.execute_query(nodes_query, {"scenario_id": scenario_id})
            edge_results = await repo.execute_query(edges_query, {"scenario_id": scenario_id})

            if not node_results:
                raise HTTPException(status_code=404, detail="Scenario not found")

            # 노드 변환
            nodes = []
            for row in node_results:
                nodes.append(GraphNode(
                    id=row["id"],
                    label=row["title"],
                    type=row["type"],
                    properties=row["props"]
                ))

            # 엣지 변환
            edges = []
            for row in edge_results:
                edges.append(GraphEdge(
                    id=row["rel_id"],
                    from_id=row["from_id"],
                    to_id=row["to_id"],
                    type=row["rel_type"],
                    properties=row["props"]
                ))
        else:
            # 전체 그래프 (간단히 시나리오 노드만)
            nodes_query = """
            MATCH (s:Scenario)
            RETURN
                s.scenario_id as id,
                s.title as title,
                'Scenario' as type,
                properties(s) as props
            """

            node_results = await repo.execute_query(nodes_query)
            nodes = [GraphNode(
                id=row["id"],
                label=row["title"],
                type=row["type"],
                properties=row["props"]
            ) for row in node_results]
            edges = []

        return GraphData(nodes=nodes, edges=edges)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Repository는 싱글톤이므로 여기서 닫지 않음
        pass


@router.get("/scenarios/list")
async def list_scenarios():
    """
    시나리오 목록 조회

    Returns:
        시나리오 ID, 제목, 난이도 목록
    """
    repo = get_neo4j_repository()

    try:
        query = """
        MATCH (s:Scenario)
        RETURN s.scenario_id as id, s.title as title, s.difficulty as difficulty
        ORDER BY s.sequence_order
        """
        results = await repo.execute_query(query)
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _node_to_dict(node, node_type: str) -> GraphNode:
    """Neo4j 노드를 GraphNode로 변환"""
    # node가 dict인지 Neo4j Node 객체인지 확인
    if isinstance(node, dict):
        # dict인 경우 (execute_query의 result.data() 결과)
        node_id = None
        for key in ["scenario_id", "character_id", "location_id", "event_id",
                    "rule_id", "trick_id", "item_id", "skill_id"]:
            if key in node:
                node_id = node[key]
                break
        if not node_id:
            node_id = str(id(node))

        label = node.get("name") or node.get("title") or node_type
        properties = node
    else:
        # Neo4j Node 객체인 경우
        node_id = None
        if hasattr(node, "element_id"):
            node_id = node.element_id
        elif hasattr(node, "id"):
            node_id = str(node.id)
        else:
            for key in ["scenario_id", "character_id", "location_id", "event_id",
                        "rule_id", "trick_id", "item_id", "skill_id"]:
                if key in node:
                    node_id = node[key]
                    break

        if not node_id:
            node_id = str(id(node))

        label = node.get("name") or node.get("title") or node_type
        properties = dict(node)

    return GraphNode(
        id=node_id,
        label=label,
        type=node_type,
        properties=properties
    )


def _rel_to_dict(rel) -> GraphEdge:
    """Neo4j 관계를 GraphEdge로 변환"""
    # rel이 dict인지 Neo4j Relationship 객체인지 확인
    if isinstance(rel, dict):
        # dict인 경우
        rel_id = str(id(rel))
        from_id = rel.get("start_node_id", "unknown")
        to_id = rel.get("end_node_id", "unknown")
        rel_type = rel.get("type", "RELATED_TO")
        properties = {k: v for k, v in rel.items() if k not in ["start_node_id", "end_node_id", "type"]}
    else:
        # Neo4j Relationship 객체인 경우
        if hasattr(rel, "element_id"):
            rel_id = rel.element_id
        elif hasattr(rel, "id"):
            rel_id = str(rel.id)
        else:
            rel_id = str(id(rel))

        from_node = rel.nodes[0] if hasattr(rel, "nodes") else rel.start_node
        to_node = rel.nodes[1] if hasattr(rel, "nodes") else rel.end_node

        from_id = _extract_node_id(from_node)
        to_id = _extract_node_id(to_node)

        rel_type = rel.type if hasattr(rel, "type") else "RELATED_TO"
        properties = dict(rel) if hasattr(rel, "__iter__") else {}

    return GraphEdge(
        id=rel_id,
        from_id=from_id,
        to_id=to_id,
        type=rel_type,
        properties=properties
    )


def _extract_node_id(node):
    """노드에서 ID 추출"""
    if hasattr(node, "element_id"):
        return node.element_id
    elif hasattr(node, "id"):
        return str(node.id)
    else:
        for key in ["scenario_id", "character_id", "location_id", "event_id",
                    "rule_id", "trick_id", "item_id", "skill_id"]:
            if key in node:
                return node[key]
        return str(id(node))
