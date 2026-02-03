from abc import ABC, abstractmethod

from domain.world.model import GameState


class IGameService(ABC):
    @abstractmethod
    async def create_session(self) -> GameState:
        """새 게임 세션 생성"""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> GameState | None:
        """세션 조회"""
        pass

    @abstractmethod
    async def play(
        self, session_id: str, user_input: str
    ) -> tuple[GameState, str, list[str]]:
        """플레이어 입력 처리 후 결과 반환 (상태, 응답, 선택지)"""
        pass
