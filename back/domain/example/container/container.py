from functools import lru_cache

from domain.example.interface import IExampleService
from domain.example.repository import ExampleRepository
from domain.example.service import ExampleService


class Container:
    def __init__(self) -> None:
        self._repository = ExampleRepository()
        self._service = ExampleService(repository=self._repository)

    @property
    def service(self) -> IExampleService:
        return self._service


@lru_cache
def get_container() -> Container:
    return Container()


def get_example_service() -> IExampleService:
    return get_container().service
