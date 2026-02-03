from abc import ABC, abstractmethod

from domain.example.model import ExampleCreate, ExampleResponse, ExampleUpdate


class IExampleRepository(ABC):
    @abstractmethod
    async def create(self, data: ExampleCreate) -> ExampleResponse:
        pass

    @abstractmethod
    async def get_by_id(self, id: str) -> ExampleResponse | None:
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ExampleResponse]:
        pass

    @abstractmethod
    async def update(self, id: str, data: ExampleUpdate) -> ExampleResponse | None:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
