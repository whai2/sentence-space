"""Supervisor Agent - 멀티 에이전트 오케스트레이터"""

from typing import Any, List
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor

from app.domains.multi_agent.services.agents.supervisor.prompts import SUPERVISOR_PROMPT


def create_supervisor_workflow(
    llm: ChatOpenAI,
    agents: List[Any],
    output_mode: str = "last_message",
) -> Any:
    """Supervisor 워크플로우 생성

    Args:
        llm: LangChain LLM 인스턴스
        agents: Sub-Agent 목록 (notion_agent, clickup_reader, clickup_writer)
        output_mode: 출력 모드 ("last_message" 또는 "full_history")

    Returns:
        컴파일 가능한 StateGraph
    """
    workflow = create_supervisor(
        agents=agents,
        model=llm,
        prompt=SUPERVISOR_PROMPT,
        output_mode=output_mode,
    )

    return workflow
