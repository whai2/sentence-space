"""Multi-Agent State Definition"""

from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage


class MultiAgentState(TypedDict):
    """멀티 에이전트 시스템의 공유 상태

    Supervisor와 모든 Sub-Agent가 공유하는 상태입니다.
    """

    # 메시지 히스토리 (LangGraph 기본)
    messages: List[BaseMessage]

    # 현재 활성 에이전트
    current_agent: str  # "supervisor" | "notion" | "clickup_reader" | "clickup_writer"

    # Supervisor의 라우팅 결정 이유
    supervisor_reasoning: Optional[str]

    # 각 에이전트의 출력 결과
    agent_outputs: Dict[str, Any]

    # 도구 실행 히스토리
    tool_history: List[Dict[str, Any]]

    # 반복 카운트
    iteration_count: int
    max_iterations: int
