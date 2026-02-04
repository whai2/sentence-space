from functools import lru_cache

from server.config import get_settings
from domain.orv.repository import ORVGameRepository
from domain.orv.service import ORVGameService
from domain.orv.story import StoryManager
from domain.orv.interface import IORVGameService


@lru_cache
def get_orv_game_repository() -> ORVGameRepository:
    return ORVGameRepository()


@lru_cache
def get_story_manager() -> StoryManager:
    """스토리 매니저 싱글턴"""
    return StoryManager()


@lru_cache
def get_orv_game_service() -> IORVGameService:
    settings = get_settings()
    return ORVGameService(
        repository=get_orv_game_repository(),
        openrouter_api_key=settings.openrouter_api_key,
        model_name=settings.llm_model,
        data_dir=settings.data_dir,
        story_manager=get_story_manager(),
        langfuse_public_key=settings.langfuse_public_key,
        langfuse_secret_key=settings.langfuse_secret_key,
        langfuse_host=settings.langfuse_host,
        langfuse_enabled=settings.langfuse_enabled,
    )
