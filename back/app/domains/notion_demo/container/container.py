"""Notion Demo Dependency Injection Container"""

import os
from dependency_injector import containers, providers
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from app.domains.notion_demo.services.agent.mcp_client import NotionMCPClient
from app.domains.notion_demo.services.agent.agent import NotionAgent
from app.domains.notion_demo.services.agent.langfuse_handler import LangFuseHandler
from app.domains.notion_demo.repositories import SessionRepository, ChatRepository
from app.domains.notion_demo.handlers import ChatHandler
from app.common.database.mongodb import get_database


class NotionDemoContainer(containers.DeclarativeContainer):
    """Notion Demo 의존성 주입 컨테이너"""

    # Configuration
    config = providers.Configuration()

    # Memory Saver (Singleton - 모든 대화에서 공유)
    memory_saver = providers.Singleton(MemorySaver)

    # LLM (Singleton - OpenRouter를 통한 모델 접근)
    llm = providers.Singleton(
        ChatOpenAI,
        model="google/gemini-2.5-flash",
        temperature=0.7,
        api_key=providers.Callable(lambda: os.environ.get("OPENROUTER_API_KEY")),
        base_url="https://openrouter.ai/api/v1",
    )

    # Notion MCP Client (Singleton - MCP 서버 연결 공유)
    mcp_client = providers.Singleton(
        NotionMCPClient,
        notion_token=providers.Callable(lambda: os.environ.get("NOTION_API_KEY")),
    )

    # LangFuse Handler (Singleton - 환경변수에서 자동으로 설정 로드)
    langfuse_handler = providers.Singleton(LangFuseHandler)

    # MongoDB Database (Callable - get_database() 함수 호출)
    database = providers.Callable(get_database)

    # Repositories (Factory - 요청마다 새 인스턴스)
    session_repository = providers.Factory(SessionRepository, db=database)

    chat_repository = providers.Factory(ChatRepository, db=database)

    # Handlers (Factory - 비즈니스 로직 처리)
    chat_handler = providers.Factory(
        ChatHandler,
        session_repository=session_repository,
        chat_repository=chat_repository,
    )

    # Notion Agent (Singleton - MCP 세션 및 도구 재사용, Handler 주입)
    notion_agent = providers.Singleton(
        NotionAgent,
        llm=llm,
        mcp_client=mcp_client,
        memory_saver=memory_saver,
        chat_handler=chat_handler,
        langfuse_handler=langfuse_handler,
    )
