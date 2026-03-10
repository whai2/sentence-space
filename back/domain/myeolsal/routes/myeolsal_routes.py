"""
멸살법 API 라우트

FastAPI 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from domain.myeolsal.container import get_myeolsal_service


router = APIRouter(prefix="/myeolsal", tags=["멸살법"])


# ============================================
# 요청/응답 모델
# ============================================

class QueryRequest(BaseModel):
    """RAG 질의 요청"""
    question: str = Field(description="질문")


class QueryResponse(BaseModel):
    """RAG 질의 응답"""
    query: str
    response: str
    query_type: str | None = None
    data: dict | None = None


class GenerateBeastRequest(BaseModel):
    """괴수 생성 요청"""
    concept: str = Field(description="괴수 컨셉 (예: '화염 늑대')")
    grade: str | None = Field(default=None, description="등급 지정")
    species: str | None = Field(default=None, description="종 지정")
    save: bool = Field(default=True, description="저장 여부")


class SearchResponse(BaseModel):
    """검색 응답"""
    results: list[dict]
    count: int


class StatsResponse(BaseModel):
    """통계 응답"""
    pinecone: dict  # includes scenario_distribution
    rules: dict


# ============================================
# 엔드포인트
# ============================================

@router.post("/query", response_model=QueryResponse)
async def query_myeolsal(request: QueryRequest):
    """
    멸살법 RAG 질의

    자연어 질문을 받아 괴수 정보를 검색하거나 새로운 괴수를 생성합니다.
    """
    service = get_myeolsal_service()
    result = await service.query(request.question)

    return QueryResponse(
        query=result["query"],
        response=result["response"],
        query_type=result.get("query_type"),
        data=result.get("data")
    )


@router.get("/beasts", response_model=SearchResponse)
async def search_beasts(
    q: str = Query(description="검색 쿼리"),
    grade: str | None = Query(default=None, description="등급 필터"),
    species: str | None = Query(default=None, description="종 필터"),
    scenario: str | None = Query(default=None, description="시나리오 필터 (예: scenario_main_001)"),
    limit: int = Query(default=10, ge=1, le=50, description="결과 수")
):
    """괴수 검색"""
    service = get_myeolsal_service()
    results = await service.search_beasts(
        query=q,
        grade=grade,
        species=species,
        scenario=scenario,
        limit=limit
    )

    return SearchResponse(results=results, count=len(results))


@router.get("/beasts/list")
async def list_beasts(
    offset: int = Query(default=0, ge=0, description="오프셋"),
    limit: int = Query(default=50, ge=1, le=100, description="페이지 크기"),
    grade: str | None = Query(default=None, description="등급 필터"),
    species: str | None = Query(default=None, description="종 필터"),
    include_stats: bool = Query(default=False, description="통계 포함 여부"),
):
    """괴수 전체 목록 (페이지네이션)"""
    service = get_myeolsal_service()
    return service.list_beasts(
        offset=offset, limit=limit, grade=grade, species=species,
        include_stats=include_stats,
    )


@router.get("/beasts/{beast_id}")
async def get_beast(beast_id: str):
    """괴수 상세 조회"""
    service = get_myeolsal_service()
    result = await service.get_beast(beast_id)

    if not result:
        raise HTTPException(status_code=404, detail="괴수를 찾을 수 없습니다")

    return result


@router.get("/beasts/grade/{grade}", response_model=SearchResponse)
async def get_beasts_by_grade(grade: str):
    """등급별 괴수 목록"""
    service = get_myeolsal_service()
    results = await service.get_beasts_by_grade(grade)

    return SearchResponse(results=results, count=len(results))


@router.get("/beasts/species/{species}", response_model=SearchResponse)
async def get_beasts_by_species(species: str):
    """종별 괴수 목록"""
    service = get_myeolsal_service()
    results = await service.get_beasts_by_species(species)

    return SearchResponse(results=results, count=len(results))


@router.post("/beasts/generate")
async def generate_beast(request: GenerateBeastRequest):
    """
    새로운 괴수 생성

    세계관 규칙에 맞는 새로운 괴수를 생성합니다.
    """
    service = get_myeolsal_service()
    result = await service.generate_beast(
        concept=request.concept,
        grade=request.grade,
        species=request.species,
        save=request.save
    )

    return result


@router.delete("/beasts/{beast_id}")
async def delete_beast(beast_id: str):
    """괴수 삭제"""
    service = get_myeolsal_service()
    success = await service.delete_beast(beast_id)

    if not success:
        raise HTTPException(status_code=404, detail="괴수를 찾을 수 없습니다")

    return {"deleted": beast_id}


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """저장소 통계"""
    service = get_myeolsal_service()
    return service.get_stats()


@router.get("/rules")
async def get_rules():
    """멸살법 규칙 조회"""
    service = get_myeolsal_service()
    return service.get_rules()


@router.get("/graph")
async def get_graph(limit: int = Query(default=100, ge=1, le=500)):
    """괴수 관계 그래프 조회 (시각화용)"""
    service = get_myeolsal_service()
    return await service.get_graph(limit)


@router.post("/initialize")
async def initialize():
    """서비스 초기화"""
    service = get_myeolsal_service()
    return await service.initialize()


@router.post("/seed")
async def load_seed_data(force: bool = Query(default=False, description="기존 데이터 삭제 후 재로드")):
    """
    시드 데이터 로드

    - force=False (기본): 새로운 데이터만 추가 (기존 데이터 유지)
    - force=True: 기존 데이터 삭제 후 전체 재로드
    """
    from pathlib import Path

    service = get_myeolsal_service()
    data_dir = Path(__file__).parent.parent / "data"

    return await service.load_seed_data(data_dir, force=force)
