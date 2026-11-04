"""
런 세계관 API 라우트
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from domain.run.container import get_run_service

router = APIRouter(prefix="/run", tags=["런 세계관"])


# === Request/Response 모델 ===

class QueryRequest(BaseModel):
    question: str = Field(description="질문")


class QueryResponse(BaseModel):
    query: str
    query_type: str
    response: str
    data: dict | None = None


class SeedNotionRequest(BaseModel):
    worldbuilding: str | None = Field(default=None, description="세계관 마크다운")
    characters: str | None = Field(default=None, description="인물 마크다운")
    events: str | None = Field(default=None, description="사건 마크다운")
    concepts: list[dict] | None = Field(default=None, description="개념 리스트 [{title, content, url}]")


class SearchRequest(BaseModel):
    query: str
    entity_types: list[str] | None = None
    limit: int = 5


# === 엔드포인트 ===

@router.post("/query", response_model=QueryResponse)
async def query_run(request: QueryRequest):
    """자연어 세계관 질의"""
    service = get_run_service()
    result = await service.query(request.question)
    return QueryResponse(**result)


@router.post("/search")
async def search_run(request: SearchRequest):
    """시맨틱 검색"""
    service = get_run_service()
    results = await service.search(
        query=request.query,
        entity_types=request.entity_types,
        limit=request.limit,
    )
    return {"results": results, "count": len(results)}


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """엔티티 상세 조회"""
    service = get_run_service()
    entity = await service.get_entity(entity_id)
    if not entity:
        return {"error": "Entity not found"}
    return entity


@router.get("/graph")
async def get_graph(limit: int = 100):
    """시각화용 그래프 데이터"""
    service = get_run_service()
    return await service.get_graph(limit)


@router.get("/stats")
async def get_stats():
    """저장소 통계"""
    service = get_run_service()
    return service.get_stats()


@router.post("/seed")
async def seed_from_notion(request: SeedNotionRequest):
    """Notion 데이터 → DB 로드"""
    service = get_run_service()
    notion_data = request.model_dump(exclude_none=True)
    result = await service.seed_from_notion_data(notion_data)
    return result


@router.post("/seed/json")
async def seed_from_json():
    """기존 JSON 파일에서 DB 로드"""
    service = get_run_service()
    result = await service.seed_from_json()
    return result


@router.post("/initialize")
async def initialize():
    """서비스 초기화"""
    service = get_run_service()
    result = await service.initialize(auto_seed=True)
    return result
