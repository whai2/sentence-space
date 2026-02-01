"""ClickUp LangGraph Agent with ReAct Pattern using MCP Server"""

from typing import Dict, Any, List, AsyncGenerator, Optional
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.domains.clickup_demo.models.state import ClickUpState
from app.domains.clickup_demo.services.agent.mcp_client import ClickUpMCPClient
from app.domains.clickup_demo.services.agent.graph import ClickUpGraphBuilder
from app.domains.clickup_demo.services.agent.constants import NodeNames
from app.domains.clickup_demo.services.agent.stream_events import (
    NodeStartEvent,
    NodeEndEvent,
    ToolResultEvent,
    FinalEvent,
    create_tool_details,
)
from app.domains.clickup_demo.services.agent.langfuse_handler import LangFuseHandler
from app.domains.clickup_demo.services.agent.tool_wrapper import CompactToolWrapper


class ClickUpAgent:
    """ClickUp LangGraph Agent with ReAct Pattern

    Reasoning and Acting 패턴을 적용한 ClickUp 작업 관리 에이전트
    MCP 서버를 통해 ClickUp API와 통신
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        mcp_client: ClickUpMCPClient,
        memory_saver: MemorySaver,
        chat_handler=None,
        max_iterations: int = 10,
        langfuse_handler: Optional[LangFuseHandler] = None,
    ):
        """
        Args:
            llm: LangChain LLM 모델
            mcp_client: ClickUp MCP 클라이언트
            memory_saver: LangGraph 메모리 저장소
            chat_handler: 채팅 핸들러 (선택)
            max_iterations: 최대 반복 횟수
            langfuse_handler: LangFuse 핸들러 (선택, 추적 및 관찰성)
        """
        self.llm = llm
        self.mcp_client = mcp_client
        self.memory_saver = memory_saver
        self.chat_handler = chat_handler
        self.max_iterations = max_iterations
        self.langfuse_handler = langfuse_handler or LangFuseHandler()
        self.tools: List[Any] = []
        self.graph: StateGraph = None
        self.graph_builder: ClickUpGraphBuilder = None

    async def initialize(self):
        """에이전트 초기화: MCP 도구 로드 및 그래프 빌드"""
        # MCP 서버에서 도구 로드
        raw_tools = await self.mcp_client.get_tools()

        # 도구 응답 필터링 래퍼 적용 (토큰 사용량 대폭 절감)
        # TODO: tool wrapper 수정 필요 - 현재는 비활성화
        # self.tools = CompactToolWrapper.wrap_tools(raw_tools)
        self.tools = raw_tools

        # 그래프 빌더 생성 및 그래프 빌드
        self.graph_builder = ClickUpGraphBuilder(
            llm=self.llm,
            tools=self.tools,
            memory_saver=self.memory_saver,
            max_iterations=self.max_iterations,
            mcp_client=self.mcp_client,
        )
        self.graph = self.graph_builder.build()

    async def chat(self, user_message: str, conversation_id: str) -> Dict[str, Any]:
        """채팅 인터페이스

        Args:
            user_message: 사용자 메시지
            conversation_id: 대화 ID

        Returns:
            응답 딕셔너리
        """
        # 초기화 확인 및 MCP 세션 상태 확인
        if not self.graph or not self.mcp_client._initialized:
            await self.initialize()

        # MongoDB 세션 생성/확인 (핸들러가 주입된 경우)
        if self.chat_handler:
            await self.chat_handler.ensure_session_exists(conversation_id)

        # LangFuse 콜백 핸들러 생성
        langfuse_callback = self.langfuse_handler.get_callback_handler(
            session_id=conversation_id,
            trace_name="ClickUpAgent.chat",
            metadata={"user_message": user_message},
        )

        # 이전 대화 상태 로드
        # recursion_limit: ReAct 패턴에서 max_iterations * 4 (REASON+ACT+OBSERVE+FINALIZE) + 여유분
        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": self.max_iterations * 4 + 10,
            "callbacks": [langfuse_callback],
        }
        previous_state = await self.graph.aget_state(config)

        # 이전 메시지에 새 메시지 추가
        if previous_state and previous_state.values:
            messages = previous_state.values.get("messages", [])
            messages.append(HumanMessage(content=user_message))
        else:
            messages = [HumanMessage(content=user_message)]

        # 초기 상태 설정 (이전 메시지 포함)
        initial_state: ClickUpState = {
            "messages": messages,
            "node_sequence": [],
            "execution_logs": [],
            "max_iterations": self.max_iterations,
            "current_iteration": 0,
            "tool_history": [],
            "current_decision": {},
            "is_final_answer": False,
            "processed_tools": [],
        }

        # 그래프 실행
        final_state = await self.graph.ainvoke(initial_state, config)

        # 최종 응답 추출
        assistant_message_content = final_state["messages"][-1].content
        if isinstance(assistant_message_content, list):
            # content가 리스트인 경우 (Claude 모델 등)
            assistant_message = ""
            for item in assistant_message_content:
                if isinstance(item, dict) and "text" in item:
                    assistant_message += item["text"]
                elif isinstance(item, str):
                    assistant_message += item
        else:
            assistant_message = assistant_message_content

        # 도구 사용 통계
        tool_names = [tool["tool"] for tool in final_state["tool_history"]]
        unique_tools = list(set(tool_names))

        # MongoDB에 채팅 저장 (핸들러가 주입된 경우)
        if self.chat_handler:
            try:
                await self.chat_handler.save_chat(
                    session_id=conversation_id,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    node_sequence=final_state["node_sequence"],
                    execution_logs=final_state["execution_logs"],
                    tool_history=final_state["tool_history"],
                )
            except Exception as e:
                # MongoDB 저장 실패는 로그만 남기고 응답은 정상 반환
                print(f"Failed to save chat to MongoDB: {e}")

        # LangFuse 이벤트 플러시
        self.langfuse_handler.flush()

        return {
            "conversation_id": conversation_id,
            "assistant_message": assistant_message,
            "node_sequence": final_state["node_sequence"],
            "execution_logs": final_state["execution_logs"],
            "tool_history": final_state["tool_history"],
            "used_tools": unique_tools,
            "tool_count": len(tool_names),
        }

    async def stream_chat(
        self, user_message: str, conversation_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """스트리밍 채팅 인터페이스 (수정된 버전)"""

        if not self.graph or not self.mcp_client._initialized:
            await self.initialize()

        # MongoDB 세션 생성/확인 (핸들러가 주입된 경우)
        if self.chat_handler:
            await self.chat_handler.ensure_session_exists(conversation_id)

        # LangFuse 콜백 핸들러 생성
        langfuse_callback = self.langfuse_handler.get_callback_handler(
            session_id=conversation_id,
            trace_name="ClickUpAgent.stream_chat",
            metadata={"user_message": user_message},
        )

        # 이전 대화 상태 로드
        # recursion_limit: ReAct 패턴에서 max_iterations * 4 (REASON+ACT+OBSERVE+FINALIZE) + 여유분
        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": self.max_iterations * 4 + 10,
            "callbacks": [langfuse_callback],
        }
        previous_state = await self.graph.aget_state(config)

        # 이전 메시지에 새 메시지 추가
        if previous_state and previous_state.values:
            messages = previous_state.values.get("messages", [])
            messages.append(HumanMessage(content=user_message))
        else:
            messages = [HumanMessage(content=user_message)]

        # 초기 상태 설정 (이전 메시지 포함)
        initial_state: ClickUpState = {
            "messages": messages,
            "node_sequence": [],
            "execution_logs": [],
            "max_iterations": self.max_iterations,
            "current_iteration": 0,
            "tool_history": [],
            "current_decision": {},
            "is_final_answer": False,
            "processed_tools": [],
        }

        # astream_events를 사용하여 모든 이벤트 캡처 (LLM 토큰 포함)
        # version="v2"를 사용하면 더 세밀한 이벤트 제어 가능
        last_tool_history_len = 0
        current_node = None

        async for event in self.graph.astream_events(
            initial_state, config, version="v2"
        ):
            event_type = event.get("event")
            event_name = event.get("name", "")
            event_data = event.get("data", {})

            # 1. LLM 스트리밍 토큰 이벤트 (on_chat_model_stream)
            if event_type == "on_chat_model_stream":
                chunk = event_data.get("chunk")
                if chunk and hasattr(chunk, "content"):
                    # Claude와 OpenAI 모두 호환되도록 content 추출
                    content = ""
                    if isinstance(chunk.content, str):
                        content = chunk.content
                    elif isinstance(chunk.content, list):
                        # Claude 모델의 경우 content가 리스트일 수 있음
                        for item in chunk.content:
                            if isinstance(item, dict) and "text" in item:
                                content += item["text"]
                            elif isinstance(item, str):
                                content += item

                    if content:
                        yield {
                            "event_type": "message_chunk",
                            "node_name": current_node or "reason",
                            "data": {"text": content},
                            "timestamp": event.get("metadata", {}).get("timestamp", 0),
                        }

            # 2. 노드 시작 이벤트 (on_chain_start)
            elif event_type == "on_chain_start":
                # 그래프 노드 시작 감지
                if event_name in [NodeNames.REASON, NodeNames.ACT, NodeNames.OBSERVE, NodeNames.FINALIZE]:
                    current_node = event_name
                    yield {
                        "event_type": "node_start",
                        "node_name": event_name,
                        "timestamp": event.get("metadata", {}).get("timestamp"),
                    }

            # 3. 노드 종료 이벤트 (on_chain_end)
            elif event_type == "on_chain_end":
                if event_name in [NodeNames.REASON, NodeNames.ACT, NodeNames.OBSERVE, NodeNames.FINALIZE]:
                    output = event_data.get("output", {})
                    current_iteration = output.get("current_iteration", 0)

                    yield {
                        "event_type": "node_end",
                        "node_name": event_name,
                        "iteration": current_iteration,
                    }

                    # ACT 노드 종료 시 도구 실행 결과 이벤트
                    if event_name == NodeNames.ACT and "tool_history" in output:
                        new_tool_history = output["tool_history"]
                        recent_tools = new_tool_history[last_tool_history_len:]
                        last_tool_history_len = len(new_tool_history)

                        for tool_result in recent_tools:
                            event_obj = ToolResultEvent.create(
                                node_name=event_name,
                                iteration=current_iteration,
                                tool_name=tool_result.get("tool", ""),
                                args=tool_result.get("args", {}),
                                success=tool_result.get("success", False),
                                result=tool_result.get("result") if tool_result.get("success") else None,
                                error=tool_result.get("error") if not tool_result.get("success") else None,
                            )
                            yield event_obj.to_dict()

                    # REASON 노드 종료 시 최종 답변 여부 이벤트
                    elif event_name == NodeNames.REASON and "is_final_answer" in output:
                        yield {
                            "event_type": "REASON_END",
                            "node_name": NodeNames.REASON,
                            "is_final": output["is_final_answer"],
                        }

        # 4. 스트림 종료 후 최종 요약 정보 (FINALIZE 이벤트)
        # Checkpointer를 사용하여 최종 상태를 로드 (기존 구현과 동일)
        final_state_snapshot = await self.graph.aget_state(config)

        if final_state_snapshot and final_state_snapshot.values:
            # FinalEvent.create 로직 (기존 구현과 동일)
            values = final_state_snapshot.values
            assistant_message_content = values["messages"][-1].content
            if isinstance(assistant_message_content, list):
                # content가 리스트인 경우 (Claude 모델 등)
                assistant_message = ""
                for item in assistant_message_content:
                    if isinstance(item, dict) and "text" in item:
                        assistant_message += item["text"]
                    elif isinstance(item, str):
                        assistant_message += item
            else:
                assistant_message = assistant_message_content
            tool_details = create_tool_details(values.get("tool_history", []))

            # 도구 사용 통계
            tool_names = [tool["tool"] for tool in values.get("tool_history", [])]
            unique_tools = list(set(tool_names))

            event = FinalEvent.create(
                node_name=NodeNames.FINALIZE,
                iteration=values.get("current_iteration", 0),
                conversation_id=conversation_id,
                assistant_message=assistant_message,
                node_sequence=values.get("node_sequence", []),
                execution_logs=values.get("execution_logs", []),
                tool_details=tool_details,
                used_tools=unique_tools,
                tool_usage_count=len(tool_names),
            )
            yield event.to_dict()

            # MongoDB에 채팅 저장 (핸들러가 주입된 경우)
            if self.chat_handler:
                try:
                    await self.chat_handler.save_chat_from_stream_event(
                        session_id=conversation_id,
                        user_message=user_message,
                        assistant_message=assistant_message,
                        node_sequence=values.get("node_sequence", []),
                        execution_logs=values.get("execution_logs", []),
                        tool_details=tool_details,
                    )
                except Exception as e:
                    # MongoDB 저장 실패는 로그만 남기고 스트림에는 영향 없음
                    print(f"Failed to save chat to MongoDB: {e}")

            # LangFuse 이벤트 플러시
            self.langfuse_handler.flush()
