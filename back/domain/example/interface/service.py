from abc import ABC, abstractmethod

from domain.example.model import ExampleCreate, ExampleResponse, ExampleUpdate


class IExampleService(ABC):
    @abstractmethod
    async def create_example(self, data: ExampleCreate) -> ExampleResponse:
        pass

    @abstractmethod
    async def get_example(self, id: str) -> ExampleResponse | None:
        pass

    @abstractmethod
    async def get_examples(self, skip: int = 0, limit: int = 100) -> list[ExampleResponse]:
        pass

    @abstractmethod
    async def update_example(self, id: str, data: ExampleUpdate) -> ExampleResponse | None:
        pass

    @abstractmethod
    async def delete_example(self, id: str) -> bool:
        pass
