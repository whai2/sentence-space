"""Notion LangGraph Agent with ReAct Pattern using MCP Server"""

from typing import Dict, Any, List, AsyncGenerator, Optional
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.domains.notion_demo.models.state import NotionState
from app.domains.notion_demo.services.agent.mcp_client import NotionMCPClient
from app.domains.notion_demo.services.agent.graph import NotionGraphBuilder
from app.domains.notion_demo.services.agent.constants import NodeNames
from app.domains.notion_demo.services.agent.stream_events import (
    ToolResultEvent,
    FinalEvent,
    create_tool_details,
)
from app.domains.notion_demo.services.agent.langfuse_handler import LangFuseHandler


class NotionAgent:
    """Notion LangGraph Agent with ReAct Pattern

    Reasoning and Acting 패턴을 적용한 Notion 문서 관리 에이전트
    MCP 서버를 통해 Notion API와 통신
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        mcp_client: NotionMCPClient,
        memory_saver: MemorySaver,
        chat_handler=None,
        max_iterations: int = 10,
        langfuse_handler: Optional[LangFuseHandler] = None,
    ):
        """
        Args:
            llm: LangChain LLM 모델
            mcp_client: Notion MCP 클라이언트
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
        self.graph_builder: NotionGraphBuilder = None

    async def initialize(self):
        """에이전트 초기화: MCP 도구 로드 및 그래프 빌드"""
        raw_tools = await self.mcp_client.get_tools()
        self.tools = raw_tools

        self.graph_builder = NotionGraphBuilder(
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
        if not self.graph or not self.mcp_client._initialized:
            await self.initialize()

        if self.chat_handler:
            await self.chat_handler.ensure_session_exists(conversation_id)

        langfuse_callback = self.langfuse_handler.get_callback_handler(
            session_id=conversation_id,
            trace_name="NotionAgent.chat",
            metadata={"user_message": user_message},
        )

        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": self.max_iterations * 4 + 10,
            "callbacks": [langfuse_callback],
        }
        previous_state = await self.graph.aget_state(config)

        if previous_state and previous_state.values:
            messages = previous_state.values.get("messages", [])
            messages.append(HumanMessage(content=user_message))
        else:
            messages = [HumanMessage(content=user_message)]

        initial_state: NotionState = {
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

        final_state = await self.graph.ainvoke(initial_state, config)

        assistant_message_content = final_state["messages"][-1].content
        if isinstance(assistant_message_content, list):
            assistant_message = ""
            for item in assistant_message_content:
                if isinstance(item, dict) and "text" in item:
                    assistant_message += item["text"]
                elif isinstance(item, str):
                    assistant_message += item
        else:
            assistant_message = assistant_message_content

        tool_names = [tool["tool"] for tool in final_state["tool_history"]]
        unique_tools = list(set(tool_names))

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
                print(f"Failed to save chat to MongoDB: {e}")

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
        """스트리밍 채팅 인터페이스"""

        if not self.graph or not self.mcp_client._initialized:
            await self.initialize()

        if self.chat_handler:
            await self.chat_handler.ensure_session_exists(conversation_id)

        langfuse_callback = self.langfuse_handler.get_callback_handler(
            session_id=conversation_id,
            trace_name="NotionAgent.stream_chat",
            metadata={"user_message": user_message},
        )

        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": self.max_iterations * 4 + 10,
            "callbacks": [langfuse_callback],
        }
        previous_state = await self.graph.aget_state(config)

        if previous_state and previous_state.values:
            messages = previous_state.values.get("messages", [])
            messages.append(HumanMessage(content=user_message))
        else:
            messages = [HumanMessage(content=user_message)]

        initial_state: NotionState = {
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

        last_tool_history_len = 0
        current_node = None

        async for event in self.graph.astream_events(
            initial_state, config, version="v2"
        ):
            event_type = event.get("event")
            event_name = event.get("name", "")
            event_data = event.get("data", {})

            if event_type == "on_chat_model_stream":
                chunk = event_data.get("chunk")
                if chunk and hasattr(chunk, "content"):
                    content = ""
                    if isinstance(chunk.content, str):
                        content = chunk.content
                    elif isinstance(chunk.content, list):
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

            elif event_type == "on_chain_start":
                if event_name in [NodeNames.REASON, NodeNames.ACT, NodeNames.OBSERVE, NodeNames.FINALIZE]:
                    current_node = event_name
                    yield {
                        "event_type": "node_start",
                        "node_name": event_name,
                        "timestamp": event.get("metadata", {}).get("timestamp"),
                    }

            elif event_type == "on_chain_end":
                if event_name in [NodeNames.REASON, NodeNames.ACT, NodeNames.OBSERVE, NodeNames.FINALIZE]:
                    output = event_data.get("output", {})
                    current_iteration = output.get("current_iteration", 0)

                    yield {
                        "event_type": "node_end",
                        "node_name": event_name,
                        "iteration": current_iteration,
                    }

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

                    elif event_name == NodeNames.REASON and "is_final_answer" in output:
                        yield {
                            "event_type": "REASON_END",
                            "node_name": NodeNames.REASON,
                            "is_final": output["is_final_answer"],
                        }

        final_state_snapshot = await self.graph.aget_state(config)

        if final_state_snapshot and final_state_snapshot.values:
            values = final_state_snapshot.values
            assistant_message_content = values["messages"][-1].content
            if isinstance(assistant_message_content, list):
                assistant_message = ""
                for item in assistant_message_content:
                    if isinstance(item, dict) and "text" in item:
                        assistant_message += item["text"]
                    elif isinstance(item, str):
                        assistant_message += item
            else:
                assistant_message = assistant_message_content
            tool_details = create_tool_details(values.get("tool_history", []))

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
                    print(f"Failed to save chat to MongoDB: {e}")

            self.langfuse_handler.flush()
