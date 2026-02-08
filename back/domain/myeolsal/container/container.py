"""
멸살법 DI 컨테이너

의존성 주입 및 싱글톤 관리
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Union

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from server.config import get_settings
from domain.myeolsal.models import MyeolsalRules
from domain.myeolsal.repository import ChromaBeastRepository, Neo4jMyeolsalRepository
from domain.myeolsal.agents import (
    BeastGeneratorAgent,
    BeastRetrieverAgent,
    BeastValidatorAgent,
)
from domain.myeolsal.graph import MyeolsalWorkflow
from domain.myeolsal.service import MyeolsalService


@lru_cache
def get_myeolsal_rules() -> MyeolsalRules:
    """멸살법 규칙 로드"""
    rules_path = Path(__file__).parent.parent / "data" / "rules.json"

    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return MyeolsalRules(**data)

    # 기본 규칙 반환
    return MyeolsalRules()


@lru_cache
def get_chroma_repository() -> ChromaBeastRepository:
    """ChromaDB 저장소 (기본 임베딩 함수 사용)"""
    settings = get_settings()
    # data_dir 설정이 있으면 사용, 없으면 기본 경로
    persist_dir = getattr(settings, 'data_dir', './data') + "/chroma_myeolsal"

    return ChromaBeastRepository(
        persist_directory=persist_dir,
        collection_name="myeolsal_beasts"
    )


@lru_cache
def get_neo4j_repository() -> Neo4jMyeolsalRepository:
    """Neo4j 저장소"""
    settings = get_settings()

    return Neo4jMyeolsalRepository(
        uri=settings.neo4j_uri,
        username=getattr(settings, 'neo4j_username', 'neo4j'),
        password=getattr(settings, 'neo4j_password', 'password')
    )


@lru_cache
def get_llm() -> Union[ChatOpenAI, ChatAnthropic]:
    """LLM (OpenRouter 또는 직접 Anthropic API)"""
    settings = get_settings()

    # OpenRouter 사용 (우선)
    if settings.openrouter_api_key:
        return ChatOpenAI(
            model=settings.llm_model,  # "anthropic/claude-3.5-sonnet" 등
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.5,
            max_tokens=4096
        )

    # 직접 Anthropic API 사용
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.5,
        max_tokens=4096
    )


@lru_cache
def get_retriever() -> BeastRetrieverAgent:
    """괴수 검색 에이전트"""
    return BeastRetrieverAgent(
        chroma_repo=get_chroma_repository(),
        neo4j_repo=get_neo4j_repository()
    )


@lru_cache
def get_generator() -> BeastGeneratorAgent:
    """괴수 생성 에이전트"""
    rules = get_myeolsal_rules()

    return BeastGeneratorAgent(
        llm=get_llm(),
        rules=rules
    )


@lru_cache
def get_validator() -> BeastValidatorAgent:
    """괴수 검증 에이전트"""
    return BeastValidatorAgent(rules=get_myeolsal_rules())


@lru_cache
def get_workflow() -> MyeolsalWorkflow:
    """멸살법 워크플로우"""
    return MyeolsalWorkflow(
        retriever=get_retriever(),
        generator=get_generator(),
        validator=get_validator(),
        llm=get_llm()
    )


@lru_cache
def get_myeolsal_service() -> MyeolsalService:
    """멸살법 서비스"""
    return MyeolsalService(
        chroma_repo=get_chroma_repository(),
        neo4j_repo=get_neo4j_repository(),
        retriever=get_retriever(),
        generator=get_generator(),
        validator=get_validator(),
        workflow=get_workflow(),
        rules=get_myeolsal_rules()
    )
