from fastapi import APIRouter, Depends, HTTPException, status

from domain.example.container import get_example_service
from domain.example.interface import IExampleService
from domain.example.model import ExampleCreate, ExampleResponse, ExampleUpdate

router = APIRouter(prefix="/examples", tags=["examples"])


@router.post("", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
async def create_example(
    data: ExampleCreate,
    service: IExampleService = Depends(get_example_service),
) -> ExampleResponse:
    return await service.create_example(data)


@router.get("", response_model=list[ExampleResponse])
async def get_examples(
    skip: int = 0,
    limit: int = 100,
    service: IExampleService = Depends(get_example_service),
) -> list[ExampleResponse]:
    return await service.get_examples(skip=skip, limit=limit)


@router.get("/{example_id}", response_model=ExampleResponse)
async def get_example(
    example_id: str,
    service: IExampleService = Depends(get_example_service),
) -> ExampleResponse:
    example = await service.get_example(example_id)
    if example is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Example not found",
        )
    return example


@router.patch("/{example_id}", response_model=ExampleResponse)
async def update_example(
    example_id: str,
    data: ExampleUpdate,
    service: IExampleService = Depends(get_example_service),
) -> ExampleResponse:
    example = await service.update_example(example_id, data)
    if example is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Example not found",
        )
    return example


@router.delete("/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_example(
    example_id: str,
    service: IExampleService = Depends(get_example_service),
) -> None:
    deleted = await service.delete_example(example_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Example not found",
        )
