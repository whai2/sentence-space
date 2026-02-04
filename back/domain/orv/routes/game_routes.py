from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from domain.orv.container import get_orv_game_service
from domain.orv.interface import IORVGameService
from domain.orv.model import GameState

router = APIRouter(prefix="/orv", tags=["orv"])


class PlayRequest(BaseModel):
    session_id: str
    input: str


class PlayResponse(BaseModel):
    state: GameState
    response: str
    choices: list[str] = []
    scenario_completed: bool = False  # True면 채팅 비활성화, "다음 시나리오" 버튼 표시


class SessionResponse(BaseModel):
    session_id: str
    message: str
    state: GameState
    choices: list[str] = []


# 초기 선택지
INITIAL_CHOICES = [
    "주변을 둘러본다 - 상황을 파악해야 한다",
    "저 여성에게 다가간다 - 뭔가 안고 있는 것 같다",
    "시스템 창을 자세히 읽어본다 - 뭔가 힌트가 있을지도",
    "다른 승객들에게 말을 건다 - 정보가 필요하다",
]


@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    service: IORVGameService = Depends(get_orv_game_service),
) -> SessionResponse:
    """새 게임 세션 생성 - 도깨비가 시나리오 오프닝 안내"""
    state = await service.create_session()

    # 도깨비가 오프닝 메시지 생성
    opening_message = await service.generate_opening_message(state.session_id)

    return SessionResponse(
        session_id=state.session_id,
        message=opening_message,
        state=state,
        choices=INITIAL_CHOICES,
    )


@router.get("/session/{session_id}", response_model=GameState)
async def get_session(
    session_id: str,
    service: IORVGameService = Depends(get_orv_game_service),
) -> GameState:
    """게임 세션 조회"""
    state = await service.get_session(session_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return state


@router.post("/play", response_model=PlayResponse)
async def play(
    request: PlayRequest,
    service: IORVGameService = Depends(get_orv_game_service),
) -> PlayResponse:
    """플레이어 행동 처리"""
    try:
        state, response, choices = await service.play(request.session_id, request.input)

        # 시나리오 클리어 확인
        scenario_completed = (
            state.current_scenario is not None
            and state.current_scenario.status == "completed"
        )

        # 클리어 시 선택지 비우기 (프론트에서 "다음 시나리오" 버튼만 표시)
        if scenario_completed:
            choices = []

        return PlayResponse(
            state=state,
            response=response,
            choices=choices,
            scenario_completed=scenario_completed,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
