"""Chat Handler for managing chat sessions and messages"""

from datetime import datetime
from typing import Dict, Any, List

from app.domains.notion_demo.models.documents import SessionDocument, ChatDocument
from app.domains.notion_demo.repositories import SessionRepository, ChatRepository


class ChatHandler:
    """
    채팅 비즈니스 로직 핸들러

    Service Layer와 Repository Layer 사이의 중간 계층
    """

    def __init__(
        self,
        session_repository: SessionRepository,
        chat_repository: ChatRepository,
    ):
        """
        Args:
            session_repository: 세션 리포지토리
            chat_repository: 채팅 리포지토리
        """
        self.session_repository = session_repository
        self.chat_repository = chat_repository

    async def ensure_session_exists(self, session_id: str) -> SessionDocument:
        """
        세션 존재 확인 및 생성

        Args:
            session_id: 세션 ID

        Returns:
            SessionDocument: 세션 문서
        """
        if not await self.session_repository.session_exists(session_id):
            return await self.session_repository.create_session(session_id)

        return await self.session_repository.get_session(session_id)

    async def save_chat(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        node_sequence: List[str],
        execution_logs: List[Dict[str, Any]],
        tool_history: List[Dict[str, Any]],
    ) -> str:
        """
        채팅 저장

        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            assistant_message: AI 응답
            node_sequence: 실행된 노드 순서
            execution_logs: 실행 로그
            tool_history: 도구 실행 이력

        Returns:
            str: 생성된 채팅 문서 ID
        """
        tool_details_data = []
        for idx, tool_exec in enumerate(tool_history, start=1):
            tool_details_data.append({
                "tool_name": tool_exec["tool"],
                "args": tool_exec["args"],
                "success": tool_exec["success"],
                "result_summary": (
                    tool_exec.get("result", "")[:200] if tool_exec["success"] else None
                ),
                "error": tool_exec.get("error") if not tool_exec["success"] else None,
                "iteration": idx,
            })

        tool_names = [tool["tool"] for tool in tool_history]
        unique_tools = list(set(tool_names))

        chat_doc = ChatDocument(
            session_id=session_id,
            user_message=user_message,
            assistant_message=assistant_message,
            node_sequence=node_sequence,
            execution_logs=execution_logs,
            used_tools=unique_tools,
            tool_usage_count=len(tool_names),
            tool_details=tool_details_data,
            created_at=datetime.utcnow(),
        )

        return await self.chat_repository.create_chat(chat_doc)

    async def save_chat_from_stream_event(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        node_sequence: List[str],
        execution_logs: List[Dict[str, Any]],
        tool_details: List[Any],
    ) -> str:
        """
        스트리밍 이벤트에서 채팅 저장

        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            assistant_message: AI 응답
            node_sequence: 실행된 노드 순서
            execution_logs: 실행 로그
            tool_details: 도구 실행 상세 정보

        Returns:
            str: 생성된 채팅 문서 ID
        """
        tool_details_data = []
        for tool_detail in tool_details:
            if isinstance(tool_detail, dict):
                tool_details_data.append({
                    "tool_name": tool_detail.get("tool_name", ""),
                    "args": tool_detail.get("args", {}),
                    "success": tool_detail.get("success", False),
                    "result_summary": tool_detail.get("result_summary"),
                    "error": tool_detail.get("error"),
                    "iteration": tool_detail.get("iteration", 0),
                })
            else:
                tool_details_data.append({
                    "tool_name": tool_detail.tool_name,
                    "args": tool_detail.args,
                    "success": tool_detail.success,
                    "result_summary": tool_detail.result_summary,
                    "error": tool_detail.error,
                    "iteration": tool_detail.iteration,
                })

        tool_names = [td["tool_name"] for td in tool_details_data]
        unique_tools = list(set(tool_names))

        chat_doc = ChatDocument(
            session_id=session_id,
            user_message=user_message,
            assistant_message=assistant_message,
            node_sequence=node_sequence,
            execution_logs=execution_logs,
            used_tools=unique_tools,
            tool_usage_count=len(tool_names),
            tool_details=tool_details_data,
            created_at=datetime.utcnow(),
        )

        return await self.chat_repository.create_chat(chat_doc)

    async def get_session_chats(
        self, session_id: str, limit: int = 100, skip: int = 0
    ) -> List[ChatDocument]:
        """
        세션의 채팅 이력 조회

        Args:
            session_id: 세션 ID
            limit: 조회할 최대 개수
            skip: 건너뛸 개수

        Returns:
            List[ChatDocument]: 채팅 문서 리스트
        """
        return await self.chat_repository.get_chats_by_session(
            session_id, limit=limit, skip=skip
        )

    async def get_session_chat_count(self, session_id: str) -> int:
        """
        세션의 채팅 개수 조회

        Args:
            session_id: 세션 ID

        Returns:
            int: 채팅 개수
        """
        return await self.chat_repository.get_chat_count(session_id)
