"""Multi-Agent Dependency Injection Container"""

import os
from dependency_injector import containers, providers
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from app.domains.multi_agent.services.agents.notion.mcp_client import NotionMCPClient
from app.domains.multi_agent.services.agents.clickup.mcp_client import ClickUpMCPClient
from app.domains.multi_agent.handlers.chat_handler import MultiAgentChatHandler
from app.domains.clickup_demo.repositories import SessionRepository, ChatRepository
from app.domains.clickup_demo.services.agent.langfuse_handler import LangFuseHandler
from app.common.database.mongodb import get_database
from app.common.database.neo4j_db import get_neo4j_driver
from app.domains.multi_agent.services.knowledge_graph.neo4j_service import Neo4jKnowledgeGraphService
from app.domains.multi_agent.services.knowledge_graph.query_pre_filter import QueryPreFilter
from app.domains.multi_agent.services.knowledge_graph.graph_gatekeeper import GraphGatekeeper
from app.domains.multi_agent.services.knowledge_graph.topic_extractor import TopicExtractor


class MultiAgentContainer(containers.DeclarativeContainer):
    """Multi-Agent 의존성 주입 컨테이너"""

    # Configuration
    config = providers.Configuration()

    # Memory Saver (Singleton - 모든 대화에서 공유)
    memory_saver = providers.Singleton(MemorySaver)

    # LLM (Singleton - OpenRouter를 통한 모델 접근)
    llm = providers.Singleton(
        ChatOpenAI,
        model="google/gemini-2.5-flash",  # OpenRouter 모델 ID
        temperature=0.7,
        api_key=providers.Callable(lambda: os.environ.get("OPENROUTER_API_KEY")),
        base_url="https://openrouter.ai/api/v1",
    )

    # Notion MCP Client (Singleton)
    notion_mcp_client = providers.Singleton(
        NotionMCPClient,
        notion_token=providers.Callable(lambda: os.environ.get("NOTION_TOKEN")),
    )

    # ClickUp MCP Client (Singleton)
    clickup_mcp_client = providers.Singleton(
        ClickUpMCPClient,
        clickup_token=providers.Callable(lambda: os.environ.get("CLICKUP_ACCESS_TOKEN")),
    )

    # MongoDB Database
    database = providers.Callable(get_database)

    # Repositories
    session_repository = providers.Factory(SessionRepository, db=database)
    chat_repository = providers.Factory(ChatRepository, db=database)

    # Chat Handler
    chat_handler = providers.Factory(
        MultiAgentChatHandler,
        session_repository=session_repository,
        chat_repository=chat_repository,
    )

    # LangFuse Handler (Singleton - 환경변수에서 자동으로 설정 로드)
    langfuse_handler = providers.Singleton(LangFuseHandler)

    # --- Knowledge Graph ---

    # Neo4j Driver (Callable - get_database와 동일 패턴)
    neo4j_driver = providers.Callable(get_neo4j_driver)

    # Knowledge Graph Service (Factory - 요청마다 새 인스턴스)
    knowledge_graph_service = providers.Factory(
        Neo4jKnowledgeGraphService,
        driver=neo4j_driver,
    )

    # KG용 경량 LLM (Singleton - gpt-4o-mini via OpenRouter)
    kg_llm = providers.Singleton(
        ChatOpenAI,
        model="openai/gpt-4o-mini",
        temperature=0.0,
        api_key=providers.Callable(lambda: os.environ.get("OPENROUTER_API_KEY")),
        base_url="https://openrouter.ai/api/v1",
    )

    # Query Pre-Filter (Singleton - stateless regex)
    query_pre_filter = providers.Singleton(QueryPreFilter)

    # Graph Gatekeeper (Singleton - LLM 분류기)
    graph_gatekeeper = providers.Singleton(
        GraphGatekeeper,
        llm=kg_llm,
    )

    # Topic Extractor (Singleton - LLM 토픽 추출)
    topic_extractor = providers.Singleton(
        TopicExtractor,
        llm=kg_llm,
    )
