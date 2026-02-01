"""Multi-Agent Chat Handler"""

from typing import Optional, Dict, Any, List

from app.domains.clickup_demo.repositories import SessionRepository, ChatRepository
from app.domains.clickup_demo.models.documents import ChatDocument


class MultiAgentChatHandler:
    """멀티 에이전트 채팅 핸들러

    세션 및 채팅 이력 관리
    기존 ClickUp 리포지토리 재사용
    """

    def __init__(
        self,
        session_repository: SessionRepository,
        chat_repository: ChatRepository,
    ):
        self.session_repository = session_repository
        self.chat_repository = chat_repository

    async def get_or_create_session(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """세션 조회 또는 생성

        Args:
            session_id: 세션 ID
            metadata: 세션 메타데이터

        Returns:
            세션 정보
        """
        session = await self.session_repository.get_session(session_id)
        if session:
            return {
                "session_id": session.session_id,
                "created_at": session.created_at,
                "metadata": session.metadata,
            }

        new_session = await self.session_repository.create_session(
            session_id=session_id,
            metadata=metadata or {"agent_type": "multi_agent"},
        )
        return {
            "session_id": new_session.session_id,
            "created_at": new_session.created_at,
            "metadata": new_session.metadata,
        }

    async def save_chat(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        agent_path: List[str],
        tool_details: Optional[List] = None,
    ) -> Dict[str, Any]:
        """채팅 저장

        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            assistant_message: 어시스턴트 응답
            agent_path: 호출된 에이전트 경로 (예: ["supervisor", "notion_agent"])
            tool_details: 도구 실행 상세

        Returns:
            저장된 채팅 정보
        """
        chat_doc = ChatDocument(
            session_id=session_id,
            user_message=user_message,
            assistant_message=assistant_message,
            node_sequence=agent_path,
            execution_logs=[],
            used_tools=[],
            tool_usage_count=0,
            tool_details=tool_details or [],
        )
        chat_id = await self.chat_repository.create_chat(chat_doc)
        return {
            "id": chat_id,
            "session_id": session_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "agent_path": agent_path,
            "created_at": chat_doc.created_at,
        }

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """세션 채팅 이력 조회

        Args:
            session_id: 세션 ID
            limit: 조회 개수 제한

        Returns:
            채팅 이력 목록
        """
        chats = await self.chat_repository.get_chats_by_session(
            session_id, limit=limit
        )
        return [
            {
                "user_message": chat.user_message,
                "assistant_message": chat.assistant_message,
                "agent_path": chat.node_sequence,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
            }
            for chat in chats
        ]

    async def get_all_sessions(
        self,
        limit: int = 100,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """멀티 에이전트 세션 목록 조회

        Args:
            limit: 조회 개수 제한
            skip: 건너뛸 개수

        Returns:
            세션 목록 및 전체 개수
        """
        # metadata.agent_type이 "multi_agent"인 세션만 조회
        sessions = await self.session_repository.get_sessions_by_metadata(
            {"agent_type": "multi_agent"},
            limit=limit,
            skip=skip,
        )
        total = await self.session_repository.count_sessions_by_metadata(
            {"agent_type": "multi_agent"}
        )
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "metadata": s.metadata,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in sessions
            ],
            "total": total,
        }
