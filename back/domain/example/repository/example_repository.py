from datetime import datetime
from uuid import uuid4

from domain.example.interface import IExampleRepository
from domain.example.model import ExampleCreate, ExampleResponse, ExampleUpdate


class ExampleRepository(IExampleRepository):
    def __init__(self) -> None:
        self._storage: dict[str, dict] = {}

    async def create(self, data: ExampleCreate) -> ExampleResponse:
        id = str(uuid4())
        now = datetime.utcnow()
        record = {
            "id": id,
            "name": data.name,
            "description": data.description,
            "created_at": now,
            "updated_at": None,
        }
        self._storage[id] = record
        return ExampleResponse(**record)

    async def get_by_id(self, id: str) -> ExampleResponse | None:
        record = self._storage.get(id)
        if record is None:
            return None
        return ExampleResponse(**record)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ExampleResponse]:
        records = list(self._storage.values())
        return [ExampleResponse(**r) for r in records[skip : skip + limit]]

    async def update(self, id: str, data: ExampleUpdate) -> ExampleResponse | None:
        record = self._storage.get(id)
        if record is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            record.update(update_data)
            record["updated_at"] = datetime.utcnow()

        return ExampleResponse(**record)

    async def delete(self, id: str) -> bool:
        if id not in self._storage:
            return False
        del self._storage[id]
        return True
