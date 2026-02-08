"""
LangGraph State 정의

Graph 노드 간 데이터 전달에 사용되는 상태
"""
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from .base import GameState
from .scenario import ScenarioContext
from .agent_output import OrchestratorDecision, NarratorOutput, StateChange


class GraphState(TypedDict):
    """
    LangGraph 워크플로우 상태

    노드 간 데이터 전달 구조
    """
    # ============================================
    # 입력 (사용자로부터)
    # ============================================
    session_id: str
    player_action: str

    # ============================================
    # 게임 상태 (MongoDB에서 로드)
    # ============================================
    game_state: GameState

    # ============================================
    # 시나리오 컨텍스트
    # ============================================
    scenario_context: ScenarioContext | None

    # ============================================
    # Agent 출력
    # ============================================
    # Orchestrator 판단
    orchestrator_decision: OrchestratorDecision | None

    # Narrator 서술
    narrator_output: NarratorOutput | None

    # ============================================
    # 검증 결과
    # ============================================
    validation_passed: bool
    validation_error: str | None

    # ============================================
    # 최종 적용될 상태 변경
    # ============================================
    applied_changes: StateChange | None

    # ============================================
    # 메시지 히스토리 (최근 N턴만)
    # ============================================
    messages: Annotated[list[BaseMessage], add_messages]

    # ============================================
    # 시스템 메시지 (도깨비 브리핑 등)
    # ============================================
    system_messages: list[str]

    # ============================================
    # 에러 처리
    # ============================================
    error: str | None
    retry_count: int
