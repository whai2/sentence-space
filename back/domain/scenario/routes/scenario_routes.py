"""
시나리오 설명집 API 라우트

FastAPI 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query

from domain.scenario.container import get_scenario_service


router = APIRouter(prefix="/scenario", tags=["시나리오 설명집"])


# ============================================
# 엔드포인트
# ============================================

@router.get("/list")
async def list_scenarios(
    offset: int = Query(default=0, ge=0, description="오프셋"),
    limit: int = Query(default=50, ge=1, le=100, description="페이지 크기"),
    type: str | None = Query(default=None, description="시나리오 유형 필터 (main, sub, hidden)"),
):
    """시나리오 전체 목록 (페이지네이션)"""
    service = get_scenario_service()
    return await service.list_scenarios_async(
        offset=offset, limit=limit, type_filter=type,
    )


@router.get("/stats")
async def get_stats():
    """시나리오 통계"""
    service = get_scenario_service()
    return await service.get_stats()


@router.get("/graph")
async def get_graph(limit: int = Query(default=100, ge=1, le=500)):
    """시나리오 관계 그래프 (시각화용)"""
    service = get_scenario_service()
    return await service.get_graph(limit)


@router.post("/initialize")
async def initialize():
    """서비스 초기화"""
    service = get_scenario_service()
    return await service.initialize()


@router.post("/seed")
async def load_seed_data(
    force: bool = Query(default=False, description="기존 데이터 삭제 후 재로드")
):
    """시드 데이터 로드"""
    from pathlib import Path

    service = get_scenario_service()
    data_dir = Path(__file__).parent.parent / "data"

    return await service.load_seed_data(data_dir, force=force)


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """시나리오 상세 조회 (연결된 괴수 포함)"""
    service = get_scenario_service()
    result = await service.get_scenario(scenario_id)

    if not result:
        raise HTTPException(status_code=404, detail="시나리오를 찾을 수 없습니다")

    return result
