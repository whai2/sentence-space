"""스트리밍 이벤트 DTO 클래스"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from app.domains.notion_demo.services.agent.constants import EventTypes


@dataclass
class StreamEvent:
    """기본 스트리밍 이벤트"""
    event_type: str
    node_name: str
    iteration: int
    data: Dict[str, Any]
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)


class NodeStartEvent(StreamEvent):
    """노드 시작 이벤트"""

    @classmethod
    def create(cls, node_name: str, iteration: int, node_sequence: List[str]):
        return cls(
            event_type=EventTypes.NODE_START,
            node_name=node_name,
            iteration=iteration,
            data={"node_sequence": node_sequence}
        )


class NodeEndEvent(StreamEvent):
    """노드 종료 이벤트 (reason 노드용)"""

    @classmethod
    def create(cls, node_name: str, iteration: int, has_tool_calls: bool, is_final: bool):
        return cls(
            event_type=EventTypes.NODE_END,
            node_name=node_name,
            iteration=iteration,
            data={
                "has_tool_calls": has_tool_calls,
                "is_final": is_final,
            }
        )


class ToolResultEvent(StreamEvent):
    """도구 실행 결과 이벤트"""

    @classmethod
    def create(
        cls,
        node_name: str,
        iteration: int,
        tool_name: str,
        args: Dict[str, Any],
        success: bool,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ):
        return cls(
            event_type=EventTypes.TOOL_RESULT,
            node_name=node_name,
            iteration=iteration,
            data={
                "tool_name": tool_name,
                "args": args,
                "success": success,
                "result": result,
                "error": error,
            }
        )


@dataclass
class ToolDetail:
    """도구 실행 상세 정보"""
    tool_name: str
    args: Dict[str, Any]
    success: bool
    result_summary: Optional[str]
    error: Optional[str]
    iteration: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FinalEvent(StreamEvent):
    """최종 결과 이벤트"""

    @classmethod
    def create(
        cls,
        node_name: str,
        iteration: int,
        conversation_id: str,
        assistant_message: str,
        node_sequence: List[str],
        execution_logs: List[Dict[str, Any]],
        used_tools: List[str],
        tool_usage_count: int,
        tool_details: List[Dict[str, Any]],
    ):
        return cls(
            event_type=EventTypes.FINAL,
            node_name=node_name,
            iteration=iteration,
            data={
                "conversation_id": conversation_id,
                "assistant_message": assistant_message,
                "node_sequence": node_sequence,
                "execution_logs": execution_logs,
                "used_tools": used_tools,
                "tool_usage_count": tool_usage_count,
                "tool_details": tool_details,
            }
        )


def create_tool_details(tool_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """도구 실행 기록을 ToolDetail 리스트로 변환"""
    tool_details = []
    for idx, tool_exec in enumerate(tool_history, start=1):
        detail = ToolDetail(
            tool_name=tool_exec.get("tool", ""),
            args=tool_exec.get("args", {}),
            success=tool_exec.get("success", False),
            result_summary=(
                str(tool_exec.get("result", ""))[:200]
                if tool_exec.get("success")
                else None
            ),
            error=(
                tool_exec.get("error")
                if not tool_exec.get("success")
                else None
            ),
            iteration=idx,
        )
        tool_details.append(detail.to_dict())
    return tool_details
