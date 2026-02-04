from abc import ABC, abstractmethod

from domain.orv.model import GameState


class IORVGameService(ABC):
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
        """플레이어 행동 처리"""
        pass

    @abstractmethod
    async def generate_opening_message(self, session_id: str) -> str:
        """도깨비가 생성하는 시나리오 오프닝 메시지"""
        pass
