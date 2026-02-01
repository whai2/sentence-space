"""ClickUp Reader Agent - 읽기 전용 에이전트"""

from typing import Any, List
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.domains.multi_agent.services.agents.clickup.prompts import (
    get_clickup_reader_prompt,
)

# 읽기 전용 도구 이름 목록
READER_TOOL_NAMES = {
    "get_workspace_hierarchy",
    "search_tasks",
    "get_container",
    "find_members",
}


def filter_reader_tools(tools: List[Any]) -> List[Any]:
    """읽기 전용 도구만 필터링

    Args:
        tools: 전체 도구 목록

    Returns:
        읽기 전용 도구만 포함된 목록
    """
    return [tool for tool in tools if tool.name in READER_TOOL_NAMES]


def create_clickup_reader_agent(
    llm: ChatOpenAI,
    tools: List[Any],
    name: str = "clickup_reader",
) -> Any:
    """ClickUp Reader 에이전트 생성

    Args:
        llm: LangChain LLM 인스턴스
        tools: ClickUp MCP 도구 목록 (전체)
        name: 에이전트 이름

    Returns:
        컴파일된 ReAct 에이전트
    """
    # 읽기 전용 도구만 필터링
    reader_tools = filter_reader_tools(tools)

    agent = create_react_agent(
        model=llm,
        tools=reader_tools,
        name=name,
        prompt=get_clickup_reader_prompt(),
    )

    return agent
