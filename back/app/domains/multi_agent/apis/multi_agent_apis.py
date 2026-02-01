"""Multi-Agent API Endpoints"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from app.domains.multi_agent.container import MultiAgentContainer
from app.domains.multi_agent.services.knowledge_graph import (
    PreFilterResult,
    GatekeeperVerdict,
)

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [MultiAgent] %(message)s")
    )
    logger.addHandler(handler)
from app.domains.multi_agent.services.agents.notion import (
    create_notion_agent,
)
from app.domains.multi_agent.services.agents.clickup import (
    create_clickup_reader_agent,
    create_clickup_writer_agent,
)
from app.domains.multi_agent.services.agents.supervisor import (
    create_supervisor_workflow,
)

router = APIRouter(prefix="/multi-agent", tags=["multi-agent"])

# Container 인스턴스
container = MultiAgentContainer()


class MultiAgentChatRequest(BaseModel):
    """멀티 에이전트 채팅 요청"""

    message: str
    conversation_id: Optional[str] = None


class MultiAgentChatResponse(BaseModel):
    """멀티 에이전트 채팅 응답"""

    conversation_id: str
    message: str
    agent_path: list[str]


def _get_langfuse_callback(conversation_id: str, trace_name: str, user_message: str):
    """LangFuse 콜백 핸들러 생성"""
    langfuse_handler = container.langfuse_handler()
    return langfuse_handler.get_callback_handler(
        session_id=conversation_id,
        trace_name=trace_name,
        metadata={"user_message": user_message},
    )


async def _get_or_create_supervisor():
    """Supervisor 워크플로우 생성 또는 반환"""
    start_time = time.time()
    logger.info("Supervisor 워크플로우 생성 시작")

    llm = container.llm()
    logger.debug(f"LLM 로드 완료: {llm.model_name}")

    # MCP 클라이언트 초기화 및 도구 로드
    # 매 요청마다 세션 상태 확인 및 재초기화
    notion_client = container.notion_mcp_client()
    clickup_client = container.clickup_mcp_client()

    # 세션이 닫혀있으면 재초기화
    logger.debug("Notion MCP 세션 확인 중...")
    try:
        await notion_client.ensure_session()
        logger.debug("Notion MCP 세션 확인 완료")
    except Exception as e:
        logger.warning(f"Notion MCP 세션 재초기화 필요: {e}")
        await notion_client.close()
        await notion_client.initialize()
        logger.debug("Notion MCP 세션 재초기화 완료")

    logger.debug("ClickUp MCP 세션 확인 중...")
    try:
        await clickup_client.ensure_session()
        logger.debug("ClickUp MCP 세션 확인 완료")
    except Exception as e:
        logger.warning(f"ClickUp MCP 세션 재초기화 필요: {e}")
        await clickup_client.close()
        await clickup_client.initialize()
        logger.debug("ClickUp MCP 세션 재초기화 완료")

    # 도구 새로 로드 (세션에 바인딩된 도구)
    logger.debug("MCP 도구 로드 중...")
    notion_tools = await notion_client.get_tools()
    clickup_tools = await clickup_client.get_tools()
    logger.debug(f"도구 로드 완료 - Notion: {len(notion_tools)}개, ClickUp: {len(clickup_tools)}개")

    # ClickUp 도구 이름 로깅 (디버깅용)
    clickup_tool_names = [tool.name for tool in clickup_tools]
    logger.info(f"ClickUp 전체 도구 목록: {clickup_tool_names}")

    # 에이전트 생성
    logger.debug("에이전트 생성 중...")
    notion_agent = create_notion_agent(llm, notion_tools)
    clickup_reader = create_clickup_reader_agent(llm, clickup_tools)
    clickup_writer = create_clickup_writer_agent(llm, clickup_tools)

    # Reader 에이전트에 연결된 도구 확인 (CompiledGraph의 경우)
    try:
        # create_react_agent가 반환하는 CompiledGraph에서 tools 확인
        if hasattr(clickup_reader, 'nodes'):
            for node_name, node in clickup_reader.nodes.items():
                if hasattr(node, 'tools_by_name'):
                    logger.info(f"clickup_reader '{node_name}' 도구: {list(node.tools_by_name.keys())}")
        # 직접 tools 속성 확인
        from app.domains.multi_agent.services.agents.clickup.reader_agent import filter_reader_tools, READER_TOOL_NAMES
        filtered = filter_reader_tools(clickup_tools)
        logger.info(f"READER_TOOL_NAMES: {READER_TOOL_NAMES}")
        logger.info(f"필터링된 reader 도구 ({len(filtered)}개): {[t.name for t in filtered]}")
    except Exception as e:
        logger.warning(f"도구 확인 중 에러: {e}")

    logger.debug("에이전트 생성 완료")

    # Supervisor 워크플로우 생성
    logger.debug("Supervisor 워크플로우 생성 중...")
    workflow = create_supervisor_workflow(
        llm=llm,
        agents=[notion_agent, clickup_reader, clickup_writer],
    )

    # 컴파일
    memory_saver = container.memory_saver()
    app = workflow.compile(checkpointer=memory_saver)

    elapsed = time.time() - start_time
    logger.info(f"Supervisor 워크플로우 생성 완료 ({elapsed:.2f}s)")

    return app


@router.post("/chat", response_model=MultiAgentChatResponse)
async def chat(request: MultiAgentChatRequest):
    """멀티 에이전트 채팅 (단일 응답)

    Args:
        request: 채팅 요청

    Returns:
        채팅 응답
    """
    try:
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Supervisor 앱 가져오기
        app = await _get_or_create_supervisor()

        # LangFuse 콜백 핸들러 생성
        langfuse_callback = _get_langfuse_callback(
            conversation_id=conversation_id,
            trace_name="MultiAgent.chat",
            user_message=request.message,
        )

        # --- Knowledge Graph 사전 처리 ---
        query_id = str(uuid.uuid4())
        kg_service = container.knowledge_graph_service()
        pre_filter = container.query_pre_filter()

        pre_filter_result = pre_filter.should_store(request.message)
        kg_enabled = False

        if pre_filter_result == PreFilterResult.PASS:
            try:
                gatekeeper = container.graph_gatekeeper()
                verdict = await gatekeeper.classify(request.message)

                if verdict != GatekeeperVerdict.SKIP:
                    kg_enabled = True
                    await kg_service.create_query_node(
                        query_id=query_id,
                        text=request.message,
                        conversation_id=conversation_id,
                        gatekeeper_verdict=verdict.value,
                    )
                    await kg_service.link_query_chain(
                        query_id=query_id,
                        conversation_id=conversation_id,
                    )

                    if verdict == GatekeeperVerdict.STORE:
                        extractor = container.topic_extractor()
                        result = await extractor.extract(request.message)
                        if result.intent:
                            await kg_service.update_query_intent(query_id, result.intent)
                        if result.topics:
                            await kg_service.link_topics(query_id, result.topics)
                        if result.keywords:
                            await kg_service.link_keywords(query_id, result.keywords)
            except Exception as e:
                logger.warning(f"KG pre-processing failed in /chat: {e}")

        # 메시지 구성
        messages = [HumanMessage(content=request.message)]

        # 실행
        config = {
            "configurable": {"thread_id": conversation_id},
            "callbacks": [langfuse_callback],
        }
        result = await app.ainvoke({"messages": messages}, config=config)

        # 응답 추출
        response_messages = result.get("messages", [])
        if response_messages:
            last_message = response_messages[-1]
            response_text = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )
        else:
            response_text = "응답을 생성할 수 없습니다."

        # 에이전트 경로 추출 (간소화)
        agent_path = ["supervisor"]

        # KG: Query 완료 처리
        if kg_enabled:
            asyncio.create_task(
                kg_service.complete_query(
                    query_id=query_id,
                    response_summary=response_text[:500] if response_text else "",
                )
            )

        # 채팅 저장
        chat_handler = container.chat_handler()
        await chat_handler.get_or_create_session(conversation_id)
        await chat_handler.save_chat(
            session_id=conversation_id,
            user_message=request.message,
            assistant_message=response_text,
            agent_path=agent_path,
        )

        # LangFuse 이벤트 플러시
        container.langfuse_handler().flush()

        return MultiAgentChatResponse(
            conversation_id=conversation_id,
            message=response_text,
            agent_path=agent_path,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: MultiAgentChatRequest):
    """멀티 에이전트 채팅 (스트리밍)

    Args:
        request: 채팅 요청

    Returns:
        SSE 스트리밍 응답 (ClickUp Demo와 동일한 형식)
    """

    async def event_generator():
        stream_start_time = time.time()
        logger.info(f"스트리밍 시작 - message: {request.message[:50]}...")

        try:
            conversation_id = request.conversation_id or str(uuid.uuid4())
            logger.debug(f"conversation_id: {conversation_id}")

            # Supervisor 앱 가져오기
            app = await _get_or_create_supervisor()

            # LangFuse 콜백 핸들러 생성
            langfuse_callback = _get_langfuse_callback(
                conversation_id=conversation_id,
                trace_name="MultiAgent.stream_chat",
                user_message=request.message,
            )

            # 메시지 구성
            messages = [HumanMessage(content=request.message)]

            # 스트리밍 실행
            config = {
                "configurable": {"thread_id": conversation_id},
                "callbacks": [langfuse_callback],
            }
            full_response = ""
            agent_path = []
            current_agent = None
            iteration = 0
            tool_results = []
            event_count = 0

            # --- Knowledge Graph 사전 처리 ---
            query_id = str(uuid.uuid4())
            kg_service = container.knowledge_graph_service()
            pre_filter = container.query_pre_filter()

            pre_filter_result = pre_filter.should_store(request.message)
            kg_enabled = False
            routing_order = 0

            if pre_filter_result == PreFilterResult.PASS:
                async def _kg_pre_process():
                    nonlocal kg_enabled
                    try:
                        gatekeeper = container.graph_gatekeeper()
                        verdict = await gatekeeper.classify(request.message)
                        logger.debug(f"KG Gatekeeper verdict: {verdict.value}")

                        if verdict == GatekeeperVerdict.SKIP:
                            return

                        kg_enabled = True

                        await kg_service.create_query_node(
                            query_id=query_id,
                            text=request.message,
                            conversation_id=conversation_id,
                            gatekeeper_verdict=verdict.value,
                        )
                        await kg_service.link_query_chain(
                            query_id=query_id,
                            conversation_id=conversation_id,
                        )

                        if verdict == GatekeeperVerdict.STORE:
                            extractor = container.topic_extractor()
                            result = await extractor.extract(request.message)

                            if result.intent:
                                await kg_service.update_query_intent(query_id, result.intent)
                            if result.topics:
                                await kg_service.link_topics(query_id, result.topics)
                            if result.keywords:
                                await kg_service.link_keywords(query_id, result.keywords)
                    except Exception as e:
                        logger.warning(f"KG pre-processing failed: {e}")

                kg_task = asyncio.create_task(_kg_pre_process())

                def _handle_kg_task_exception(task):
                    if task.exception():
                        logger.warning(f"KG background task failed: {task.exception()}")

                kg_task.add_done_callback(_handle_kg_task_exception)

            logger.info("astream_events 시작...")
            async for event in app.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                event_count += 1
                kind = event.get("event", "")
                event_name = event.get("name", "")

                # 모든 이벤트 상세 로깅 (디버깅용)
                if kind in ["on_chain_start", "on_chain_end", "on_tool_start", "on_tool_end"]:
                    logger.info(f"[Event #{event_count}] {kind}: {event_name}")
                    # 추가 데이터 로깅
                    event_data = event.get("data", {})
                    if event_data:
                        # output이 있으면 요약해서 로깅
                        if "output" in event_data:
                            output = event_data.get("output")
                            if isinstance(output, dict) and "messages" in output:
                                msgs = output.get("messages", [])
                                logger.info(f"  -> messages count: {len(msgs)}")
                                if msgs:
                                    last_msg = msgs[-1]
                                    if hasattr(last_msg, "content"):
                                        content_preview = str(last_msg.content)[:200]
                                        logger.info(f"  -> last message: {content_preview}...")
                        # input이 있으면 로깅
                        if "input" in event_data:
                            input_preview = str(event_data.get("input"))[:200]
                            logger.info(f"  -> input: {input_preview}...")

                # on_chat_model_end 이벤트도 로깅 (LLM 응답 완료)
                if kind == "on_chat_model_end":
                    logger.info(f"[Event #{event_count}] {kind}: {event_name} - LLM 응답 완료")

                # 1. 노드/에이전트 시작 이벤트
                if kind == "on_chain_start":
                    # 에이전트 노드 감지 (supervisor, notion_agent, clickup_reader, clickup_writer)
                    if event_name in ["supervisor", "notion_agent", "clickup_reader", "clickup_writer"]:
                        current_agent = event_name
                        if event_name not in agent_path:
                            agent_path.append(event_name)
                        iteration += 1
                        yield f"data: {json.dumps({'event_type': 'node_start', 'node_name': event_name, 'iteration': iteration, 'data': {'agent_path': agent_path}}, ensure_ascii=False)}\n\n"

                        # KG: 라우팅 기록
                        if kg_enabled:
                            routing_order += 1
                            _order = routing_order
                            _agent = event_name
                            asyncio.create_task(
                                kg_service.record_routing(
                                    query_id=query_id,
                                    agent_name=_agent,
                                    order=_order,
                                )
                            )

                # 2. LLM 스트리밍 토큰 이벤트
                elif kind == "on_chat_model_stream":
                    chunk_data = event.get("data", {}).get("chunk", {})
                    if hasattr(chunk_data, "content") and chunk_data.content:
                        chunk_text = chunk_data.content
                        # content가 리스트인 경우 처리 (Claude 모델)
                        if isinstance(chunk_text, list):
                            text_parts = []
                            for item in chunk_text:
                                if isinstance(item, dict) and "text" in item:
                                    text_parts.append(item["text"])
                                elif isinstance(item, str):
                                    text_parts.append(item)
                            chunk_text = "".join(text_parts)

                        if chunk_text:
                            full_response += chunk_text
                            yield f"data: {json.dumps({'event_type': 'message_chunk', 'node_name': current_agent or 'supervisor', 'data': {'text': chunk_text}}, ensure_ascii=False)}\n\n"

                # 3. 도구 호출 이벤트
                elif kind == "on_tool_start":
                    tool_name = event_name
                    tool_input = event.get("data", {}).get("input", {})
                    # tool_input이 직렬화 불가능한 객체를 포함할 수 있으므로 안전하게 직렬화
                    try:
                        # 먼저 JSON 직렬화 시도
                        tool_input_serializable = json.loads(json.dumps(tool_input, default=str))
                    except Exception:
                        tool_input_serializable = str(tool_input)
                    yield f"data: {json.dumps({'event_type': 'tool_start', 'node_name': current_agent or 'agent', 'iteration': iteration, 'data': {'tool_name': tool_name, 'args': tool_input_serializable}}, ensure_ascii=False)}\n\n"

                # 4. 도구 실행 결과 이벤트
                elif kind == "on_tool_end":
                    tool_name = event_name
                    tool_output = event.get("data", {}).get("output", "")
                    # 결과 요약 (너무 길면 자름)
                    result_summary = str(tool_output)[:500] if tool_output else ""
                    tool_results.append({
                        "tool_name": tool_name,
                        "success": True,
                        "result_summary": result_summary,
                    })
                    yield f"data: {json.dumps({'event_type': 'tool_result', 'node_name': current_agent or 'agent', 'iteration': iteration, 'data': {'tool_name': tool_name, 'success': True, 'result': result_summary}}, ensure_ascii=False)}\n\n"

                    # KG: Tool 실행 기록
                    if kg_enabled:
                        _exec_id = str(uuid.uuid4())
                        _tool_name = tool_name
                        _agent = current_agent or "unknown"
                        _input = str(event.get("data", {}).get("input", ""))[:200]
                        _output = result_summary[:200]
                        asyncio.create_task(
                            kg_service.record_tool_execution(
                                query_id=query_id,
                                execution_id=_exec_id,
                                tool_name=_tool_name,
                                agent_name=_agent,
                                input_summary=_input,
                                output_summary=_output,
                                success=True,
                            )
                        )

                # 5. 노드/에이전트 종료 이벤트
                elif kind == "on_chain_end":
                    if event_name in ["supervisor", "notion_agent", "clickup_reader", "clickup_writer"]:
                        yield f"data: {json.dumps({'event_type': 'node_end', 'node_name': event_name, 'iteration': iteration}, ensure_ascii=False)}\n\n"

            # 6. 최종 결과 이벤트 (ClickUp Demo의 final 이벤트와 동일)
            elapsed = time.time() - stream_start_time
            logger.info(f"astream_events 완료 - 총 {event_count}개 이벤트, {elapsed:.2f}s 소요")
            logger.info(f"agent_path: {agent_path}, tools: {len(tool_results)}개 사용")

            final_event = {
                "event_type": "final",
                "node_name": "supervisor",
                "iteration": iteration,
                "data": {
                    "conversation_id": conversation_id,
                    "assistant_message": full_response,
                    "node_sequence": agent_path,
                    "execution_logs": [{"agent": a, "iteration": i + 1} for i, a in enumerate(agent_path)],
                    "used_tools": [t["tool_name"] for t in tool_results],
                    "tool_usage_count": len(tool_results),
                    "tool_details": tool_results,
                },
                "timestamp": time.time(),
            }
            yield f"data: {json.dumps(final_event, ensure_ascii=False)}\n\n"

            # KG: Query 완료 처리
            if kg_enabled:
                _response_summary = full_response[:500] if full_response else ""
                asyncio.create_task(
                    kg_service.complete_query(
                        query_id=query_id,
                        response_summary=_response_summary,
                    )
                )

            # 채팅 저장
            logger.debug("채팅 저장 중...")
            chat_handler = container.chat_handler()
            await chat_handler.get_or_create_session(conversation_id)
            await chat_handler.save_chat(
                session_id=conversation_id,
                user_message=request.message,
                assistant_message=full_response,
                agent_path=agent_path,
            )
            logger.debug("채팅 저장 완료")

            # LangFuse 이벤트 플러시
            container.langfuse_handler().flush()
            logger.info(f"스트리밍 완료 - 총 {time.time() - stream_start_time:.2f}s")

        except Exception as e:
            error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"스트리밍 에러: {error_detail}")
            yield f"data: {json.dumps({'event_type': 'error', 'node_name': None, 'iteration': None, 'data': {'error': f'{type(e).__name__}: {str(e)}'}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/sessions")
async def get_all_sessions(limit: int = 100, skip: int = 0):
    """멀티 에이전트 세션 목록 조회

    Args:
        limit: 조회 개수 제한
        skip: 건너뛸 개수

    Returns:
        세션 목록 및 전체 개수
    """
    chat_handler = container.chat_handler()
    return await chat_handler.get_all_sessions(limit=limit, skip=skip)


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, limit: int = 50):
    """세션 채팅 이력 조회

    Args:
        session_id: 세션 ID
        limit: 조회 개수 제한

    Returns:
        채팅 이력 목록
    """
    chat_handler = container.chat_handler()
    history = await chat_handler.get_session_history(session_id, limit=limit)
    return {"session_id": session_id, "history": history}


@router.get("/sessions/{session_id}/chats")
async def get_session_chats(session_id: str, limit: int = 100, skip: int = 0):
    """세션 채팅 목록 조회 (ChatPage와 동일한 형식)

    Args:
        session_id: 세션 ID
        limit: 조회 개수 제한
        skip: 건너뛸 개수

    Returns:
        채팅 목록
    """
    chat_handler = container.chat_handler()
    history = await chat_handler.get_session_history(session_id, limit=limit)
    # ChatPage와 동일한 형식으로 변환
    chats = [
        {
            "id": f"{session_id}-{idx}",
            "session_id": session_id,
            "user_message": h["user_message"],
            "assistant_message": h["assistant_message"],
            "node_sequence": h.get("agent_path", []),
            "execution_logs": [],
            "used_tools": [],
            "tool_usage_count": 0,
            "tool_details": [],
            "created_at": h.get("created_at"),
        }
        for idx, h in enumerate(history)
    ]
    return {"chats": chats, "total": len(chats)}


# ── Knowledge Graph Read API ─────────────────────────────────────

def _serialize_neo4j_value(value: Any) -> Any:
    """Neo4j 값을 JSON 직렬화 가능한 형태로 변환"""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize_neo4j_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_neo4j_value(item) for item in value]
    return value


def _deep_serialize(obj: Any) -> Any:
    """중첩 구조를 재귀적으로 직렬화"""
    if isinstance(obj, dict):
        return {k: _deep_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_serialize(item) for item in obj]
    return _serialize_neo4j_value(obj)


@router.get("/knowledge-graph/graph")
async def get_knowledge_graph():
    """전체 지식 그래프 데이터 조회 (react-force-graph-2d 호환 포맷)"""
    try:
        kg_service = container.knowledge_graph_service()
        graph_data = await kg_service.get_full_graph()
        return _deep_serialize(graph_data)
    except Exception as e:
        logger.error(f"Failed to get knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-graph/nodes/{node_id:path}")
async def get_knowledge_graph_node(node_id: str):
    """노드 상세 정보 조회"""
    try:
        kg_service = container.knowledge_graph_service()
        node_data = await kg_service.get_node_detail(node_id)
        if node_data is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return _deep_serialize(node_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
