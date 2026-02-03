from domain.example.interface import IExampleRepository, IExampleService
from domain.example.model import ExampleCreate, ExampleResponse, ExampleUpdate


class ExampleService(IExampleService):
    def __init__(self, repository: IExampleRepository) -> None:
        self._repository = repository

    async def create_example(self, data: ExampleCreate) -> ExampleResponse:
        return await self._repository.create(data)

    async def get_example(self, id: str) -> ExampleResponse | None:
        return await self._repository.get_by_id(id)

    async def get_examples(self, skip: int = 0, limit: int = 100) -> list[ExampleResponse]:
        return await self._repository.get_all(skip=skip, limit=limit)

    async def update_example(self, id: str, data: ExampleUpdate) -> ExampleResponse | None:
        return await self._repository.update(id, data)

    async def delete_example(self, id: str) -> bool:
        return await self._repository.delete(id)
