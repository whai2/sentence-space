import uuid

from domain.orv.model import GameState


class ORVGameRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, GameState] = {}

    async def create(self) -> GameState:
        """새 게임 상태 생성"""
        session_id = str(uuid.uuid4())
        state = GameState(session_id=session_id)
        self._sessions[session_id] = state
        return state

    async def get(self, session_id: str) -> GameState | None:
        """세션 조회"""
        return self._sessions.get(session_id)

    async def update(self, state: GameState) -> None:
        """상태 업데이트"""
        self._sessions[state.session_id] = state

    async def delete(self, session_id: str) -> None:
        """세션 삭제"""
        if session_id in self._sessions:
            del self._sessions[session_id]
