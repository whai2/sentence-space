"""
LangGraph 워크플로우

Multi-Agent 시스템을 조율하는 워크플로우
- Orchestrator → NPC → Narrator → DB Update
- Auto-Narrator → Orchestrator → DB Update (자동 모드)
"""
import asyncio
import logging
from typing import Literal
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

from domain.orv_v2.models import GraphState, GameState, ScenarioContext, GameMode
from domain.orv_v2.models.story_plan import StoryPlan, StoryProgress
from domain.orv_v2.agents import (
    OrchestratorAgent,
    NarratorAgent,
    NPCAgent,
    NPCDecision,
    AutoNarratorAgent,
    GraphRAGRetriever,
)
from domain.orv_v2.agents.story_planner import StoryPlannerAgent
from domain.orv_v2.agents.story_executor import StoryExecutorAgent


# ============================================
# Repository (임시, 나중에 실제 MongoDB로 교체)
# ============================================

class GameRepository:
    """게임 상태 저장소 (임시 인터페이스)"""

    async def load_game_state(self, session_id: str) -> GameState:
        """게임 상태 로드"""
        raise NotImplementedError

    async def load_scenario_context(self, session_id: str) -> ScenarioContext | None:
        """시나리오 컨텍스트 로드"""
        raise NotImplementedError

    async def load_npcs(self, session_id: str):
        """NPC 목록 로드"""
        raise NotImplementedError

    async def save_game_state(self, game_state: GameState):
        """게임 상태 저장"""
        raise NotImplementedError

    async def log_state_change(self, session_id: str, turn: int, changes, narrative: str):
        """상태 변경 로그 저장"""
        raise NotImplementedError

    async def load_story_plan(self, session_id: str) -> StoryPlan | None:
        """스토리 플랜 로드"""
        raise NotImplementedError

    async def save_story_plan(self, story_plan: StoryPlan):
        """스토리 플랜 저장"""
        raise NotImplementedError

    async def load_story_progress(self, session_id: str) -> StoryProgress | None:
        """스토리 진행 상황 로드"""
        raise NotImplementedError

    async def save_story_progress(self, session_id: str, progress: StoryProgress):
        """스토리 진행 상황 저장"""
        raise NotImplementedError

    async def get_scenario_from_neo4j(self, scenario_id: str) -> dict:
        """Neo4j에서 시나리오 상세 정보 조회"""
        raise NotImplementedError


# ============================================
# LangGraph Nodes
# ============================================

class GameWorkflow:
    """
    게임 워크플로우

    LangGraph 기반 멀티 에이전트 조율
    """

    def __init__(
        self,
        orchestrator: OrchestratorAgent,
        narrator: NarratorAgent,
        npc_agent: NPCAgent,
        auto_narrator: AutoNarratorAgent,
        repository: GameRepository,
        graph_rag_retriever: GraphRAGRetriever | None = None,
        story_planner: StoryPlannerAgent | None = None,
        story_executor: StoryExecutorAgent | None = None,
    ):
        self.orchestrator = orchestrator
        self.narrator = narrator
        self.npc_agent = npc_agent
        self.auto_narrator = auto_narrator
        self.repository = repository
        self.graph_rag_retriever = graph_rag_retriever
        self.story_planner = story_planner
        self.story_executor = story_executor or StoryExecutorAgent()

        # Graph 빌드
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        graph = StateGraph(GraphState)

        # 노드 추가
        graph.add_node("load_state", self._load_state)
        graph.add_node("auto_narrative_node", self._auto_narrative_node)  # NEW
        graph.add_node("orchestrator_node", self._orchestrator_node)
        graph.add_node("validate_node", self._validate_node)
        graph.add_node("npc_phase", self._npc_phase)
        graph.add_node("narrator_node", self._narrator_node)
        graph.add_node("update_state", self._update_state)

        # 엣지 설정
        graph.set_entry_point("load_state")

        # 모드 기반 라우팅 (AUTO vs INTERACTIVE)
        graph.add_conditional_edges(
            "load_state",
            self._route_by_mode,
            {
                "auto": "auto_narrative_node",
                "interactive": "orchestrator_node",
            },
        )

        # Auto-Narrative 경로: auto → update
        graph.add_edge("auto_narrative_node", "update_state")

        # Interactive 경로 (기존)
        graph.add_edge("orchestrator_node", "validate_node")

        # 조건부 엣지: 검증 성공 → npc_phase, 실패 → END
        graph.add_conditional_edges(
            "validate_node",
            self._should_continue,
            {
                "continue": "npc_phase",
                "end": END,
            },
        )

        graph.add_edge("npc_phase", "narrator_node")
        graph.add_edge("narrator_node", "update_state")
        graph.add_edge("update_state", END)

        return graph.compile()

    # ============================================
    # Node Functions
    # ============================================

    async def _load_state(self, state: GraphState) -> GraphState:
        """1. 게임 상태 로드 (MongoDB)"""
        session_id = state["session_id"]
        logger.info(f"🎮 [Workflow] 게임 상태 로드: session_id={session_id}")

        # MongoDB에서 로드
        game_state = await self.repository.load_game_state(session_id)
        scenario_context = await self.repository.load_scenario_context(session_id)

        logger.info(f"   - 게임 모드: {game_state.game_mode.value}, 턴: {game_state.turn_count}")
        if game_state.current_scenario:
            logger.info(f"   - 현재 시나리오: {game_state.current_scenario.scenario_id}")

        state["game_state"] = game_state
        state["scenario_context"] = scenario_context
        state["validation_passed"] = False
        state["validation_error"] = None
        state["system_messages"] = []
        state["error"] = None
        state["retry_count"] = 0

        return state

    async def _orchestrator_node(self, state: GraphState) -> GraphState:
        """2. Orchestrator 판단"""
        player_action = state["player_action"]
        game_state = state["game_state"]
        scenario_context = state.get("scenario_context")

        # Orchestrator 호출
        decision = await self.orchestrator.decide(
            player_action=player_action,
            game_state=game_state,
            scenario_context=scenario_context,
        )

        state["orchestrator_decision"] = decision
        return state

    def _route_by_mode(self, state: GraphState) -> Literal["auto", "interactive"]:
        """
        게임 모드 기반 라우팅

        AUTO_NARRATIVE → auto_narrative_node
        INTERACTIVE → orchestrator_node
        """
        game_state = state["game_state"]
        return "auto" if game_state.game_mode == GameMode.AUTO_NARRATIVE else "interactive"

    async def _auto_narrative_node(self, state: GraphState) -> GraphState:
        """
        자동 스토리 진행 노드 (AUTO_NARRATIVE 모드)

        - Story Plan 확인/생성 (없으면 Planner 호출)
        - Story Executor로 현재 가이던스 생성
        - GraphRAG로 시나리오 지식 검색 (선택적)
        - AutoNarratorAgent가 player_action과 narrative를 모두 생성
        - 시나리오 시작 감지 시 모드 전환 준비
        """
        logger.info(f"🤖 [Workflow] Auto-Narrative 노드 시작")
        game_state = state["game_state"]
        scenario_context = state.get("scenario_context")

        # ============================================
        # 1. Story Plan 확인/생성 (Plan-and-Execute)
        # ============================================
        story_plan = None
        story_progress = None
        story_guidance = None

        if self.story_planner and self.story_executor:
            # Story Plan 로드
            story_plan = await self.repository.load_story_plan(game_state.session_id)

            # Story Plan이 없으면 생성 (시나리오 시작 시)
            if not story_plan and game_state.current_scenario:
                try:
                    logger.info(f"📖 [Workflow] 스토리 플랜 생성 시작: scenario_id={game_state.current_scenario.scenario_id}")
                    # Neo4j에서 시나리오 상세 정보 조회
                    logger.info(f"🔍 [Workflow] Neo4j에서 시나리오 데이터 조회 중...")
                    scenario_data = await self.repository.get_scenario_from_neo4j(
                        game_state.current_scenario.scenario_id
                    )

                    # Planner로 전체 스토리 플랜 생성
                    logger.info(f"📋 [Workflow] StoryPlanner 호출...")
                    planner_output = await self.story_planner.create_story_plan(
                        scenario_id=game_state.current_scenario.scenario_id,
                        scenario_data=scenario_data,
                        game_state=game_state
                    )

                    story_plan = planner_output.story_plan

                    # Phases 검증
                    if not story_plan.phases:
                        logger.warning(f"⚠️  [Workflow] 스토리 플랜이 비어있습니다 (Haiku 생성 실패). StoryPlanner 없이 진행합니다.")
                        story_plan = None
                    else:
                        await self.repository.save_story_plan(story_plan)

                        # 초기 Progress 생성
                        story_progress = StoryProgress(
                            current_phase_id=story_plan.phases[0].phase_id,
                            current_phase_name=story_plan.phases[0].phase_name,
                            current_turn=game_state.turn_count,
                            completed_events=[],
                            next_event=story_plan.phases[0].events[0] if story_plan.phases[0].events else None,
                            deviation_level=0
                        )
                        await self.repository.save_story_progress(game_state.session_id, story_progress)

                        logger.info(f"✅ [Workflow] 스토리 플랜 생성 완료: {len(story_plan.phases)}개 페이즈")
                except Exception as e:
                    logger.error(f"❌ [Workflow] 스토리 플랜 생성 실패: {e}", exc_info=True)

            # Story Progress 로드
            if story_plan:
                story_progress = await self.repository.load_story_progress(game_state.session_id)

                if story_progress:
                    # Executor로 현재 가이던스 생성
                    executor_guidance = self.story_executor.get_current_guidance(
                        story_plan=story_plan,
                        story_progress=story_progress,
                        game_state=game_state
                    )

                    story_guidance = executor_guidance.narrative_guidance
                    print(f"📍 현재 단계: {executor_guidance.current_phase.phase_name}")

        # ============================================
        # 2. 최근 히스토리 가져오기
        # ============================================
        recent_logs = await self.repository.get_state_change_log(
            game_state.session_id, limit=3
        )
        recent_history = "\n".join([
            f"턴 {log['turn']}: {log['narrative'][:100]}..."
            for log in reversed(recent_logs)
        ]) if recent_logs else "게임 시작"

        # ============================================
        # 3. GraphRAG로 강화된 컨텍스트 조회 (선택적)
        # ============================================
        enriched_context = None
        if self.graph_rag_retriever and game_state.current_scenario:
            try:
                logger.info(f"🔍 [Workflow] GraphRAG 호출: scenario_id={game_state.current_scenario.scenario_id}")
                enriched_context = await self.graph_rag_retriever.retrieve_scenario_knowledge(
                    scenario_id=game_state.current_scenario.scenario_id,
                    remaining_time=scenario_context.remaining_time if scenario_context else None,
                    current_phase=scenario_context.current_phase if scenario_context else None,
                )
                logger.info(f"✅ [Workflow] GraphRAG 컨텍스트 조회 완료")
            except Exception as e:
                # GraphRAG 실패 시 기본 컨텍스트 사용 (graceful degradation)
                logger.warning(f"⚠️  [Workflow] GraphRAG 조회 실패 (기본 컨텍스트 사용): {e}", exc_info=True)
        else:
            if not self.graph_rag_retriever:
                logger.info(f"ℹ️  [Workflow] GraphRAG retriever가 설정되지 않음")
            elif not game_state.current_scenario:
                logger.info(f"ℹ️  [Workflow] 현재 시나리오가 없음 (GraphRAG 스킵)")

        # ============================================
        # 4. AutoNarrator 호출 (Story Guidance 포함)
        # ============================================
        auto_output = await self.auto_narrator.generate_turn(
            game_state=game_state,
            scenario_context=scenario_context,
            recent_history=recent_history,
            enriched_context=enriched_context,
            story_guidance=story_guidance,  # NEW: Story Plan 가이던스
        )

        # player_action 저장
        state["player_action"] = auto_output.player_action

        # AUTO 모드에서는 Orchestrator 호출 생략 (성능 최적화)
        # 빈 StateChange 사용 (상태 변경은 AutoNarrator의 서술에 맡김)
        from domain.orv_v2.models import StateChange
        state["applied_changes"] = StateChange()
        state["validation_passed"] = True
        state["orchestrator_decision"] = None  # AUTO 모드에서는 None

        # AutoNarrator의 narrative 사용 (NarratorAgent 대신)
        from domain.orv_v2.models import NarratorOutput
        state["narrator_output"] = NarratorOutput(
            narrative=auto_output.narrative,
            scene_mood=auto_output.scene_mood,
            npc_reactions=[],
            suggested_choices=auto_output.initial_choices if auto_output.scenario_starting else [],
        )

        # 시나리오 시작 감지 시 모드 전환 플래그
        if auto_output.scenario_starting:
            state["mode_transition"] = "to_interactive"
            state["initial_choices"] = auto_output.initial_choices

        return state

    async def _validate_node(self, state: GraphState) -> GraphState:
        """3. 개연성 재검증"""
        decision = state["orchestrator_decision"]
        game_state = state["game_state"]

        # Orchestrator가 이미 판단했지만, 한번 더 체크 (이중 안전장치)
        if not decision.is_action_valid:
            state["validation_passed"] = False
            state["validation_error"] = decision.validation_reason
            return state

        # 코드 레벨 검증
        is_valid, error = self.orchestrator.validate_state_changes(
            changes=decision.state_changes,
            game_state=game_state,
        )

        state["validation_passed"] = is_valid
        state["validation_error"] = error

        if is_valid:
            state["applied_changes"] = decision.state_changes

        return state

    def _should_continue(self, state: GraphState) -> Literal["continue", "end"]:
        """조건부 엣지: 검증 성공 여부"""
        return "continue" if state["validation_passed"] else "end"

    async def _npc_phase(self, state: GraphState) -> GraphState:
        """4. NPC 의사결정 (활성화된 NPC들)"""
        game_state = state["game_state"]
        player_action = state["player_action"]

        # 현재 위치의 살아있는 NPC들
        npcs = await self.repository.load_npcs(game_state.session_id)
        active_npcs = [
            npc for npc in npcs
            if npc.position == game_state.player.position and npc.is_alive
        ]

        # 최대 3명까지만 활성화 (비용 절감)
        active_npcs = active_npcs[:3]

        if not active_npcs:
            state["npc_reactions"] = []
            return state

        # 병렬로 NPC 의사결정 처리
        tasks = [
            self.npc_agent.decide(
                npc=npc,
                player_action=player_action,
                game_state=game_state,
            )
            for npc in active_npcs
        ]

        npc_decisions: list[NPCDecision] = await asyncio.gather(*tasks)

        # NPC 반응 요약 (Narrator에게 전달)
        npc_reactions = []
        for decision in npc_decisions:
            reaction = f"{decision.npc_name}: {decision.action_description}"
            if decision.dialogue:
                reaction += f' - "{decision.dialogue}"'
            npc_reactions.append(reaction)

        state["npc_reactions"] = npc_reactions
        return state

    async def _narrator_node(self, state: GraphState) -> GraphState:
        """5. 서술 생성"""
        player_action = state["player_action"]
        game_state = state["game_state"]
        orchestrator_decision = state["orchestrator_decision"]
        npc_reactions = state.get("npc_reactions", [])

        # Narrator 호출
        narrator_output = await self.narrator.narrate(
            player_action=player_action,
            game_state=game_state,
            orchestrator_decision=orchestrator_decision,
            npc_reactions=npc_reactions,
        )

        state["narrator_output"] = narrator_output
        return state

    async def _update_state(self, state: GraphState) -> GraphState:
        """6. 상태 업데이트 (MongoDB Transaction)"""
        game_state = state["game_state"]
        applied_changes = state["applied_changes"]
        narrator_output = state["narrator_output"]

        # 상태 변경 적용
        player = game_state.player

        if applied_changes.health_change:
            player.health = max(0, min(
                player.max_health,
                player.health + applied_changes.health_change
            ))

        if applied_changes.stamina_change:
            player.stamina = max(0, min(100, player.stamina + applied_changes.stamina_change))

        if applied_changes.coins_change:
            player.coins = max(0, player.coins + applied_changes.coins_change)

        if applied_changes.exp_change:
            player.experience += applied_changes.exp_change
            # 레벨업 체크 (간단히)
            while player.experience >= player.exp_to_next_level:
                player.experience -= player.exp_to_next_level
                player.level += 1
                player.exp_to_next_level = int(player.exp_to_next_level * 1.5)

        if applied_changes.new_position:
            player.position = applied_changes.new_position

        if applied_changes.new_items:
            from domain.orv_v2.models import ItemInstance
            for item_name in applied_changes.new_items:
                item = ItemInstance(
                    item_id=f"item_{game_state.turn_count}",
                    name=item_name,
                    item_type="misc",
                )
                player.inventory.append(item)

        # 턴 증가
        game_state.turn_count += 1

        # 모드 전환 로직
        mode_transition = state.get("mode_transition")

        if mode_transition == "to_interactive":
            # AUTO → INTERACTIVE (시나리오 시작)
            game_state.game_mode = GameMode.INTERACTIVE
            game_state.scenario_phase = "active"

        elif game_state.current_scenario and game_state.current_scenario.status == "completed":
            # INTERACTIVE → AUTO (시나리오 종료)
            game_state.game_mode = GameMode.AUTO_NARRATIVE
            game_state.scenario_phase = "completed"

        # Story Progress 업데이트 (Plan-and-Execute)
        if self.story_executor:
            try:
                story_progress = await self.repository.load_story_progress(game_state.session_id)
                if story_progress:
                    # TODO: 완료된 이벤트 ID를 추적하는 로직 추가 필요
                    story_progress.current_turn = game_state.turn_count
                    await self.repository.save_story_progress(game_state.session_id, story_progress)
            except Exception as e:
                print(f"⚠️  Story Progress 업데이트 실패: {e}")

        # MongoDB 저장 (Transaction)
        await self.repository.save_game_state(game_state)

        # 상태 변경 로그 저장
        await self.repository.log_state_change(
            session_id=game_state.session_id,
            turn=game_state.turn_count,
            changes=applied_changes,
            narrative=narrator_output.narrative,
        )

        state["game_state"] = game_state
        return state

    # ============================================
    # Public API
    # ============================================

    async def run_turn(
        self,
        session_id: str,
        player_action: str | None = None,
    ) -> dict:
        """
        턴 실행

        Args:
            session_id: 세션 ID
            player_action: 플레이어 행동 (Interactive 모드에서만 필수, Auto 모드에서는 None)

        Returns:
            턴 결과 (서술, 선택지, 상태 등)
        """
        logger.info(f"🎯 [Workflow] run_turn 호출: session_id={session_id}, player_action={player_action[:50] if player_action else 'None'}...")

        # 초기 상태
        initial_state: GraphState = {
            "session_id": session_id,
            "player_action": player_action or "",
            "game_state": None,  # load_state에서 로드
            "scenario_context": None,
            "orchestrator_decision": None,
            "narrator_output": None,
            "validation_passed": False,
            "validation_error": None,
            "applied_changes": None,
            "messages": [],
            "system_messages": [],
            "error": None,
            "retry_count": 0,
        }

        # Graph 실행
        logger.info(f"▶️  [Workflow] LangGraph 워크플로우 실행 시작...")
        result = await self.graph.ainvoke(initial_state)
        logger.info(f"✅ [Workflow] LangGraph 워크플로우 실행 완료")

        # 검증 실패 시
        if not result["validation_passed"]:
            return {
                "success": False,
                "error": result["validation_error"],
                "narrative": f"[시스템] {result['validation_error']}",
                "choices": ["다시 시도하기"],
            }

        # 성공
        narrator_output = result["narrator_output"]
        game_state = result["game_state"]
        mode_transition = result.get("mode_transition")

        return {
            "success": True,
            "narrative": narrator_output.narrative,
            "choices": narrator_output.suggested_choices,
            "scene_mood": narrator_output.scene_mood,
            "game_state": {
                "turn": game_state.turn_count,
                "health": game_state.player.health,
                "coins": game_state.player.coins,
                "level": game_state.player.level,
            },
            "game_mode": game_state.game_mode.value,
            "mode_changed": mode_transition is not None,
        }
