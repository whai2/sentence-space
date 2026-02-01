"""ClickUp Demo State Models"""

from typing import List, Dict, Any, TypedDict
from langchain_core.messages import BaseMessage


class ClickUpState(TypedDict):
    """ClickUp 에이전트 상태"""

    # 메시지
    messages: List[BaseMessage]

    # 실행 추적
    node_sequence: List[str]
    execution_logs: List[Dict[str, Any]]

    # 반복 제어
    max_iterations: int
    current_iteration: int

    # 도구 실행 기록
    tool_history: List[Dict[str, Any]]

    # 현재 결정
    current_decision: Dict[str, Any]
    is_final_answer: bool
