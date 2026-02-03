from datetime import datetime

from pydantic import BaseModel, Field


class ExampleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class ExampleCreate(ExampleBase):
    pass


class ExampleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class ExampleResponse(ExampleBase):
    id: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
