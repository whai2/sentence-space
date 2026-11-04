"""
런 세계관 RAG 워크플로우

질문 → 분류 → 검색 → 관계 보강 → 응답 생성
"""
from typing import Literal, TypedDict, Union

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from domain.run.agents.lore_retriever import LoreRetrieverAgent


class RunGraphState(TypedDict):
    """워크플로우 상태"""
    # 입력
    query: str
    query_type: str  # "lore_query", "character_query", "event_query"

    # 중간 결과
    retrieved_entities: list[dict]
    entity_types_filter: list[str]

    # 출력
    response: str
    response_data: dict | None

    # 에러
    error: str | None


class QueryClassification(BaseModel):
    """쿼리 분류 결과"""
    query_type: Literal["lore_query", "character_query", "event_query"] = Field(
        description="쿼리 유형"
    )
    intent: str = Field(description="쿼리 의도 요약")
    keywords: list[str] = Field(description="핵심 키워드")
    entity_types: list[str] = Field(
        default_factory=list,
        description="검색 대상 엔티티 타입 (concept, character, event, world_setting)"
    )


CLASSIFY_PROMPT = """당신은 소설 「런」의 세계관 질문 분류기입니다.

## 세계관 개요
미래 한국. 커넥톰(뇌 신경 연결 패턴) 디코딩 기술이 고도화된 세계.
기억의 읽기/쓰기/이식/삭제가 가능. 기억이 경제적 자산으로 거래됨.
오펀(문장 공간에서 태어난 존재), 염적(범죄 조직), 런(기술 원천 조직) 등이 존재.

## 엔티티 타입
- concept: 세계관 개념/기술/제도 (기억 오염, 커넥톰 지문, 인지적 고리 등 31개)
- character: 인물 (주인공, 테스, 카우트, 린, 세르게이 등 9명)
- event: 사건 (노틸러스 프로젝트, 38층 침투, 노르드 괴멸 등)
- world_setting: 세계관 설정 (기술, 조직, 장소, 경제 등)

## 분류 규칙
- **lore_query**: 개념, 기술, 규칙, 설정에 대한 질문 → entity_types: ["concept", "world_setting"]
- **character_query**: 인물에 대한 질문 → entity_types: ["character"]
- **event_query**: 사건, 시간순, 인과관계에 대한 질문 → entity_types: ["event", "character"]

## 질문
{query}
"""


RESPONSE_PROMPT = """당신은 소설 「런」의 세계관 전문가 어시스턴트입니다.
검색된 정보를 바탕으로 정확하고 일관된 답변을 제공합니다.

## 검색된 정보
{retrieved_info}

## 관계 정보
{relations_info}

## 사용자 질문
{query}

## 규칙
1. 검색된 정보에 기반하여 정확하게 답하세요
2. 정보가 없는 부분은 "설정되지 않음" 또는 "아직 확인되지 않음"으로 표시하세요
3. 관련 개념이나 인물 간의 연결고리를 함께 설명하세요
4. 간결하되 핵심 정보를 빠뜨리지 마세요
5. 답변은 한국어로 작성하세요
"""


class RunWorkflow:
    """
    런 세계관 RAG 워크플로우

    질문 분류 → 검색 → 관계 보강 → 응답 생성
    """

    def __init__(
        self,
        retriever: LoreRetrieverAgent,
        llm: Union[ChatOpenAI, ChatAnthropic],
    ):
        self.retriever = retriever
        self.llm = llm
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 상태 그래프 구성"""
        graph = StateGraph(RunGraphState)

        # 노드 등록
        graph.add_node("classify_query", self._classify_query)
        graph.add_node("search_lore", self._search_lore)
        graph.add_node("format_response", self._format_response)

        # 엣지 연결
        graph.set_entry_point("classify_query")
        graph.add_edge("classify_query", "search_lore")
        graph.add_edge("search_lore", "format_response")
        graph.add_edge("format_response", END)

        return graph.compile()

    async def run(self, query: str) -> dict:
        """워크플로우 실행"""
        initial_state: RunGraphState = {
            "query": query,
            "query_type": "",
            "retrieved_entities": [],
            "entity_types_filter": [],
            "response": "",
            "response_data": None,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state)
            return {
                "query": query,
                "query_type": result.get("query_type", ""),
                "response": result.get("response", ""),
                "data": result.get("response_data"),
            }
        except Exception as e:
            return {
                "query": query,
                "query_type": "error",
                "response": f"처리 중 오류가 발생했습니다: {str(e)}",
                "data": None,
            }

    async def _classify_query(self, state: RunGraphState) -> dict:
        """질문 분류"""
        try:
            structured_llm = self.llm.with_structured_output(QueryClassification)
            prompt = ChatPromptTemplate.from_messages([
                ("system", CLASSIFY_PROMPT),
            ])
            chain = prompt | structured_llm
            result: QueryClassification = await chain.ainvoke({"query": state["query"]})

            return {
                "query_type": result.query_type,
                "entity_types_filter": result.entity_types,
            }
        except Exception:
            # 분류 실패 시 전체 검색
            return {
                "query_type": "lore_query",
                "entity_types_filter": [],
            }

    async def _search_lore(self, state: RunGraphState) -> dict:
        """세계관 검색"""
        entity_types = state.get("entity_types_filter") or None

        results = await self.retriever.search(
            query=state["query"],
            n_results=8,
            entity_types=entity_types,
            include_relations=True,
        )

        return {"retrieved_entities": results}

    async def _format_response(self, state: RunGraphState) -> dict:
        """응답 생성"""
        entities = state.get("retrieved_entities", [])

        if not entities:
            return {
                "response": "관련 정보를 찾지 못했습니다.",
                "response_data": {"entities": []},
            }

        # 검색 결과 포맷팅
        retrieved_lines = []
        relations_lines = []

        for entity in entities:
            doc = entity.get("document", "")
            metadata = entity.get("metadata", {})
            title = metadata.get("title", entity.get("id", ""))
            entity_type = metadata.get("entity_type", "")
            score = entity.get("score", 0)

            retrieved_lines.append(f"[{entity_type}] {title} (관련도: {score:.2f})\n{doc}\n")

            relations = entity.get("relations", [])
            if relations:
                rel_strs = [
                    f"  - {r['title']} ({r['label']}) [{r['relation_type']}]"
                    for r in relations[:5]
                ]
                relations_lines.append(f"{title}의 관계:\n" + "\n".join(rel_strs))

        retrieved_info = "\n---\n".join(retrieved_lines)
        relations_info = "\n\n".join(relations_lines) if relations_lines else "관계 정보 없음"

        # LLM 응답 생성
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", RESPONSE_PROMPT),
            ])
            chain = prompt | self.llm
            result = await chain.ainvoke({
                "query": state["query"],
                "retrieved_info": retrieved_info,
                "relations_info": relations_info,
            })

            response_text = result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            response_text = f"응답 생성 실패. 검색 결과:\n{retrieved_info}"

        return {
            "response": response_text,
            "response_data": {
                "entities": [
                    {
                        "id": e.get("id"),
                        "title": e.get("metadata", {}).get("title", ""),
                        "entity_type": e.get("metadata", {}).get("entity_type", ""),
                        "score": e.get("score", 0),
                        "relations": [
                            {"title": r["title"], "type": r["relation_type"]}
                            for r in e.get("relations", [])[:5]
                        ],
                    }
                    for e in entities
                ],
            },
        }
