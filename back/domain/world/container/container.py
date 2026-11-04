from functools import lru_cache

from domain.world.interface import IGameService
from domain.world.repository import GameRepository
from domain.world.service import GameService
from server.config import get_settings


class Container:
    def __init__(self) -> None:
        settings = get_settings()
        self._repository = GameRepository()
        self._service = GameService(
            repository=self._repository,
            openrouter_api_key=settings.openrouter_api_key,
            model_name=settings.llm_model,
        )

    @property
    def service(self) -> IGameService:
        return self._service


@lru_cache
def get_container() -> Container:
    return Container()


def get_game_service() -> IGameService:
    return get_container().service
