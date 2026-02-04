"""
ORV 게임 서비스

멀티 에이전트 시스템을 활용한 게임 서비스.
DirectorAgent가 전체 이야기를 관장하고, NPCAgent들이 개별 의사결정을 수행합니다.
StoryManager가 장기 스토리 아크와 복선을 관리합니다.
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler

from domain.orv.interface import IORVGameService
from domain.orv.model.state import GameState
from domain.orv.repository.game_repository import ORVGameRepository
from domain.orv.memory.store import MemoryManager
from domain.orv.memory.persistence import SessionPersistence
from domain.orv.service.orchestrator import GameOrchestrator
from domain.orv.story.manager import StoryManager


class ORVGameService(IORVGameService):
    """
    멀티 에이전트 기반 ORV 게임 서비스.

    특징:
    - DirectorAgent가 전체 서사 관장
    - NPCAgent들이 개별 의사결정
    - 키워드 기반 기억 검색
    - JSON 파일 영속성
    - StoryManager가 3막 구조, 긴장 곡선, 복선/회수 관리
    """

    def __init__(
        self,
        repository: ORVGameRepository,
        openrouter_api_key: str,
        model_name: str = "anthropic/claude-3.5-sonnet",
        data_dir: str = "data",
        story_manager: Optional[StoryManager] = None,
        langfuse_public_key: str = "",
        langfuse_secret_key: str = "",
        langfuse_host: str = "https://cloud.langfuse.com",
        langfuse_enabled: bool = True,
    ) -> None:
        self._repository = repository

        # Langfuse 콜백 핸들러 설정 (비용 추적)
        # Langfuse v3는 환경변수에서 설정을 읽음
        callbacks = []
        if langfuse_enabled and langfuse_public_key and langfuse_secret_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = langfuse_secret_key
            os.environ["LANGFUSE_HOST"] = langfuse_host
            self._langfuse_handler = LangfuseCallbackHandler()
            callbacks.append(self._langfuse_handler)
        else:
            self._langfuse_handler = None

        self._llm = ChatOpenAI(
            model=model_name,
            openai_api_key=openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            callbacks=callbacks if callbacks else None,
        )

        # 스토리 매니저 (공유)
        self._story_manager = story_manager or StoryManager()

        # 세션별 오케스트레이터 캐시
        self._orchestrators: dict[str, GameOrchestrator] = {}

        # 영속성 관리자
        self._persistence = SessionPersistence(data_dir)

    def _get_orchestrator(self, session_id: str) -> GameOrchestrator:
        """세션별 오케스트레이터 조회 또는 생성"""
        if session_id not in self._orchestrators:
            memory_manager = MemoryManager()

            # 기존 기억 로드 시도
            _, memory_stores = self._persistence.load_session(session_id)
            if memory_stores:
                memory_manager.load_stores(memory_stores)

            self._orchestrators[session_id] = GameOrchestrator(
                llm=self._llm,
                memory_manager=memory_manager,
                persistence=self._persistence,
                story_manager=self._story_manager,
            )

        return self._orchestrators[session_id]

    async def create_session(self) -> GameState:
        """새 게임 세션 생성"""
        game_state = await self._repository.create()

        # 오케스트레이터 초기화
        self._get_orchestrator(game_state.session_id)

        return game_state

    async def generate_opening_message(self, session_id: str) -> str:
        """도깨비가 생성하는 시나리오 오프닝 메시지"""
        game_state = await self._repository.get(session_id)
        if game_state is None:
            raise ValueError(f"Session not found: {session_id}")

        orchestrator = self._get_orchestrator(session_id)

        # 첫 번째 시나리오 가져오기
        scenario = orchestrator.knowledge.scenarios[0]

        # 도깨비가 오프닝 메시지 생성
        opening = await orchestrator.dokkaebi.generate_scenario_opening(
            scenario=scenario,
            game_state=game_state,
        )

        return opening

    async def get_session(self, session_id: str) -> GameState | None:
        """게임 세션 조회"""
        # 먼저 인메모리에서 조회
        game_state = await self._repository.get(session_id)

        # 없으면 영속성 저장소에서 로드
        if game_state is None:
            game_state_dict, memory_stores = self._persistence.load_session(session_id)
            if game_state_dict:
                game_state = GameState.model_validate(game_state_dict)
                await self._repository.update(game_state)

                # 메모리도 로드
                orchestrator = self._get_orchestrator(session_id)
                if memory_stores:
                    orchestrator.memory_manager.load_stores(memory_stores)

        return game_state

    async def play(
        self,
        session_id: str,
        user_input: str,
    ) -> tuple[GameState, str, list[str]]:
        """
        플레이어 행동 처리.

        Returns:
            (업데이트된 GameState, GM 응답, 선택지 목록)
        """
        game_state = await self._repository.get(session_id)
        if game_state is None:
            raise ValueError(f"Session not found: {session_id}")

        if game_state.game_over:
            if game_state.scenario_cleared:
                return (
                    game_state,
                    "[시스템: 시나리오 클리어]\n\n플랫폼에 발을 디뎠다. 살았다. 적어도, 지금은.",
                    [],
                )
            if game_state.player.health <= 0:
                return (
                    game_state,
                    "[시스템: 사망]\n\n시야가 어두워진다. 마지막으로 본 것은 푸른 빛의 시스템 창이었다.",
                    [],
                )
            return game_state, "게임이 종료되었습니다.", []

        # 오케스트레이터로 턴 실행
        orchestrator = self._get_orchestrator(session_id)
        updated_state, response, choices = await orchestrator.run(
            game_state=game_state,
            player_action=user_input,
            message_history=game_state.message_history,
        )

        # 히스토리 업데이트
        updated_state.message_history.append({"role": "user", "content": user_input})
        updated_state.message_history.append({"role": "assistant", "content": response})

        # 저장
        await self._repository.update(updated_state)

        return updated_state, response, choices

    async def delete_session(self, session_id: str) -> None:
        """세션 삭제"""
        await self._repository.delete(session_id)
        self._persistence.delete_session(session_id)

        if session_id in self._orchestrators:
            del self._orchestrators[session_id]

    def list_saved_sessions(self) -> list[str]:
        """저장된 세션 목록"""
        return self._persistence.list_sessions()
