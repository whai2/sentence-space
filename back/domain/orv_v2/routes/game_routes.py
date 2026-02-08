"""
ORV v2 API Routes

FastAPI 라우트
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from domain.orv_v2.service import ORVGameService
from domain.orv_v2.container import get_game_service


router = APIRouter(prefix="/orv/v2", tags=["ORV v2"])


# ============================================
# Request/Response Models
# ============================================

class CreateSessionResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    player_name: str
    scenario: str | None
    message: str


class ActionRequest(BaseModel):
    """행동 요청"""
    action: str


class ActionResponse(BaseModel):
    """행동 응답"""
    success: bool
    narrative: str
    choices: list[str]
    scene_mood: str | None = None
    game_state: dict | None = None
    error: str | None = None
    game_mode: str | None = None
    mode_changed: bool | None = None


class SessionInfoResponse(BaseModel):
    """세션 정보 응답"""
    session_id: str
    turn: int
    player: dict
    scenario: dict | None
    game_over: bool


# ============================================
# Routes
# ============================================

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    service: ORVGameService = Depends(get_game_service),
):
    """
    새 게임 세션 생성

    지하철 3호선 시나리오로 시작
    """
    result = await service.create_session()
    return result


@router.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session(
    session_id: str,
    service: ORVGameService = Depends(get_game_service),
):
    """
    세션 정보 조회

    Args:
        session_id: 세션 ID
    """
    result = await service.get_session(session_id)

    if not result:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    return result


@router.post("/sessions/{session_id}/continue", response_model=ActionResponse)
async def continue_auto_narrative(
    session_id: str,
    service: ORVGameService = Depends(get_game_service),
):
    """
    자동 스토리 진행 ("진행하기" 버튼)

    Auto-Narrative 모드에서만 사용

    Args:
        session_id: 세션 ID

    Returns:
        자동 생성된 턴 결과
    """
    logger.info(f"📥 [API] POST /sessions/{session_id}/continue 호출됨")
    try:
        result = await service.continue_auto_narrative(session_id)
        logger.info(f"📤 [API] 응답 성공: success={result.get('success', False)}")
        return ActionResponse(**result)
    except Exception as e:
        logger.error(f"❌ [API] 에러 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/actions", response_model=ActionResponse)
async def process_action(
    session_id: str,
    request: ActionRequest,
    service: ORVGameService = Depends(get_game_service),
):
    """
    플레이어 행동 처리 (Interactive 모드)

    Args:
        session_id: 세션 ID
        request: 행동 요청

    Returns:
        서술, 선택지, 상태 등
    """
    logger.info(f"📥 [API] POST /sessions/{session_id}/actions 호출됨")
    logger.info(f"   - 행동: {request.action[:100]}...")
    try:
        result = await service.process_action(
            session_id=session_id,
            player_action=request.action,
        )

        logger.info(f"📤 [API] 응답 성공: success={result.get('success', False)}")
        return ActionResponse(**result)

    except Exception as e:
        logger.error(f"❌ [API] 에러 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    service: ORVGameService = Depends(get_game_service),
):
    """
    세션 삭제

    Args:
        session_id: 세션 ID
    """
    await service.delete_session(session_id)
    return {"message": "세션이 삭제되었습니다"}


@router.get("/sessions/{session_id}/logs")
async def get_state_log(
    session_id: str,
    limit: int = 10,
    service: ORVGameService = Depends(get_game_service),
):
    """
    상태 변경 로그 조회 (디버깅용)

    Args:
        session_id: 세션 ID
        limit: 조회 개수
    """
    logs = await service.get_state_log(session_id, limit)
    return {"logs": logs}
