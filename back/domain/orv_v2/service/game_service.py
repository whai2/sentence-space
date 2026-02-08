"""
ORV v2 게임 서비스

GameWorkflow를 래핑하고 비즈니스 로직 제공
"""
import logging
from domain.orv_v2.models import GameState, GameMode
from domain.orv_v2.graph import GameWorkflow
from domain.orv_v2.repository import MongoDBGameRepository

logger = logging.getLogger(__name__)


class ORVGameService:
    """
    ORV v2 게임 서비스

    API 레이어와 워크플로우 사이의 비즈니스 로직
    """

    def __init__(
        self,
        workflow: GameWorkflow,
        repository: MongoDBGameRepository,
    ):
        self.workflow = workflow
        self.repository = repository

    async def create_session(self) -> dict:
        """
        새 게임 세션 생성

        Returns:
            세션 정보
        """
        game_state = await self.repository.create_session()

        # 초기 NPC 스폰 (예시: 3호선 객차에 학생 2명)
        from domain.orv_v2.models import NPCState, Coordinate, NPCPersonality, NPCRelationship
        import uuid

        # 학생 1
        student1 = NPCState(
            npc_id=str(uuid.uuid4()),
            name="이름 없는 학생",
            npc_type="student",
            description="겁에 질린 대학생",
            position="3호선_객차_3",
            coordinates=Coordinate(lat=37.5030, lng=127.0246),
            health=50,
            max_health=50,
            personality=NPCPersonality(bravery=20, aggression=10, empathy=70),
            relationship=NPCRelationship(),
        )

        # 학생 2
        student2 = NPCState(
            npc_id=str(uuid.uuid4()),
            name="이름 없는 학생",
            npc_type="student",
            description="불안해하는 여대생",
            position="3호선_객차_3",
            coordinates=Coordinate(lat=37.5030, lng=127.0246),
            health=40,
            max_health=40,
            personality=NPCPersonality(bravery=15, aggression=5, empathy=80),
            relationship=NPCRelationship(),
        )

        # NPC 저장
        await self.repository.save_npc(game_state.session_id, student1)
        await self.repository.save_npc(game_state.session_id, student2)

        # 시나리오 1 시작
        from domain.orv_v2.models import CurrentScenario
        game_state.current_scenario = CurrentScenario(
            scenario_id="scenario_1",
            title="지하철 3호선 - 생존 적합성 테스트",
            status="active",
            remaining_time=15,
            progress="시나리오 시작",
        )

        await self.repository.save_game_state(game_state)

        return {
            "session_id": game_state.session_id,
            "player_name": game_state.player.name,
            "scenario": game_state.current_scenario.title if game_state.current_scenario else None,
            "message": "게임이 시작되었습니다. 지하철 3호선 안, 갑자기 멈춘 지하철...",
        }

    async def get_session(self, session_id: str) -> dict | None:
        """
        세션 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 또는 None
        """
        game_state = await self.repository.load_game_state(session_id)

        if not game_state:
            return None

        return {
            "session_id": game_state.session_id,
            "turn": game_state.turn_count,
            "player": {
                "name": game_state.player.name,
                "level": game_state.player.level,
                "health": game_state.player.health,
                "max_health": game_state.player.max_health,
                "coins": game_state.player.coins,
                "position": game_state.player.position,
            },
            "scenario": {
                "title": game_state.current_scenario.title if game_state.current_scenario else None,
                "status": game_state.current_scenario.status if game_state.current_scenario else None,
                "remaining_time": game_state.current_scenario.remaining_time if game_state.current_scenario else None,
            } if game_state.current_scenario else None,
            "game_over": game_state.game_over,
        }

    async def process_action(
        self,
        session_id: str,
        player_action: str,
    ) -> dict:
        """
        플레이어 행동 처리

        Args:
            session_id: 세션 ID
            player_action: 플레이어 행동

        Returns:
            턴 결과
        """
        logger.info(f"🎮 [GameService] 플레이어 행동 처리: session_id={session_id}")
        logger.info(f"   - 행동: {player_action[:100]}...")

        # Workflow 실행
        result = await self.workflow.run_turn(
            session_id=session_id,
            player_action=player_action,
        )

        logger.info(f"✅ [GameService] 행동 처리 완료: success={result.get('success', False)}")

        return result

    async def continue_auto_narrative(self, session_id: str) -> dict:
        """
        자동 스토리 진행 (진행하기 버튼)

        Args:
            session_id: 세션 ID

        Returns:
            턴 결과
        """
        logger.info(f"🤖 [GameService] Auto-Narrative 진행: session_id={session_id}")

        # 게임 상태 확인
        game_state = await self.repository.load_game_state(session_id)

        if not game_state:
            logger.warning(f"⚠️  [GameService] 세션을 찾을 수 없음: session_id={session_id}")
            return {
                "success": False,
                "error": "세션을 찾을 수 없습니다",
            }

        if game_state.game_mode != GameMode.AUTO_NARRATIVE:
            logger.warning(f"⚠️  [GameService] Auto-Narrative 모드가 아님: mode={game_state.game_mode.value}")
            return {
                "success": False,
                "error": "Auto-Narrative 모드가 아닙니다",
            }

        logger.info(f"   - 턴: {game_state.turn_count}, 현재 시나리오: {game_state.current_scenario.scenario_id if game_state.current_scenario else 'None'}")

        # Workflow 실행 (player_action=None)
        result = await self.workflow.run_turn(
            session_id=session_id,
            player_action=None,
        )

        logger.info(f"✅ [GameService] Auto-Narrative 완료: success={result.get('success', False)}")

        return result

    async def delete_session(self, session_id: str):
        """
        세션 삭제

        Args:
            session_id: 세션 ID
        """
        await self.repository.delete_session(session_id)

    async def get_state_log(self, session_id: str, limit: int = 10) -> list[dict]:
        """
        상태 변경 로그 조회 (디버깅용)

        Args:
            session_id: 세션 ID
            limit: 조회 개수

        Returns:
            상태 변경 로그
        """
        return await self.repository.get_state_change_log(session_id, limit)
