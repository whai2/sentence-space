from uuid import uuid4

from domain.world.model import GameState, PlayerState


class GameRepository:
    """게임 상태 저장소 (인메모리)"""

    def __init__(self) -> None:
        self._sessions: dict[str, GameState] = {}

    async def create(self) -> GameState:
        session_id = str(uuid4())
        state = GameState(
            session_id=session_id,
            player=PlayerState(),
        )
        self._sessions[session_id] = state
        return state

    async def get(self, session_id: str) -> GameState | None:
        return self._sessions.get(session_id)

    async def update(self, state: GameState) -> GameState:
        self._sessions[state.session_id] = state
        return state

    async def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
