"""
멸살법 RAG 워크플로우

질문 → 분류 → 검색/생성 → 검증 → 응답
"""
from typing import Literal, TypedDict, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from domain.myeolsal.models import BeastEntry
from domain.myeolsal.agents import (
    BeastGeneratorAgent,
    BeastRetrieverAgent,
    BeastValidatorAgent,
    GenerationRequest,
)


class MyeolsalGraphState(TypedDict):
    """워크플로우 상태"""
    # 입력
    query: str
    query_type: str  # "search", "generate", "info"

    # 중간 결과
    retrieved_beasts: list[dict]
    generated_beast: BeastEntry | None
    validation_result: dict | None

    # 출력
    response: str
    response_data: dict | None

    # 에러 처리
    error: str | None
    retry_count: int


class QueryClassification(BaseModel):
    """쿼리 분류 결과"""
    query_type: Literal["search", "generate", "info"] = Field(
        description="쿼리 유형: search(검색), generate(생성), info(정보 조회)"
    )
    intent: str = Field(description="쿼리 의도 요약")
    keywords: list[str] = Field(description="핵심 키워드")
    filters: dict[str, str] = Field(
        default_factory=dict,
        description="필터 조건 (grade, species 등)"
    )


CLASSIFY_PROMPT = """당신은 멸살법 질문 분류기입니다.
사용자의 질문을 분석하여 유형을 분류하세요.

## 유형
- **search**: 기존 괴수 정보 검색 (예: "7급 괴수 알려줘", "어룡 어떻게 상대해?")
- **generate**: 새로운 괴수 생성 요청 (예: "화염 늑대 만들어줘", "5급 충왕종 생성")
- **info**: 일반 정보 조회 (예: "등급 체계가 뭐야?", "해수종 특징")

## 질문
{query}

JSON 형식으로 분류 결과를 출력하세요.
"""


RESPONSE_PROMPT = """당신은 'tls123', 멸살법의 저자입니다.
독자들의 생존을 위해 괴수 백과를 집필했습니다.

## 검색된 정보
{retrieved_info}

## 사용자 질문
{query}

## 규칙
1. tls123의 말투로 답하세요 (실용적, 냉소적이지만 도움이 되는)
2. 직접 경험하거나 조사한 것처럼 서술하세요
3. 생존에 직접적으로 도움이 되는 실용적 조언을 강조하세요
4. 위험한 상황에는 냉정하게 경고하세요 ("이건 피해라", "덤비면 죽는다")
5. 불확실한 정보는 "추정이다", "확인 안 됨" 등으로 표현하세요
"""


class MyeolsalWorkflow:
    """
    멸살법 RAG 워크플로우

    질문 분류 → 검색/생성 → 검증 → 응답 생성
    """

    def __init__(
        self,
        retriever: BeastRetrieverAgent,
        generator: BeastGeneratorAgent,
        validator: BeastValidatorAgent,
        llm: ChatAnthropic
    ):
        self.retriever = retriever
        self.generator = generator
        self.validator = validator
        self.llm = llm
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구축"""
        graph = StateGraph(MyeolsalGraphState)

        # 노드 추가
        graph.add_node("classify_query", self._classify_query)
        graph.add_node("search_beasts", self._search_beasts)
        graph.add_node("generate_beast", self._generate_beast)
        graph.add_node("validate_beast", self._validate_beast)
        graph.add_node("format_response", self._format_response)
        graph.add_node("handle_info", self._handle_info)

        # 시작점
        graph.set_entry_point("classify_query")

        # 조건부 엣지: 쿼리 유형에 따라 분기
        graph.add_conditional_edges(
            "classify_query",
            self._route_by_query_type,
            {
                "search": "search_beasts",
                "generate": "generate_beast",
                "info": "handle_info",
            }
        )

        # 검색 후 응답
        graph.add_edge("search_beasts", "format_response")

        # 생성 후 검증 후 응답
        graph.add_edge("generate_beast", "validate_beast")
        graph.add_conditional_edges(
            "validate_beast",
            self._should_retry,
            {
                "continue": "format_response",
                "retry": "generate_beast",
                "fail": "format_response",
            }
        )

        # 정보 조회 후 응답
        graph.add_edge("handle_info", "format_response")

        # 응답 후 종료
        graph.add_edge("format_response", END)

        return graph.compile()

    async def _classify_query(self, state: MyeolsalGraphState) -> dict:
        """쿼리 분류"""
        prompt = ChatPromptTemplate.from_template(CLASSIFY_PROMPT)
        structured_llm = self.llm.with_structured_output(QueryClassification)

        chain = prompt | structured_llm
        result: QueryClassification = await chain.ainvoke({"query": state["query"]})

        return {
            "query_type": result.query_type,
            "retrieved_beasts": [],
            "generated_beast": None,
            "validation_result": None,
            "error": None,
        }

    def _route_by_query_type(self, state: MyeolsalGraphState) -> str:
        """쿼리 유형에 따른 라우팅"""
        return state["query_type"]

    async def _search_beasts(self, state: MyeolsalGraphState) -> dict:
        """괴수 검색"""
        try:
            results = await self.retriever.search(
                query=state["query"],
                n_results=5,
                include_relations=True
            )
            return {"retrieved_beasts": results, "error": None}
        except Exception as e:
            return {"retrieved_beasts": [], "error": str(e)}

    async def _generate_beast(self, state: MyeolsalGraphState) -> dict:
        """괴수 생성"""
        try:
            # 유사 괴수 검색하여 참고
            similar = await self.retriever.search(state["query"], n_results=3)
            similar_beasts = []  # TODO: dict를 BeastEntry로 변환

            request = GenerationRequest(concept=state["query"])
            beast = await self.generator.generate(request, similar_beasts)

            return {
                "generated_beast": beast,
                "error": None,
            }
        except Exception as e:
            return {
                "generated_beast": None,
                "error": str(e),
            }

    async def _validate_beast(self, state: MyeolsalGraphState) -> dict:
        """생성된 괴수 검증"""
        beast = state.get("generated_beast")
        if not beast:
            return {
                "validation_result": {"is_valid": False, "errors": ["생성된 괴수 없음"]},
                "retry_count": state.get("retry_count", 0) + 1,
            }

        result = self.validator.validate(beast)

        return {
            "validation_result": result.model_dump(),
            "retry_count": state.get("retry_count", 0) if result.is_valid else state.get("retry_count", 0) + 1,
        }

    def _should_retry(self, state: MyeolsalGraphState) -> str:
        """재시도 여부 판단"""
        validation = state.get("validation_result", {})
        retry_count = state.get("retry_count", 0)

        if validation.get("is_valid", False):
            return "continue"
        elif retry_count >= 2:
            return "fail"
        else:
            return "retry"

    async def _handle_info(self, state: MyeolsalGraphState) -> dict:
        """일반 정보 조회"""
        # 등급 체계, 종별 특성 등 기본 정보 반환
        info_response = """멸살법 기본 정보입니다.

**등급 체계**: 9급(약함) → 특급(최강)
**종별 분류**: 괴수종, 악마종, 해수종, 충왕종, 거신, 재앙
**위험도**: 안전, 보통, 위험, 치명

자세한 정보는 특정 괴수나 등급을 질문해주세요."""

        return {
            "response": info_response,
            "error": None,
        }

    async def _format_response(self, state: MyeolsalGraphState) -> dict:
        """응답 포맷팅"""
        if state.get("error"):
            return {
                "response": f"죄송합니다. 오류가 발생했습니다: {state['error']}",
                "response_data": None,
            }

        # 이미 응답이 있으면 그대로 반환 (info 케이스)
        if state.get("response"):
            return {"response_data": None}

        # 검색 결과가 있으면 포맷팅
        if state.get("retrieved_beasts"):
            retrieved_info = self._format_retrieved_beasts(state["retrieved_beasts"])

            prompt = ChatPromptTemplate.from_template(RESPONSE_PROMPT)
            chain = prompt | self.llm

            result = await chain.ainvoke({
                "retrieved_info": retrieved_info,
                "query": state["query"]
            })

            return {
                "response": result.content,
                "response_data": {"beasts": state["retrieved_beasts"]},
            }

        # 생성된 괴수가 있으면 포맷팅
        if state.get("generated_beast"):
            beast = state["generated_beast"]
            validation = state.get("validation_result", {})

            response = f"""새로운 괴수를 생성했습니다.

**{beast.title}** ({beast.grade} {beast.species})
{beast.description}

**스탯**: HP={beast.stats.hp}, ATK={beast.stats.atk}, DEF={beast.stats.defense}
**약점**: {', '.join(beast.weaknesses)}
**생존 가이드**: {beast.survival_guide}
"""

            if not validation.get("is_valid"):
                response += f"\n⚠️ 검증 경고: {validation.get('warnings', [])}"

            return {
                "response": response,
                "response_data": {"beast": beast.model_dump()},
            }

        return {
            "response": "정보를 찾을 수 없습니다.",
            "response_data": None,
        }

    def _format_retrieved_beasts(self, beasts: list[dict]) -> str:
        """검색된 괴수 정보 포맷팅"""
        lines = []
        for b in beasts[:5]:
            meta = b.get("metadata", {})
            lines.append(f"""
### {meta.get('title', 'Unknown')} ({meta.get('grade', '?')} {meta.get('species', '?')})
{b.get('document', '')}
약점: {meta.get('weaknesses', [])}
""")
        return "\n".join(lines)

    async def run(self, query: str) -> dict:
        """
        워크플로우 실행

        Args:
            query: 사용자 질문

        Returns:
            응답 결과
        """
        initial_state: MyeolsalGraphState = {
            "query": query,
            "query_type": "",
            "retrieved_beasts": [],
            "generated_beast": None,
            "validation_result": None,
            "response": "",
            "response_data": None,
            "error": None,
            "retry_count": 0,
        }

        final_state = await self.graph.ainvoke(initial_state)

        return {
            "query": query,
            "response": final_state.get("response", ""),
            "data": final_state.get("response_data"),
            "query_type": final_state.get("query_type"),
        }
