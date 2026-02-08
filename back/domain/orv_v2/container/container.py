"""
ORV v2 Dependency Injection Container

모든 의존성을 여기서 조립
"""
from functools import lru_cache

from server.config import get_settings
from domain.orv_v2.config import LLMFactory
from domain.orv_v2.agents import (
    OrchestratorAgent,
    NarratorAgent,
    NPCAgent,
    AutoNarratorAgent,
    GraphRAGRetriever,
)
from domain.orv_v2.agents.story_planner import StoryPlannerAgent
from domain.orv_v2.agents.story_executor import StoryExecutorAgent
from domain.orv_v2.repository import MongoDBGameRepository
from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository
from domain.orv_v2.graph import GameWorkflow
from domain.orv_v2.service import ORVGameService


# ============================================
# Singletons
# ============================================

@lru_cache
def get_llm_factory() -> LLMFactory:
    """LLM Factory 싱글톤"""
    settings = get_settings()
    return LLMFactory(
        anthropic_api_key=settings.anthropic_api_key,
        openai_api_key=settings.openai_api_key,
        openrouter_api_key=settings.openrouter_api_key,  # fallback
    )


@lru_cache
def get_orchestrator_agent() -> OrchestratorAgent:
    """Orchestrator Agent 싱글톤"""
    factory = get_llm_factory()
    return OrchestratorAgent(llm=factory.get_orchestrator_llm())


@lru_cache
def get_narrator_agent() -> NarratorAgent:
    """Narrator Agent 싱글톤"""
    factory = get_llm_factory()
    return NarratorAgent(llm=factory.get_narrator_llm())


@lru_cache
def get_npc_agent() -> NPCAgent:
    """NPC Agent 싱글톤"""
    factory = get_llm_factory()
    return NPCAgent(llm=factory.get_npc_llm())


@lru_cache
def get_auto_narrator_agent() -> AutoNarratorAgent:
    """Auto-Narrator Agent 싱글톤"""
    factory = get_llm_factory()
    return AutoNarratorAgent(llm=factory.get_narrator_llm())  # Reuse GPT-4o


@lru_cache
def get_graph_rag_retriever() -> GraphRAGRetriever:
    """GraphRAG Retriever 싱글톤"""
    return GraphRAGRetriever(neo4j_repo=get_neo4j_repository())


@lru_cache
def get_story_planner_agent() -> StoryPlannerAgent:
    """Story Planner Agent 싱글톤"""
    factory = get_llm_factory()
    return StoryPlannerAgent(llm=factory.get_npc_llm())  # Use Haiku 4.5 for speed (10x faster, 20x cheaper)


@lru_cache
def get_story_executor_agent() -> StoryExecutorAgent:
    """Story Executor Agent 싱글톤"""
    return StoryExecutorAgent()  # No LLM needed


@lru_cache
def get_repository() -> MongoDBGameRepository:
    """MongoDB Repository 싱글톤"""
    settings = get_settings()

    # MongoDB URI (환경변수 또는 기본값)
    mongodb_uri = getattr(settings, "mongodb_uri", "mongodb://localhost:27017")

    return MongoDBGameRepository(
        mongodb_uri=mongodb_uri,
        database_name="orv_game_v2",
        neo4j_repo=get_neo4j_repository(),  # NEW: Neo4j 연결
    )


@lru_cache
def get_neo4j_repository() -> Neo4jGraphRepository:
    """Neo4j Repository 싱글톤"""
    settings = get_settings()

    # Neo4j URI (환경변수 또는 기본값)
    neo4j_uri = getattr(settings, "neo4j_uri", "bolt://localhost:7687")
    neo4j_username = getattr(settings, "neo4j_username", "neo4j")
    neo4j_password = getattr(settings, "neo4j_password", "password")

    return Neo4jGraphRepository(
        uri=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
    )


@lru_cache
def get_game_workflow() -> GameWorkflow:
    """Game Workflow 싱글톤"""
    return GameWorkflow(
        orchestrator=get_orchestrator_agent(),
        narrator=get_narrator_agent(),
        npc_agent=get_npc_agent(),
        auto_narrator=get_auto_narrator_agent(),
        repository=get_repository(),
        graph_rag_retriever=get_graph_rag_retriever(),
        story_planner=get_story_planner_agent(),  # NEW
        story_executor=get_story_executor_agent(),  # NEW
    )


@lru_cache
def get_game_service() -> ORVGameService:
    """Game Service 싱글톤"""
    return ORVGameService(
        workflow=get_game_workflow(),
        repository=get_repository(),
    )


# ============================================
# Startup/Shutdown
# ============================================

async def startup():
    """애플리케이션 시작 시 초기화"""
    # MongoDB 인덱스 생성
    repo = get_repository()
    await repo.create_indexes()
    print("✅ MongoDB indexes created")

    # Neo4j 연결 확인
    neo4j_repo = get_neo4j_repository()
    is_connected = await neo4j_repo.verify_connectivity()
    if is_connected:
        print("✅ Neo4j connected")
        # 제약 조건 생성
        await neo4j_repo.create_constraints()
        print("✅ Neo4j constraints created")
    else:
        print("⚠️  Neo4j connection failed - GraphRAG features will be unavailable")


async def shutdown():
    """애플리케이션 종료 시 정리"""
    # MongoDB 연결 종료
    repo = get_repository()
    await repo.close()
    print("✅ MongoDB connection closed")

    # Neo4j 연결 종료
    neo4j_repo = get_neo4j_repository()
    await neo4j_repo.close()
    print("✅ Neo4j connection closed")
