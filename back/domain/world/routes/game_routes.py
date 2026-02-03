from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from domain.world.container import get_game_service
from domain.world.interface import IGameService
from domain.world.model import GameState

router = APIRouter(prefix="/game", tags=["game"])


class PlayRequest(BaseModel):
    session_id: str
    input: str


class PlayResponse(BaseModel):
    state: GameState
    response: str
    choices: list[str] = []


class SessionResponse(BaseModel):
    session_id: str
    message: str
    state: GameState
    choices: list[str] = []


OPENING_MESSAGE = """뒤를 돌아본다.

지평선이 사라졌다.
거대한 붉은 벽이 하늘을 삼키며 다가온다.
모래폭풍.

도망쳐야 한다.

어디로? 앞밖에 없다.
끝없는 붉은 사막.
누군가 말했다. 이 사막 어딘가에 지하 도시가 있다고.
그곳만이 살 길이다.

발밑의 모래가 뜨겁다.
등 뒤의 굉음이 점점 가까워진다.

움직여야 한다. 지금 당장."""


@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    service: IGameService = Depends(get_game_service),
) -> SessionResponse:
    """새 게임 세션 생성"""
    state = await service.create_session()
    return SessionResponse(
        session_id=state.session_id,
        message=OPENING_MESSAGE,
        state=state,
        choices=[
            "앞을 향해 달린다 - 폭풍에서 최대한 멀어진다",
            "주변을 빠르게 훑어본다 - 뭐라도 찾을 수 있을지 모른다",
            "침착하게 방향을 정한다 - 무작정 뛰면 지친다",
        ],
    )


@router.get("/session/{session_id}", response_model=GameState)
async def get_session(
    session_id: str,
    service: IGameService = Depends(get_game_service),
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
    service: IGameService = Depends(get_game_service),
) -> PlayResponse:
    """플레이어 행동 처리"""
    try:
        state, response, choices = await service.play(request.session_id, request.input)
        return PlayResponse(state=state, response=response, choices=choices)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
