"""
시나리오 설명집 DI 컨테이너

의존성 주입 및 싱글톤 관리
"""
from functools import lru_cache

from server.config import get_settings
from domain.scenario.repository import Neo4jScenarioRepository
from domain.scenario.service import ScenarioService


@lru_cache
def get_neo4j_scenario_repository() -> Neo4jScenarioRepository:
    """Neo4j 시나리오 저장소"""
    settings = get_settings()

    return Neo4jScenarioRepository(
        uri=settings.neo4j_uri,
        username=getattr(settings, 'neo4j_username', 'neo4j'),
        password=getattr(settings, 'neo4j_password', 'password')
    )


@lru_cache
def get_scenario_service() -> ScenarioService:
    """시나리오 설명집 서비스"""
    return ScenarioService(
        neo4j_repo=get_neo4j_scenario_repository()
    )
