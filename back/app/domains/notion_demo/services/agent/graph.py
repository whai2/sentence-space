"""Notion Agent Graph Builder"""

from typing import Any, List
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.domains.notion_demo.models.state import NotionState
from app.domains.notion_demo.services.agent.constants import NodeNames, EdgeDecision
from app.domains.notion_demo.services.agent.prompts import get_system_prompt
from app.domains.notion_demo.services.agent.result_summarizer import summarize_tool_result


class NotionGraphBuilder:
    """Notion Agent의 그래프 빌더 클래스

    노드와 엣지를 관리하고 ReAct 패턴을 구현합니다.
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        tools: List[Any],
        memory_saver: MemorySaver,
        max_iterations: int = 10,
        mcp_client=None,
    ):
        """
        Args:
            llm: LangChain LLM 모델
            tools: MCP 도구 리스트
            memory_saver: LangGraph 메모리 저장소
            max_iterations: 최대 반복 횟수
            mcp_client: MCP 클라이언트 (세션 유지용, 선택사항)
        """
        self.llm = llm
        self.tools = tools
        self.memory_saver = memory_saver
        self.max_iterations = max_iterations
        self.mcp_client = mcp_client

    def build(self) -> StateGraph:
        """ReAct 패턴을 적용한 LangGraph 그래프 생성"""
        workflow = StateGraph(NotionState)

        # 노드 정의
        workflow.add_node(NodeNames.REASON, self._reason_node)
        workflow.add_node(NodeNames.ACT, self._act_node)
        workflow.add_node(NodeNames.OBSERVE, self._observe_node)
        workflow.add_node(NodeNames.FINALIZE, self._finalize_node)

        # 시작점 설정
        workflow.set_entry_point(NodeNames.REASON)

        # 엣지 정의 (ReAct 사이클)
        workflow.add_conditional_edges(
            NodeNames.REASON,
            self._should_continue,
            {
                NodeNames.ACT: NodeNames.ACT,
                NodeNames.FINALIZE: NodeNames.FINALIZE,
            },
        )
        workflow.add_edge(NodeNames.ACT, NodeNames.OBSERVE)
        workflow.add_edge(NodeNames.OBSERVE, NodeNames.REASON)
        workflow.add_edge(NodeNames.FINALIZE, END)

        return workflow.compile(
            checkpointer=self.memory_saver,
            interrupt_before=None,
            interrupt_after=None,
            debug=False,
        )

    async def _reason_node(self, state: NotionState) -> NotionState:
        """추론 노드: 다음 행동을 결정 (스트리밍 지원)"""

        state["node_sequence"].append(NodeNames.REASON)
        state["current_iteration"] += 1

        system_message = SystemMessage(content=get_system_prompt())
        llm_with_tools = self.llm.bind_tools(self.tools)
        messages = [system_message] + state["messages"]

        final_response = None
        async for chunk in llm_with_tools.astream(messages):
            if final_response is None:
                final_response = chunk
            else:
                final_response += chunk

        if final_response:
            state["messages"].append(final_response)

            has_tool_calls = (
                bool(final_response.tool_calls)
                if hasattr(final_response, "tool_calls")
                else False
            )
            state["is_final_answer"] = not has_tool_calls

            state["execution_logs"].append(
                {
                    "node": NodeNames.REASON,
                    "iteration": state["current_iteration"],
                    "has_tool_calls": has_tool_calls,
                    "is_final": state["is_final_answer"],
                }
            )

        return state

    async def _act_node(self, state: NotionState) -> NotionState:
        """행동 노드: 도구 실행

        추론 단계에서 결정한 MCP 도구를 실행
        """
        state["node_sequence"].append(NodeNames.ACT)

        # MCP 세션 상태 확인 및 재초기화
        if self.mcp_client:
            try:
                await self.mcp_client.ensure_session()
            except Exception as e:
                error_msg = f"MCP 세션 초기화 실패: {str(e)}"
                state["execution_logs"].append(
                    {
                        "node": NodeNames.ACT,
                        "iteration": state["current_iteration"],
                        "error": error_msg,
                    }
                )
                last_message = state["messages"][-1]
                tool_calls = (
                    last_message.tool_calls if hasattr(last_message, "tool_calls") else []
                )
                for tool_call in tool_calls:
                    tool_call_id = tool_call.get("id", "") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
                    tool_name = tool_call.get("name", "") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                    state["tool_history"].append(
                        {
                            "tool": tool_name,
                            "args": {},
                            "error": error_msg,
                            "tool_call_id": tool_call_id,
                            "success": False,
                        }
                    )
                return state

        last_message = state["messages"][-1]
        tool_calls = (
            last_message.tool_calls if hasattr(last_message, "tool_calls") else []
        )

        # 도구 실행
        tool_results = []
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call.get("id", "")
            else:
                tool_name = getattr(tool_call, "name", "")
                tool_args = getattr(tool_call, "args", {})
                tool_call_id = getattr(tool_call, "id", "")

            if not tool_call_id:
                continue

            tool_found = False
            for tool_instance in self.tools:
                if tool_instance.name == tool_name:
                    tool_found = True
                    try:
                        result = await tool_instance.ainvoke(tool_args)

                        if result is None:
                            tool_results.append(
                                {
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "error": f"도구 '{tool_name}'가 None을 반환했습니다.",
                                    "tool_call_id": tool_call_id,
                                    "success": False,
                                }
                            )
                        else:
                            tool_results.append(
                                {
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "result": result,
                                    "tool_call_id": tool_call_id,
                                    "success": True,
                                }
                            )
                    except Exception as e:
                        if "ClosedResourceError" in str(type(e).__name__) or "ClosedResourceError" in str(e):
                            try:
                                if self.mcp_client:
                                    await self.mcp_client.close()
                                    await self.mcp_client.initialize()
                                    self.tools = await self.mcp_client.get_tools()
                                    for retry_tool in self.tools:
                                        if retry_tool.name == tool_name:
                                            result = await retry_tool.ainvoke(tool_args)
                                            if result is None:
                                                tool_results.append(
                                                    {
                                                        "tool": tool_name,
                                                        "args": tool_args,
                                                        "error": f"도구 '{tool_name}'가 None을 반환했습니다.",
                                                        "tool_call_id": tool_call_id,
                                                        "success": False,
                                                    }
                                                )
                                            else:
                                                tool_results.append(
                                                    {
                                                        "tool": tool_name,
                                                        "args": tool_args,
                                                        "result": result,
                                                        "tool_call_id": tool_call_id,
                                                        "success": True,
                                                    }
                                                )
                                            break
                                    else:
                                        raise Exception(f"재초기화 후 도구 '{tool_name}'를 찾을 수 없습니다.")
                            except Exception as retry_error:
                                error_msg = f"도구 실행 재시도 실패: {str(retry_error)}"
                                error_type = type(retry_error).__name__
                                tool_results.append(
                                    {
                                        "tool": tool_name,
                                        "args": tool_args,
                                        "error": f"[{error_type}] {error_msg}",
                                        "tool_call_id": tool_call_id,
                                        "success": False,
                                    }
                                )
                        else:
                            if "output schema" in str(e) or "structured content" in str(e):
                                error_msg = f"도구 '{tool_name}'가 빈 결과를 반환했거나 조회할 항목이 없습니다."
                            else:
                                error_msg = (
                                    str(e)
                                    if str(e)
                                    else f"도구 '{tool_name}' 실행 중 알 수 없는 오류가 발생했습니다."
                                )
                            error_type = type(e).__name__
                            tool_results.append(
                                {
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "error": f"[{error_type}] {error_msg}",
                                    "tool_call_id": tool_call_id,
                                    "success": False,
                                }
                            )
                    break

            if not tool_found:
                available_tools = [t.name for t in self.tools]
                tool_results.append(
                    {
                        "tool": tool_name,
                        "args": tool_args,
                        "error": f"도구 '{tool_name}'를 찾을 수 없습니다. 사용 가능한 도구: {', '.join(available_tools[:10])}",
                        "tool_call_id": tool_call_id,
                        "success": False,
                    }
                )

        state["tool_history"].extend(tool_results)
        state["execution_logs"].append(
            {
                "node": NodeNames.ACT,
                "iteration": state["current_iteration"],
                "tools_executed": len(tool_results),
            }
        )

        return state

    async def _observe_node(self, state: NotionState) -> NotionState:
        """관찰 노드: 도구 실행 결과를 메시지로 추가"""
        state["node_sequence"].append(NodeNames.OBSERVE)

        existing_tool_message_ids = set()
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage):
                existing_tool_message_ids.add(msg.tool_call_id)

        current_tool_call_ids = set()
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if isinstance(tool_call, dict):
                        tool_call_id = tool_call.get("id", "")
                    else:
                        tool_call_id = getattr(tool_call, "id", "")
                    if tool_call_id:
                        current_tool_call_ids.add(tool_call_id)
                break

        valid_tool_call_ids = current_tool_call_ids - existing_tool_message_ids

        processed_tools = state.get("processed_tools", [])
        recent_tools = [
            tool for tool in state["tool_history"] if tool not in processed_tools
        ]

        tool_results_by_id = {
            tool.get("tool_call_id", ""): tool for tool in recent_tools
        }

        for tool_call_id in valid_tool_call_ids:
            tool_result = tool_results_by_id.get(tool_call_id)

            if tool_result:
                if tool_result["success"]:
                    tool_name = tool_result.get("tool", "")
                    result = tool_result.get("result")
                    content = summarize_tool_result(tool_name, result)
                else:
                    error_msg = tool_result.get("error", "알 수 없는 오류가 발생했습니다.")
                    content = f"도구 실행 실패: {error_msg}\n\n도구: {tool_result.get('tool', 'unknown')}\n인자: {tool_result.get('args', {})}"

                processed_tools.append(tool_result)
            else:
                content = f"도구를 실행하지 못했습니다. tool_call_id: {tool_call_id}"

            tool_message = ToolMessage(
                content=content,
                tool_call_id=tool_call_id,
            )
            state["messages"].append(tool_message)

        state["processed_tools"] = processed_tools

        state["execution_logs"].append(
            {
                "node": NodeNames.OBSERVE,
                "iteration": state["current_iteration"],
                "observations": len(
                    [
                        t
                        for t in recent_tools
                        if t.get("tool_call_id", "") in valid_tool_call_ids
                    ]
                ),
            }
        )

        return state

    async def _finalize_node(self, state: NotionState) -> NotionState:
        """종료 노드: 최종 결과 정리"""
        state["node_sequence"].append(NodeNames.FINALIZE)

        state["execution_logs"].append(
            {
                "node": NodeNames.FINALIZE,
                "iteration": state["current_iteration"],
                "total_tools_used": len(state["tool_history"]),
            }
        )

        return state

    def _should_continue(self, state: NotionState) -> EdgeDecision:
        """다음 노드 결정

        Returns:
            "act": 도구를 실행해야 함
            "finalize": 최종 답변 준비
        """
        if state["current_iteration"] >= state["max_iterations"]:
            return NodeNames.FINALIZE

        if state["is_final_answer"]:
            return NodeNames.FINALIZE

        return NodeNames.ACT
