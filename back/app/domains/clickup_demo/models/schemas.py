"""ClickUp Demo API Schemas"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ClickUpChatRequest(BaseModel):
    """ClickUp 채팅 요청"""

    message: str = Field(..., description="사용자 메시지")
    conversation_id: Optional[str] = Field(
        None, description="대화 ID (없으면 자동 생성)"
    )


class ToolExecutionDetail(BaseModel):
    """도구 실행 상세 정보"""

    tool_name: str = Field(..., description="도구 이름")
    args: Dict[str, Any] = Field(..., description="도구 인자")
    success: bool = Field(..., description="실행 성공 여부")
    result_summary: Optional[str] = Field(None, description="결과 요약")
    error: Optional[str] = Field(None, description="에러 메시지")
    iteration: int = Field(..., description="실행 순서 (iteration)")


class ClickUpChatResponse(BaseModel):
    """ClickUp 채팅 응답"""

    conversation_id: str = Field(..., description="대화 ID")
    user_message: str = Field(..., description="사용자 메시지")
    assistant_message: str = Field(..., description="어시스턴트 응답")
    node_sequence: List[str] = Field(..., description="실행된 노드 순서")
    execution_logs: List[Dict[str, Any]] = Field(..., description="실행 로그")
    used_tools: List[str] = Field(default_factory=list, description="사용된 도구 목록")
    tool_usage_count: int = Field(default=0, description="도구 사용 횟수")
    tool_details: List[ToolExecutionDetail] = Field(
        default_factory=list, description="도구 실행 상세 정보"
    )


class ClickUpStreamEvent(BaseModel):
    """ClickUp 스트리밍 이벤트"""

    event_type: str = Field(
        ..., description="이벤트 타입: node_start, node_end, tool_result, final"
    )
    node_name: Optional[str] = Field(
        None, description="노드 이름 (reason, act, observe, finalize)"
    )
    iteration: Optional[int] = Field(None, description="현재 반복 횟수")
    data: Dict[str, Any] = Field(..., description="이벤트 데이터")
    timestamp: float = Field(..., description="타임스탬프")


class NodeStartEvent(BaseModel):
    """노드 시작 이벤트"""

    node_name: str
    iteration: int


class NodeEndEvent(BaseModel):
    """노드 종료 이벤트"""

    node_name: str
    iteration: int
    result: Dict[str, Any]


class ToolResultEvent(BaseModel):
    """도구 실행 결과 이벤트"""

    tool_name: str
    args: Dict[str, Any]
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    iteration: int


class FinalEvent(BaseModel):
    """최종 결과 이벤트"""

    conversation_id: str
    assistant_message: str
    node_sequence: List[str]
    execution_logs: List[Dict[str, Any]]
    used_tools: List[str]
    tool_usage_count: int
    tool_details: List[ToolExecutionDetail]
