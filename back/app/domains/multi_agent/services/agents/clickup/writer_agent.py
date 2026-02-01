"""ClickUp Writer Agent - 쓰기 전용 에이전트"""

from typing import Any, List
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.domains.multi_agent.services.agents.clickup.prompts import (
    get_clickup_writer_prompt,
)

# 쓰기 도구 이름 목록
WRITER_TOOL_NAMES = {
    "manage_task",
    "task_comments",
    "manage_container",
    "operate_tags",
    "task_time_tracking",
    "attach_file_to_task",
}


def filter_writer_tools(tools: List[Any]) -> List[Any]:
    """쓰기 도구만 필터링

    Args:
        tools: 전체 도구 목록

    Returns:
        쓰기 도구만 포함된 목록
    """
    return [tool for tool in tools if tool.name in WRITER_TOOL_NAMES]


def create_clickup_writer_agent(
    llm: ChatOpenAI,
    tools: List[Any],
    name: str = "clickup_writer",
) -> Any:
    """ClickUp Writer 에이전트 생성

    Args:
        llm: LangChain LLM 인스턴스
        tools: ClickUp MCP 도구 목록 (전체)
        name: 에이전트 이름

    Returns:
        컴파일된 ReAct 에이전트
    """
    # 쓰기 도구만 필터링
    writer_tools = filter_writer_tools(tools)

    agent = create_react_agent(
        model=llm,
        tools=writer_tools,
        name=name,
        prompt=get_clickup_writer_prompt(),
    )

    return agent
