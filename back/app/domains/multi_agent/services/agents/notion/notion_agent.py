"""Notion Agent - 읽기/찾기 전용 에이전트"""

from typing import Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.domains.multi_agent.services.agents.notion.prompts import NOTION_AGENT_PROMPT


def create_notion_agent(
    llm: ChatOpenAI,
    tools: list[Any],
    name: str = "notion_agent",
) -> Any:
    """Notion 에이전트 생성

    Args:
        llm: LangChain LLM 인스턴스
        tools: Notion MCP 도구 목록
        name: 에이전트 이름

    Returns:
        컴파일된 ReAct 에이전트
    """
    agent = create_react_agent(
        model=llm,
        tools=tools,
        name=name,
        prompt=NOTION_AGENT_PROMPT,
    )

    return agent
