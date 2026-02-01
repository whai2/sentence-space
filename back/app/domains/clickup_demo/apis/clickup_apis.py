"""ClickUp Demo API Endpoints"""

import json
from uuid import uuid4
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from dependency_injector.wiring import inject, Provide

from app.domains.clickup_demo.models.schemas import (
    ClickUpChatRequest,
    ClickUpChatResponse,
    ToolExecutionDetail,
)
from app.domains.clickup_demo.services.agent.agent import ClickUpAgent
from app.domains.clickup_demo.container.container import ClickUpDemoContainer
from app.domains.clickup_demo.handlers.chat_handler import ChatHandler

clickup_router = APIRouter()


@clickup_router.post("/chat", response_model=ClickUpChatResponse)
@inject
async def clickup_chat(
    request: ClickUpChatRequest,
    agent: ClickUpAgent = Depends(Provide[ClickUpDemoContainer.clickup_agent]),
) -> ClickUpChatResponse:
    """
    ClickUp 작업 관리 채팅 API

    ## 기능
    - ClickUp MCP 서버를 통한 작업 관리
    - Task Management: 작업 생성, 수정, 조회
    - Team & List Operations: 팀 및 리스트 조회
    - Space Management: 스페이스 CRUD
    - Folder & Board Management: 폴더 및 보드 관리
    - Custom Fields: 커스텀 필드 관리
    - Documentation: Docs 검색, 생성, 편집
    - Views: 다양한 뷰 생성 및 관리
    - 자연어 대화형 인터페이스
    - LangGraph ReAct 패턴 기반 자동 도구 선택

    ## 사용 예시
    - "스페이스 목록을 보여줘"
    - "첫 번째 스페이스의 리스트를 조회해줘"
    - "진행 중인 작업들을 보여줘"
    - "'회의 준비'라는 작업을 만들어줘"
    """
    conversation_id = request.conversation_id or str(uuid4())

    # 에이전트 채팅 실행 (MongoDB 저장 로직은 agent 내부에서 처리)
    result = await agent.chat(
        user_message=request.message,
        conversation_id=conversation_id,
    )

    # 도구 실행 상세 정보 생성
    tool_details = []
    for idx, tool_exec in enumerate(result["tool_history"], start=1):
        # result를 문자열로 변환 (Claude 모델은 리스트 형태로 반환할 수 있음)
        result_value = tool_exec.get("result", "")
        if isinstance(result_value, list):
            # Claude 응답 포맷 처리
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

    return ClickUpChatResponse(
        conversation_id=result["conversation_id"],
        user_message=request.message,
        assistant_message=result["assistant_message"],
        node_sequence=result["node_sequence"],
        execution_logs=result["execution_logs"],
        used_tools=result["used_tools"],
        tool_usage_count=result["tool_count"],
        tool_details=tool_details,
    )


@clickup_router.post("/chat/stream")
@inject
async def clickup_chat_stream(
    request: ClickUpChatRequest,
    agent: ClickUpAgent = Depends(Provide[ClickUpDemoContainer.clickup_agent]),
):
    """
    ClickUp 작업 관리 채팅 API (스트리밍)

    ## 기능
    - 실시간으로 각 노드 실행 결과를 스트리밍
    - 각 스텝(노드)마다 즉시 결과 반환
    - Server-Sent Events (SSE) 형식으로 스트리밍

    ## 이벤트 타입
    - `node_start`: 노드 실행 시작
    - `node_end`: 노드 실행 완료
    - `tool_result`: 도구 실행 결과
    - `final`: 최종 결과

    ## 사용 예시
    ```javascript
    const eventSource = new EventSource('/clickup/chat/stream', {
      method: 'POST',
      body: JSON.stringify({ message: '스페이스 목록을 보여줘' })
    });

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Event:', data.event_type, data);
    };
    ```
    """
    conversation_id = request.conversation_id or str(uuid4())

    async def generate():
        """스트리밍 이벤트 생성 (MongoDB 저장 로직은 agent 내부에서 처리)"""
        try:
            async for event in agent.stream_chat(
                user_message=request.message,
                conversation_id=conversation_id,
            ):
                # SSE 형식으로 전송
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            # 에러 발생 시 에러 이벤트 전송
            error_event = {
                "event_type": "error",
                "node_name": None,
                "iteration": None,
                "data": {"error": str(e)},
                "timestamp": 0,
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        finally:
            # 스트림 종료
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 버퍼링 비활성화
        },
    )


@clickup_router.get("/sessions")
async def get_all_sessions(
    limit: int = Query(100, ge=1, le=1000, description="조회할 최대 개수"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
):
    """
    모든 세션 목록 조회 (페이지네이션 지원)

    Args:
        limit: 조회할 최대 개수 (기본값: 100)
        skip: 건너뛸 개수 (기본값: 0)

    Returns:
        세션 목록 및 총 개수
    """
    from app.domains.clickup_demo.repositories import SessionRepository
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


@clickup_router.get("/sessions/{session_id}")
@inject
async def get_session(
    session_id: str,
    chat_handler: ChatHandler = Depends(Provide[ClickUpDemoContainer.chat_handler]),
):
    """
    세션 정보 조회

    Args:
        session_id: 세션 ID

    Returns:
        세션 정보 (존재하지 않으면 404)
    """
    from app.domains.clickup_demo.repositories import SessionRepository
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


@clickup_router.get("/sessions/{session_id}/chats")
@inject
async def get_session_chats(
    session_id: str,
    limit: int = Query(100, ge=1, le=1000, description="조회할 최대 개수"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    chat_handler: ChatHandler = Depends(Provide[ClickUpDemoContainer.chat_handler]),
):
    """
    세션의 채팅 이력 조회

    Args:
        session_id: 세션 ID
        limit: 조회할 최대 개수 (기본값: 100)
        skip: 건너뛸 개수 (기본값: 0)

    Returns:
        채팅 이력 목록 및 총 개수
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
