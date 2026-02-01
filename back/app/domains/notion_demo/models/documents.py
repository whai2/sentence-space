"""MongoDB Document Models for Notion Demo"""

from typing import List, Dict, Any
from pydantic import Field

from app.common.database.models import MongoBaseModel


class SessionDocument(MongoBaseModel):
    """
    채팅 세션 문서

    Attributes:
        session_id: 세션 UUID (conversation_id와 동일)
        metadata: 확장 가능한 메타데이터 (사용자 정보, 설정 등)
        created_at: 세션 생성 시간
        updated_at: 세션 마지막 업데이트 시간
    """

    session_id: str = Field(..., description="세션 고유 ID (UUID)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="확장 가능한 메타데이터"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": {"user_id": "user123", "source": "web"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class ChatDocument(MongoBaseModel):
    """
    채팅 메시지 문서

    Attributes:
        session_id: 세션 ID (SessionDocument 참조)
        user_message: 사용자 메시지
        assistant_message: AI 어시스턴트 응답
        node_sequence: 실행된 노드 순서 (LangGraph)
        execution_logs: 실행 로그
        used_tools: 사용된 도구 목록
        tool_usage_count: 도구 사용 횟수
        tool_details: 도구 실행 상세 정보
        created_at: 채팅 생성 시간
    """

    session_id: str = Field(..., description="세션 ID")
    user_message: str = Field(..., description="사용자 메시지")
    assistant_message: str = Field(..., description="AI 어시스턴트 응답")
    node_sequence: List[str] = Field(
        default_factory=list, description="실행된 노드 순서"
    )
    execution_logs: List[Dict[str, Any]] = Field(
        default_factory=list, description="실행 로그"
    )
    used_tools: List[str] = Field(default_factory=list, description="사용된 도구 목록")
    tool_usage_count: int = Field(default=0, description="도구 사용 횟수")
    tool_details: List[Dict[str, Any]] = Field(
        default_factory=list, description="도구 실행 상세 정보"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_message": "페이지 목록을 보여줘",
                "assistant_message": "다음은 사용 가능한 페이지 목록입니다...",
                "node_sequence": ["reason", "act", "observe", "finalize"],
                "execution_logs": [],
                "used_tools": ["search"],
                "tool_usage_count": 1,
                "tool_details": [
                    {
                        "tool_name": "search",
                        "args": {},
                        "success": True,
                        "result_summary": "Retrieved 3 pages",
                        "iteration": 1,
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
