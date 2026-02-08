"""
MongoDB Repository

게임 상태 영속성 관리
- Motor (비동기 MongoDB 드라이버) 사용
- Transaction 지원
"""
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from domain.orv_v2.models import (
    GameState,
    PlayerState,
    CurrentScenario,
    ScenarioContext,
    ScenarioSummary,
    NPCState,
    StateChange,
)
from domain.orv_v2.models.story_plan import StoryPlan, StoryProgress
from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository


class MongoDBGameRepository:
    """
    MongoDB 기반 게임 저장소

    Collections:
    - game_sessions: 게임 세션 상태
    - npcs: NPC 상태
    - scenario_summaries: 시나리오 요약
    - state_change_log: 상태 변경 로그
    - scenarios: 시나리오 템플릿 (Master Data)
    """

    def __init__(
        self,
        mongodb_uri: str,
        database_name: str = "orv_game",
        neo4j_repo: Neo4jGraphRepository | None = None,
    ):
        """
        Args:
            mongodb_uri: MongoDB 연결 URI
            database_name: 데이터베이스 이름
            neo4j_repo: Neo4j Repository (선택적)
        """
        self.client = AsyncIOMotorClient(mongodb_uri)
        self.db: AsyncIOMotorDatabase = self.client[database_name]
        self.neo4j_repo = neo4j_repo

        # Collections
        self.game_sessions = self.db["game_sessions"]
        self.npcs = self.db["npcs"]
        self.scenario_summaries = self.db["scenario_summaries"]
        self.state_change_log = self.db["state_change_log"]
        self.scenarios = self.db["scenarios"]
        self.story_plans = self.db["story_plans"]  # NEW
        self.story_progress = self.db["story_progress"]  # NEW

    async def create_indexes(self):
        """인덱스 생성 (최초 1회)"""
        # game_sessions
        await self.game_sessions.create_index("session_id", unique=True)
        await self.game_sessions.create_index("updated_at")

        # npcs
        await self.game_sessions.create_index([("session_id", 1), ("npc_id", 1)])
        await self.npcs.create_index([("session_id", 1), ("is_alive", 1)])

        # scenario_summaries
        await self.scenario_summaries.create_index([("session_id", 1), ("scenario_id", 1)])

        # state_change_log
        await self.state_change_log.create_index([("session_id", 1), ("turn", 1)])

    # ============================================
    # Game Session CRUD
    # ============================================

    async def create_session(self) -> GameState:
        """새 게임 세션 생성"""
        session_id = str(uuid.uuid4())

        game_state = GameState(
            session_id=session_id,
            player=PlayerState(),
            turn_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # MongoDB에 저장
        await self.game_sessions.insert_one(game_state.model_dump())

        return game_state

    async def load_game_state(self, session_id: str) -> GameState | None:
        """게임 상태 로드"""
        doc = await self.game_sessions.find_one({"session_id": session_id})

        if not doc:
            return None

        # MongoDB _id 제거
        doc.pop("_id", None)

        # Migration: 기존 세션에 game_mode, scenario_phase 필드 추가
        if "game_mode" not in doc:
            doc["game_mode"] = "auto_narrative"
        if "scenario_phase" not in doc:
            doc["scenario_phase"] = None

        return GameState(**doc)

    async def save_game_state(self, game_state: GameState):
        """게임 상태 저장 (upsert)"""
        game_state.updated_at = datetime.utcnow()

        await self.game_sessions.update_one(
            {"session_id": game_state.session_id},
            {"$set": game_state.model_dump()},
            upsert=True,
        )

    async def delete_session(self, session_id: str):
        """세션 삭제 (모든 관련 데이터)"""
        # Transaction 사용
        async with await self.client.start_session() as session:
            async with session.start_transaction():
                await self.game_sessions.delete_one(
                    {"session_id": session_id}, session=session
                )
                await self.npcs.delete_many(
                    {"session_id": session_id}, session=session
                )
                await self.scenario_summaries.delete_many(
                    {"session_id": session_id}, session=session
                )
                await self.state_change_log.delete_many(
                    {"session_id": session_id}, session=session
                )

    # ============================================
    # NPC 관리
    # ============================================

    async def save_npc(self, session_id: str, npc: NPCState):
        """NPC 저장"""
        doc = npc.model_dump()
        doc["session_id"] = session_id

        await self.npcs.update_one(
            {"session_id": session_id, "npc_id": npc.npc_id},
            {"$set": doc},
            upsert=True,
        )

    async def load_npcs(self, session_id: str) -> list[NPCState]:
        """세션의 모든 NPC 로드"""
        cursor = self.npcs.find({"session_id": session_id})
        docs = await cursor.to_list(length=100)

        npcs = []
        for doc in docs:
            doc.pop("_id", None)
            doc.pop("session_id", None)
            npcs.append(NPCState(**doc))

        return npcs

    async def load_npc(self, session_id: str, npc_id: str) -> NPCState | None:
        """특정 NPC 로드"""
        doc = await self.npcs.find_one({"session_id": session_id, "npc_id": npc_id})

        if not doc:
            return None

        doc.pop("_id", None)
        doc.pop("session_id", None)

        return NPCState(**doc)

    # ============================================
    # 시나리오 요약
    # ============================================

    async def save_scenario_summary(self, summary: ScenarioSummary):
        """시나리오 요약 저장"""
        await self.scenario_summaries.insert_one(summary.model_dump())

    async def load_scenario_summaries(self, session_id: str) -> list[ScenarioSummary]:
        """세션의 모든 시나리오 요약 로드"""
        cursor = self.scenario_summaries.find(
            {"session_id": session_id}
        ).sort("turn_start", 1)

        docs = await cursor.to_list(length=100)

        summaries = []
        for doc in docs:
            doc.pop("_id", None)
            summaries.append(ScenarioSummary(**doc))

        return summaries

    # ============================================
    # 시나리오 컨텍스트 (게임 상태 + 요약 통합)
    # ============================================

    async def load_scenario_context(self, session_id: str) -> ScenarioContext | None:
        """시나리오 컨텍스트 로드"""
        game_state = await self.load_game_state(session_id)

        if not game_state or not game_state.current_scenario:
            return None

        # 이전 시나리오 요약들
        previous_summaries = await self.load_scenario_summaries(session_id)

        # 현재 시나리오 템플릿 (Master Data)
        scenario_template = await self.scenarios.find_one(
            {"scenario_id": game_state.current_scenario.scenario_id}
        )

        if not scenario_template:
            return None

        return ScenarioContext(
            scenario_id=game_state.current_scenario.scenario_id,
            title=game_state.current_scenario.title,
            objective=scenario_template.get("objective", ""),
            difficulty=scenario_template.get("difficulty", "D급"),
            remaining_time=game_state.current_scenario.remaining_time,
            current_phase=None,  # TODO: 단계 추적 구현
            previous_summaries=previous_summaries,
        )

    # ============================================
    # 상태 변경 로그
    # ============================================

    async def log_state_change(
        self,
        session_id: str,
        turn: int,
        changes: StateChange,
        narrative: str,
    ):
        """상태 변경 로그 저장 (작붕 추적)"""
        log = {
            "session_id": session_id,
            "turn": turn,
            "narrative": narrative,
            "changes": changes.model_dump(),
            "timestamp": datetime.utcnow(),
        }

        await self.state_change_log.insert_one(log)

    async def get_state_change_log(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """상태 변경 로그 조회"""
        cursor = self.state_change_log.find(
            {"session_id": session_id}
        ).sort("turn", -1).limit(limit)

        return await cursor.to_list(length=limit)

    # ============================================
    # Transaction 지원
    # ============================================

    async def execute_transaction(self, operations: list):
        """
        MongoDB Transaction 실행

        여러 작업을 원자적으로 처리

        Example:
            await repo.execute_transaction([
                ("update", "game_sessions", {"session_id": "..."}, {"$set": {...}}),
                ("insert", "state_change_log", {...}),
            ])
        """
        async with await self.client.start_session() as session:
            async with session.start_transaction():
                for op_type, collection_name, *args in operations:
                    collection = self.db[collection_name]

                    if op_type == "update":
                        filter_doc, update_doc = args
                        await collection.update_one(
                            filter_doc, update_doc, session=session
                        )
                    elif op_type == "insert":
                        doc = args[0]
                        await collection.insert_one(doc, session=session)
                    elif op_type == "delete":
                        filter_doc = args[0]
                        await collection.delete_one(filter_doc, session=session)

    # ============================================
    # Story Plan & Progress (Plan-and-Execute)
    # ============================================

    async def load_story_plan(self, session_id: str) -> StoryPlan | None:
        """스토리 플랜 로드"""
        doc = await self.story_plans.find_one({"session_id": session_id})

        if not doc:
            return None

        doc.pop("_id", None)
        return StoryPlan(**doc)

    async def save_story_plan(self, story_plan: StoryPlan):
        """스토리 플랜 저장"""
        await self.story_plans.update_one(
            {"session_id": story_plan.session_id},
            {"$set": story_plan.model_dump()},
            upsert=True,
        )

    async def load_story_progress(self, session_id: str) -> StoryProgress | None:
        """스토리 진행 상황 로드"""
        doc = await self.story_progress.find_one({"session_id": session_id})

        if not doc:
            return None

        doc.pop("_id", None)
        return StoryProgress(**doc)

    async def save_story_progress(self, session_id: str, progress: StoryProgress):
        """스토리 진행 상황 저장"""
        doc = progress.model_dump()
        doc["session_id"] = session_id

        await self.story_progress.update_one(
            {"session_id": session_id},
            {"$set": doc},
            upsert=True,
        )

    async def get_scenario_from_neo4j(self, scenario_id: str) -> dict:
        """
        Neo4j에서 시나리오 상세 정보 조회

        Returns:
            시나리오 전체 데이터 (phases, characters, events, tricks 등)
        """
        if not self.neo4j_repo:
            raise ValueError("Neo4j Repository가 설정되지 않았습니다")

        # Neo4j에서 전체 컨텍스트 조회
        data = await self.neo4j_repo.get_scenario_full_context(scenario_id)

        if not data:
            raise ValueError(f"시나리오를 찾을 수 없습니다: {scenario_id}")

        # Phase 목록 조회
        phases_query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})-[:HAS_PHASE]->(p:Phase)
        RETURN p
        ORDER BY p.order
        """
        phases_result = await self.neo4j_repo.execute_query(
            phases_query,
            {"scenario_id": scenario_id}
        )

        # Event 목록 조회
        events_query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})-[:HAS_PHASE]->(p:Phase)-[:CONTAINS_EVENT]->(e:Event)
        RETURN e, p.phase_id as phase_id
        ORDER BY p.order, e.event_id
        """
        events_result = await self.neo4j_repo.execute_query(
            events_query,
            {"scenario_id": scenario_id}
        )

        # Character 목록 조회
        characters_query = """
        MATCH (s:Scenario {scenario_id: $scenario_id})-[:HAS_CHARACTER]->(c:Character)
        RETURN c
        """
        characters_result = await self.neo4j_repo.execute_query(
            characters_query,
            {"scenario_id": scenario_id}
        )

        # Trick 목록 조회
        tricks_result = await self.neo4j_repo.get_protagonist_tricks(scenario_id)

        return {
            "s": data.get("s", {}),
            "phases": [r["p"] for r in phases_result],
            "events": events_result,
            "characters": [r["c"] for r in characters_result],
            "protagonist_tricks": tricks_result,
        }

    # ============================================
    # Utility
    # ============================================

    async def close(self):
        """연결 종료"""
        self.client.close()
