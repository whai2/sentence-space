"""ClickUp Agent Graph Builder"""

import os
from typing import Any, List
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.domains.clickup_demo.models.state import ClickUpState
from app.domains.clickup_demo.services.agent.constants import NodeNames, EdgeDecision
from app.domains.clickup_demo.services.agent.prompts import get_system_prompt
from app.domains.clickup_demo.services.agent.result_summarizer import summarize_tool_result
from app.domains.clickup_demo.services.agent.tool_result_processor import extract_clickup_ids


class ClickUpGraphBuilder:
    """ClickUp Agent의 그래프 빌더 클래스

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
        workflow = StateGraph(ClickUpState)

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
            # max_iterations를 고려한 recursion_limit 설정
            # ReAct 패턴: REASON → ACT → OBSERVE → REASON (3 steps per iteration)
            # max_iterations * 3 + safety margin
            interrupt_before=None,
            interrupt_after=None,
            debug=False,
        )

    async def _reason_node(self, state: ClickUpState) -> ClickUpState:
        """추론 노드: 다음 행동을 결정 (스트리밍 지원)"""

        state["node_sequence"].append(NodeNames.REASON)
        state["current_iteration"] += 1

        team_id = os.environ.get("CLICKUP_TEAM_ID", "설정되지 않음")
        system_message = SystemMessage(content=get_system_prompt(team_id))
        llm_with_tools = self.llm.bind_tools(self.tools)
        messages = [system_message] + state["messages"]

        # 1. LLM의 비동기 스트리밍 호출 (핵심 변경 부분)
        # .astream() 대신 .ainvoke()를 사용하여 단일 최종 응답을 받고,
        # 스트리밍은 외부의 graph.astream()에서 처리하도록 하는 것이 LangGraph의 일반적인 접근 방식입니다.
        # 하지만 토큰 스트리밍을 위해 여기서는 .ainvoke()가 아닌 .astream()을 사용하여 최종 응답을 구성할 수 있습니다.

        final_response = None
        async for chunk in llm_with_tools.astream(messages):
            # LangGraph의 stream_mode='messages'가 이 청크를 자동으로 수집하여 외부로 스트리밍합니다.
            # 여기서는 최종 상태 업데이트를 위해 전체 응답을 재구성해야 합니다.
            if final_response is None:
                final_response = chunk
            else:
                final_response += chunk  # 청크를 누적하여 최종 응답 객체 완성

        # 2. 최종 응답으로 상태 업데이트
        if final_response:
            state["messages"].append(final_response)

            # 3. 도구 호출 여부 확인
            has_tool_calls = (
                bool(final_response.tool_calls)
                if hasattr(final_response, "tool_calls")
                else False
            )
            state["is_final_answer"] = not has_tool_calls

            # (생략된 로깅 코드는 그대로 유지)
            state["execution_logs"].append(
                {
                    "node": NodeNames.REASON,
                    "iteration": state["current_iteration"],
                    "has_tool_calls": has_tool_calls,
                    "is_final": state["is_final_answer"],
                }
            )

        return state

    async def _act_node(self, state: ClickUpState) -> ClickUpState:
        """행동 노드: 도구 실행

        추론 단계에서 결정한 MCP 도구를 실행
        """
        state["node_sequence"].append(NodeNames.ACT)

        # MCP 세션 상태 확인 및 재초기화
        if self.mcp_client:
            try:
                await self.mcp_client.ensure_session()
            except Exception as e:
                # 세션 재초기화 실패 시 에러 메시지 반환
                error_msg = f"MCP 세션 초기화 실패: {str(e)}"
                state["execution_logs"].append(
                    {
                        "node": NodeNames.ACT,
                        "iteration": state["current_iteration"],
                        "error": error_msg,
                    }
                )
                # 모든 도구 호출에 대해 에러 기록
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
            # tool_call이 딕셔너리 또는 객체일 수 있음
            if isinstance(tool_call, dict):
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call.get("id", "")
            else:
                # 객체인 경우
                tool_name = getattr(tool_call, "name", "")
                tool_args = getattr(tool_call, "args", {})
                tool_call_id = getattr(tool_call, "id", "")

            if not tool_call_id:
                # id가 없으면 건너뛰기
                continue

            # 도구 찾기 및 실행
            tool_found = False
            for tool_instance in self.tools:
                if tool_instance.name == tool_name:
                    tool_found = True
                    try:
                        result = await tool_instance.ainvoke(tool_args)

                        # 결과 후처리: lc_ prefix 제거 및 ID 추출
                        if result is not None:
                            result = extract_clickup_ids(result)

                        # 결과가 None이거나 빈 값인 경우 에러로 처리
                        if result is None:
                            tool_results.append(
                                {
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "error": f"도구 '{tool_name}'가 None을 반환했습니다. 도구 실행에 실패했을 수 있습니다.",
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
                        # ClosedResourceError가 발생하면 세션 재초기화 후 재시도
                        if "ClosedResourceError" in str(type(e).__name__) or "ClosedResourceError" in str(e):
                            try:
                                # 세션 재초기화
                                if self.mcp_client:
                                    await self.mcp_client.close()
                                    await self.mcp_client.initialize()
                                    # 도구 목록 업데이트
                                    self.tools = await self.mcp_client.get_tools()
                                    # 재시도
                                    for retry_tool in self.tools:
                                        if retry_tool.name == tool_name:
                                            result = await retry_tool.ainvoke(tool_args)

                                            # 결과 후처리: lc_ prefix 제거 및 ID 추출
                                            if result is not None:
                                                result = extract_clickup_ids(result)

                                            # 재시도 성공
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
                                # 재시도도 실패한 경우
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
                            # RuntimeError: output schema 에러 특별 처리
                            if "output schema" in str(e) or "structured content" in str(e):
                                error_msg = f"도구 '{tool_name}'가 빈 결과를 반환했거나 조회할 항목이 없습니다. 이 리소스(Space/Folder)에는 하위 항목이 없을 수 있습니다."
                            else:
                                # 다른 예외는 기존 로직으로 처리
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

            # 도구를 찾지 못한 경우
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

        # 도구 실행 기록
        state["tool_history"].extend(tool_results)
        state["execution_logs"].append(
            {
                "node": NodeNames.ACT,
                "iteration": state["current_iteration"],
                "tools_executed": len(tool_results),
            }
        )

        return state

    async def _observe_node(self, state: ClickUpState) -> ClickUpState:
        """관찰 노드: 도구 실행 결과를 메시지로 추가

        도구 실행 결과를 LLM이 이해할 수 있는 형식으로 변환
        OpenAI API 요구사항에 따라 ToolMessage를 사용
        """
        state["node_sequence"].append(NodeNames.OBSERVE)

        # 이미 ToolMessage가 생성된 tool_call_id 목록
        existing_tool_message_ids = set()
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage):
                existing_tool_message_ids.add(msg.tool_call_id)

        # 가장 최근 AIMessage에서 tool_calls 찾기
        # (현재 실행 사이클에서 생성된 tool_calls)
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

        # 아직 ToolMessage가 생성되지 않은 tool_call_id만 처리
        valid_tool_call_ids = current_tool_call_ids - existing_tool_message_ids

        # 최근 도구 실행 결과 가져오기
        processed_tools = state.get("processed_tools", [])
        recent_tools = [
            tool for tool in state["tool_history"] if tool not in processed_tools
        ]

        # tool_call_id를 키로 하는 딕셔너리 생성 (빠른 조회)
        tool_results_by_id = {
            tool.get("tool_call_id", ""): tool for tool in recent_tools
        }

        # valid_tool_call_ids에 있는 모든 ID에 대해 반드시 ToolMessage 생성
        for tool_call_id in valid_tool_call_ids:
            tool_result = tool_results_by_id.get(tool_call_id)

            if tool_result:
                # 도구 실행 결과가 있는 경우
                if tool_result["success"]:
                    # 성공한 경우: 도구 결과를 요약하여 전달
                    tool_name = tool_result.get("tool", "")
                    result = tool_result.get("result")
                    content = summarize_tool_result(tool_name, result)
                else:
                    # 실패한 경우: 에러 메시지
                    error_msg = tool_result.get("error", "알 수 없는 오류가 발생했습니다.")
                    content = f"도구 실행 실패: {error_msg}\n\n도구: {tool_result.get('tool', 'unknown')}\n인자: {tool_result.get('args', {})}"

                # 처리된 도구로 표시
                processed_tools.append(tool_result)
            else:
                # 도구 실행 결과가 없는 경우 (ACT 노드에서 실행 실패)
                content = f"도구를 실행하지 못했습니다. tool_call_id: {tool_call_id}"

            # ToolMessage 생성 (tool_call_id 필수)
            tool_message = ToolMessage(
                content=content,
                tool_call_id=tool_call_id,
            )
            state["messages"].append(tool_message)

        # 처리된 도구 목록 업데이트
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

    async def _finalize_node(self, state: ClickUpState) -> ClickUpState:
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

    def _should_continue(self, state: ClickUpState) -> EdgeDecision:
        """다음 노드 결정

        Returns:
            "act": 도구를 실행해야 함
            "finalize": 최종 답변 준비
        """
        # 최대 반복 횟수 초과
        if state["current_iteration"] >= state["max_iterations"]:
            return NodeNames.FINALIZE

        # 최종 답변인 경우
        if state["is_final_answer"]:
            return NodeNames.FINALIZE

        # 도구 실행이 필요한 경우
        return NodeNames.ACT
