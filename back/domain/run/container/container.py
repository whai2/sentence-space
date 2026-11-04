"""
런 세계관 DI 컨테이너

의존성 주입 및 싱글톤 관리
"""
from functools import lru_cache
from typing import Union

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from server.config import get_settings


@lru_cache
def get_run_pinecone_repository():
    """Pinecone 벡터 저장소 (런 전용 인덱스)"""
    from domain.run.repository.pinecone_repository import PineconeRunRepository

    settings = get_settings()
    return PineconeRunRepository(
        api_key=settings.pinecone_api_key,
        index_name=getattr(settings, "pinecone_run_index_name", "run-worldbuilding"),
        openai_api_key=settings.openai_api_key,
    )


@lru_cache
def get_run_neo4j_repository():
    """Neo4j 그래프 저장소 (공유 인스턴스, Run 접두사 노드)"""
    from domain.run.repository.neo4j_repository import Neo4jRunRepository

    settings = get_settings()
    return Neo4jRunRepository(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
    )


@lru_cache
def get_run_llm() -> Union[ChatOpenAI, ChatAnthropic]:
    """LLM (OpenRouter 또는 직접 Anthropic API)"""
    settings = get_settings()

    if settings.openrouter_api_key:
        return ChatOpenAI(
            model=settings.llm_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.3,
            max_tokens=4096,
        )

    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.3,
        max_tokens=4096,
    )


@lru_cache
def get_lore_retriever():
    """세계관 검색 에이전트"""
    from domain.run.agents.lore_retriever import LoreRetrieverAgent

    return LoreRetrieverAgent(
        vector_repo=get_run_pinecone_repository(),
        neo4j_repo=get_run_neo4j_repository(),
    )


@lru_cache
def get_run_workflow():
    """런 워크플로우"""
    from domain.run.graph.workflow import RunWorkflow

    return RunWorkflow(
        retriever=get_lore_retriever(),
        llm=get_run_llm(),
    )


@lru_cache
def get_run_service():
    """런 서비스"""
    from domain.run.service.run_service import RunService

    return RunService(
        vector_repo=get_run_pinecone_repository(),
        neo4j_repo=get_run_neo4j_repository(),
        retriever=get_lore_retriever(),
        workflow=get_run_workflow(),
    )
