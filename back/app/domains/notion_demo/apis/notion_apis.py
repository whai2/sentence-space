"""Notion Demo API Endpoints"""

import json
from uuid import uuid4
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from dependency_injector.wiring import inject, Provide

from app.domains.notion_demo.models.schemas import (
    NotionChatRequest,
    NotionChatResponse,
    ToolExecutionDetail,
)
from app.domains.notion_demo.services.agent.agent import NotionAgent
from app.domains.notion_demo.container.container import NotionDemoContainer
from app.domains.notion_demo.handlers.chat_handler import ChatHandler

notion_router = APIRouter()


@notion_router.post("/chat", response_model=NotionChatResponse)
@inject
async def notion_chat(
    request: NotionChatRequest,
    agent: NotionAgent = Depends(Provide[NotionDemoContainer.notion_agent]),
) -> NotionChatResponse:
    """
    Notion 문서 관리 채팅 API

    ## 기능
    - Notion MCP 서버를 통한 문서 관리
    - Database Operations: 데이터베이스 조회, 생성, 쿼리
    - Page Operations: 페이지 생성, 수정, 조회
    - Block Operations: 블록 생성, 수정, 삭제
    - Search: 워크스페이스 내 검색
    - 자연어 대화형 인터페이스
    - LangGraph ReAct 패턴 기반 자동 도구 선택

    ## 사용 예시
    - "워크스페이스에서 '회의록'을 검색해줘"
    - "새 페이지를 만들어줘"
    - "데이터베이스의 항목들을 보여줘"
    """
    conversation_id = request.conversation_id or str(uuid4())

    result = await agent.chat(
        user_message=request.message,
        conversation_id=conversation_id,
    )

    tool_details = []
    for idx, tool_exec in enumerate(result["tool_history"], start=1):
        result_value = tool_exec.get("result", "")
        if isinstance(result_value, list):
            result_str = ""
            for item in result_value:
                if isinstance(item, dict) and "text" in item:
                    result_str += item["text"]
                elif isinstance(item, str):
                    result_str += item
            result_value = result_str

        tool_details.append(
            ToolExecutionDetail(
                tool_name=tool_exec["tool"],
                args=tool_exec["args"],
                success=tool_exec["success"],
                result_summary=(
                    str(result_value)[:200] if tool_exec["success"] else None
                ),
                error=tool_exec.get("error") if not tool_exec["success"] else None,
                iteration=idx,
            )
        )

    return NotionChatResponse(
        conversation_id=result["conversation_id"],
        user_message=request.message,
        assistant_message=result["assistant_message"],
        node_sequence=result["node_sequence"],
        execution_logs=result["execution_logs"],
        used_tools=result["used_tools"],
        tool_usage_count=result["tool_count"],
        tool_details=tool_details,
    )


@notion_router.post("/chat/stream")
@inject
async def notion_chat_stream(
    request: NotionChatRequest,
    agent: NotionAgent = Depends(Provide[NotionDemoContainer.notion_agent]),
):
    """
    Notion 문서 관리 채팅 API (스트리밍)

    ## 기능
    - 실시간으로 각 노드 실행 결과를 스트리밍
    - 각 스텝(노드)마다 즉시 결과 반환
    - Server-Sent Events (SSE) 형식으로 스트리밍

    ## 이벤트 타입
    - `node_start`: 노드 실행 시작
    - `node_end`: 노드 실행 완료
    - `tool_result`: 도구 실행 결과
    - `final`: 최종 결과
    """
    conversation_id = request.conversation_id or str(uuid4())

    async def generate():
        try:
            async for event in agent.stream_chat(
                user_message=request.message,
                conversation_id=conversation_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_event = {
                "event_type": "error",
                "node_name": None,
                "iteration": None,
                "data": {"error": str(e)},
                "timestamp": 0,
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@notion_router.get("/sessions")
async def get_all_sessions(
    limit: int = Query(100, ge=1, le=1000, description="조회할 최대 개수"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
):
    """
    모든 세션 목록 조회 (페이지네이션 지원)
    """
    from app.domains.notion_demo.repositories import SessionRepository
    from app.common.database.mongodb import get_database

    db = get_database()
    session_repo = SessionRepository(db)
    sessions = await session_repo.get_all_sessions(limit=limit, skip=skip)
    total = await session_repo.get_session_count()

    return {
        "sessions": [
            {
                "session_id": session.session_id,
                "metadata": session.metadata,
                "created_at": (
                    session.created_at.isoformat() if session.created_at else None
                ),
                "updated_at": (
                    session.updated_at.isoformat() if session.updated_at else None
                ),
            }
            for session in sessions
        ],
        "total": total,
    }


@notion_router.get("/sessions/{session_id}")
@inject
async def get_session(
    session_id: str,
    chat_handler: ChatHandler = Depends(Provide[NotionDemoContainer.chat_handler]),
):
    """
    세션 정보 조회
    """
    from app.domains.notion_demo.repositories import SessionRepository
    from app.common.database.mongodb import get_database

    db = get_database()
    session_repo = SessionRepository(db)
    session = await session_repo.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "metadata": session.metadata,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@notion_router.get("/sessions/{session_id}/chats")
@inject
async def get_session_chats(
    session_id: str,
    limit: int = Query(100, ge=1, le=1000, description="조회할 최대 개수"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    chat_handler: ChatHandler = Depends(Provide[NotionDemoContainer.chat_handler]),
):
    """
    세션의 채팅 이력 조회
    """
    chats = await chat_handler.get_session_chats(session_id, limit=limit, skip=skip)
    total = await chat_handler.get_session_chat_count(session_id)

    return {
        "chats": [
            {
                "id": str(chat.id),
                "session_id": chat.session_id,
                "user_message": chat.user_message,
                "assistant_message": chat.assistant_message,
                "node_sequence": chat.node_sequence,
                "execution_logs": chat.execution_logs,
                "used_tools": chat.used_tools,
                "tool_usage_count": chat.tool_usage_count,
                "tool_details": chat.tool_details,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
            }
            for chat in chats
        ],
        "total": total,
    }
