"""
게임 오케스트레이터

멀티 에이전트 시스템을 조율하는 LangGraph 워크플로우.

워크플로우:
check_scenario → story_beat → director_plan → npc_phase → compose_narrative → update_state → constellation_react → END
"""

import json
import re
import random
import uuid
from typing import Annotated, TypedDict, Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from domain.orv.model.state import (
    GameState,
    NPCInstance,
    ScenarioState,
    ConstellationChannel,
    ItemInstance,
    SUBWAY_COORDINATES,
)
from domain.orv.model.knowledge import WorldKnowledge
from domain.orv.model.memory import TurnPlan, NPCDecision
from domain.orv.model.story import StoryContext, PlotPoint
from domain.orv.memory.store import MemoryManager
from domain.orv.memory.persistence import SessionPersistence
from domain.orv.agent.director import DirectorAgent
from domain.orv.agent.constellation_agent import ConstellationAgent
from domain.orv.agent.dokkaebi_agent import DokkaebiAgent
from domain.orv.story.manager import StoryManager
from domain.orv.story.presets import create_scenario_1_arc


class OrchestratorState(TypedDict):
    """오케스트레이터 상태"""

    messages: Annotated[list, add_messages]
    game_state: GameState
    player_action: str
    turn_plan: TurnPlan | None
    npc_decisions: list[NPCDecision]
    gm_response: str
    system_messages: list[str]
    # 스토리 관련
    story_context: StoryContext | None
    triggered_payoffs: list[PlotPoint]


class GameOrchestrator:
    """
    멀티 에이전트 게임 오케스트레이터.

    Director Agent가 전체 이야기를 관장하고,
    NPC Agent들이 개별 의사결정을 수행합니다.
    StoryManager가 장기 스토리 아크와 복선을 관리합니다.
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        memory_manager: MemoryManager,
        persistence: SessionPersistence | None = None,
        story_manager: StoryManager | None = None,
    ):
        self.llm = llm
        self.memory_manager = memory_manager
        self.persistence = persistence
        self.story_manager = story_manager or StoryManager()
        self.knowledge = WorldKnowledge()
        self.director = DirectorAgent(
            llm=llm,
            memory_manager=memory_manager,
            story_manager=self.story_manager,
        )
        self.constellation_agent = ConstellationAgent(
            constellations=self.knowledge.constellations,
            llm=llm,  # 메인 LLM 공유
        )
        self.dokkaebi = DokkaebiAgent(llm=llm)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        graph = StateGraph(OrchestratorState)

        # 노드 추가
        graph.add_node("check_scenario", self._check_scenario)
        graph.add_node("story_beat", self._story_beat)  # 스토리 비트 노드 추가
        graph.add_node("director_plan", self._director_plan)
        graph.add_node("npc_phase", self._npc_phase)
        graph.add_node("compose_narrative", self._compose_narrative)
        graph.add_node("update_state", self._update_state)
        graph.add_node("constellation_react", self._constellation_react)

        # 엣지 설정
        graph.set_entry_point("check_scenario")
        graph.add_edge("check_scenario", "story_beat")  # 스토리 비트를 먼저 처리
        graph.add_edge("story_beat", "director_plan")
        graph.add_edge("director_plan", "npc_phase")
        graph.add_edge("npc_phase", "compose_narrative")
        graph.add_edge("compose_narrative", "update_state")
        graph.add_edge("update_state", "constellation_react")
        graph.add_edge("constellation_react", END)

        return graph.compile()

    async def _check_scenario(self, state: OrchestratorState) -> OrchestratorState:
        """시나리오 상태 체크 및 초기화"""
        game_state = state["game_state"]
        messages = []

        # 첫 시나리오 시작
        if game_state.current_scenario is None:
            scenario = self.knowledge.scenarios[0]
            game_state.current_scenario = ScenarioState(
                scenario_id=scenario.scenario_id,
                title=scenario.title,
                difficulty=scenario.difficulty,
                objective=scenario.objective,
                time_limit=scenario.time_limit,
                remaining_time=scenario.time_limit,
                reward_coins=scenario.reward_coins,
                reward_exp=scenario.reward_exp,
            )
            messages.append(f"[시나리오 시작] {scenario.difficulty}급: {scenario.title}")

        # NPC 스폰
        self._spawn_npcs(game_state)

        # 이름 질문 체크 (플레이어가 이름을 물어보면 이름 할당)
        player_action = state.get("player_action", "")
        await self._check_name_inquiry(game_state, player_action)

        # 시나리오 시간 감소 (완료된 시나리오는 제외)
        if (game_state.current_scenario
            and game_state.current_scenario.remaining_time is not None
            and game_state.current_scenario.status != "completed"):
            game_state.current_scenario.remaining_time -= 1
            if game_state.current_scenario.remaining_time <= 0:
                game_state.current_scenario.status = "failed"
                messages.append("[시나리오 실패] 시간 초과!")

        # 스토리 아크 초기화 (첫 턴이면)
        if not self.story_manager.get_arc(game_state.session_id):
            arc = create_scenario_1_arc(start_turn=game_state.turn_count)
            self.story_manager.set_arc(game_state.session_id, arc)
            messages.append("[스토리 아크 시작] 지하철 3호선 생존")

        state["game_state"] = game_state
        state["system_messages"] = messages
        return state

    async def _story_beat(self, state: OrchestratorState) -> OrchestratorState:
        """스토리 비트 처리 - 단계 진행, 복선 체크, 긴장도 관리"""
        game_state = state["game_state"]
        player_action = state["player_action"]
        messages = state.get("system_messages", [])
        session_id = game_state.session_id

        # 스토리 컨텍스트 가져오기
        story_context = self.story_manager.get_narrative_context(session_id, game_state)
        state["story_context"] = story_context

        if story_context is None:
            state["triggered_payoffs"] = []
            return state

        # 1. 스토리 단계 진행 체크
        npc_reactions = []  # 이 시점에서는 NPC 반응이 없음
        should_advance, new_phase = self.story_manager.check_phase_progression(
            session_id=session_id,
            game_state=game_state,
            player_action=player_action,
            npc_reactions=npc_reactions,
        )

        if should_advance and new_phase:
            messages.append(f"[스토리 진행] 단계 전환: {new_phase.value}")

        # 2. 복선 회수 트리거 체크
        triggered_payoffs = self.story_manager.check_payoff_triggers(
            session_id=session_id,
            game_state=game_state,
            player_action=player_action,
        )
        state["triggered_payoffs"] = triggered_payoffs

        if triggered_payoffs:
            for pp in triggered_payoffs:
                # 상태를 PAYOFF_READY로 업데이트
                from domain.orv.model.story import PlotPointStatus
                self.story_manager.update_plot_point_status(
                    session_id, pp.plot_point_id, PlotPointStatus.PAYOFF_READY
                )

        # 3. 긴장도 조정
        tension_adjustment = self.story_manager.calculate_tension_adjustment(
            session_id=session_id,
            game_state=game_state,
            player_action=player_action,
            npc_reactions=npc_reactions,
        )

        if tension_adjustment != 0:
            self.story_manager.update_tension(
                session_id=session_id,
                adjustment=tension_adjustment,
                turn=game_state.turn_count,
            )

        state["system_messages"] = messages
        return state

    def _spawn_npcs(self, game_state: GameState) -> None:
        """현재 위치에 NPC 스폰"""
        current_loc = next(
            (loc for loc in self.knowledge.locations if loc.name == game_state.player.position),
            None,
        )
        if not current_loc:
            return

        # 이미 해당 위치에 NPC가 있으면 스킵
        existing_npcs = [npc for npc in game_state.npcs if npc.position == game_state.player.position]
        if existing_npcs:
            return

        # NPC 수 결정
        min_npcs, max_npcs = current_loc.npcs_count_range
        npc_count = random.randint(min_npcs, max_npcs)

        for _ in range(npc_count):
            npc_template = random.choice(self.knowledge.npc_templates)

            has_weapon = random.random() < npc_template.has_weapon_chance
            weapon = random.choice(npc_template.weapon_pool) if has_weapon and npc_template.weapon_pool else None

            coord = current_loc.coordinates.model_copy()
            coord.lat += random.uniform(-0.0001, 0.0001)
            coord.lng += random.uniform(-0.0001, 0.0001)

            npc = NPCInstance(
                id=str(uuid.uuid4())[:8],
                name=f"어떤 {npc_template.npc_type}",  # 이름을 물어보기 전까지는 타입 기반 이름
                named=False,  # 아직 이름이 확정되지 않음
                npc_type=npc_template.npc_type,
                description=npc_template.description,
                position=game_state.player.position,
                coordinates=coord,
                health=npc_template.base_health,
                max_health=npc_template.base_health,
                disposition=npc_template.base_disposition,
                has_weapon=has_weapon,
                weapon_type=weapon,
            )
            game_state.npcs.append(npc)

            # NPC 기억 저장소 초기화
            self.memory_manager.get_or_create_store(npc.id, npc.name)

    async def _generate_korean_name(self, npc_type: str, description: str, used_names: set[str]) -> str:
        """LLM을 사용해 NPC 타입에 맞는 한국 이름 생성"""
        from langchain_openai import ChatOpenAI

        # 저렴한 모델 사용
        cheap_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.9, max_tokens=50)

        used_names_str = ", ".join(list(used_names)[:10]) if used_names else "없음"

        prompt = f"""한국인 이름을 하나만 생성해주세요.

NPC 유형: {npc_type}
설명: {description}
이미 사용된 이름 (피해주세요): {used_names_str}

규칙:
- 성+이름 형식 (예: 김민수, 박지영)
- 유형에 어울리는 이름 (노인이면 옛날 이름, 학생이면 요즘 이름)
- 이름만 출력, 다른 설명 없이"""

        try:
            response = await cheap_llm.ainvoke(prompt)
            name = response.content.strip().replace('"', '').replace("'", "")
            # 이름만 추출 (공백이나 기타 문자 제거)
            name = name.split()[0] if name else "김철수"
            return name
        except Exception:
            # 실패 시 기본 이름
            return f"김{random.choice(['민수', '지영', '철수', '영희'])}"

    async def _check_name_inquiry(self, game_state: GameState, player_action: str) -> None:
        """
        플레이어가 NPC의 이름을 물어보면 이름을 할당합니다.

        이름 질문 패턴: "이름", "누구", "뭐야", "성함" 등
        """
        # 이름 질문 패턴
        name_patterns = ["이름", "누구", "뭐야", "성함", "누구세요", "누구야", "뭐예요"]

        # 이름 질문인지 확인
        is_name_inquiry = any(pattern in player_action for pattern in name_patterns)
        if not is_name_inquiry:
            return

        # 현재 위치의 아직 이름이 정해지지 않은 NPC들
        unnamed_npcs = [
            npc for npc in game_state.npcs
            if npc.position == game_state.player.position
            and npc.is_alive
            and not npc.named
        ]

        if not unnamed_npcs:
            return

        # 특정 타입이 언급되었는지 확인
        target_npc = None
        for npc in unnamed_npcs:
            if npc.npc_type in player_action:
                target_npc = npc
                break

        # 타입이 언급되지 않았으면 첫 번째 unnamed NPC 선택
        if target_npc is None:
            target_npc = unnamed_npcs[0]

        # 이미 사용된 이름 수집
        used_names = {npc.name for npc in game_state.npcs if npc.named}

        # LLM으로 한국 이름 생성
        new_name = await self._generate_korean_name(
            npc_type=target_npc.npc_type,
            description=target_npc.description,
            used_names=used_names,
        )

        # 이름 할당 및 상태 변경
        target_npc.name = new_name
        target_npc.named = True

        # 메모리 스토어 이름도 업데이트
        self.memory_manager.get_or_create_store(target_npc.id, new_name)

    async def _director_plan(self, state: OrchestratorState) -> OrchestratorState:
        """Director가 턴 계획 수립"""
        game_state = state["game_state"]
        player_action = state["player_action"]

        turn_plan = await self.director.plan_turn(
            game_state=game_state,
            player_action=player_action,
            session_id=game_state.session_id,
        )
        state["turn_plan"] = turn_plan

        return state

    async def _npc_phase(self, state: OrchestratorState) -> OrchestratorState:
        """활성화된 NPC들의 의사결정 처리"""
        game_state = state["game_state"]
        turn_plan = state["turn_plan"]
        player_action = state["player_action"]

        if turn_plan is None:
            state["npc_decisions"] = []
            return state

        decisions = await self.director.process_npc_decisions(
            game_state=game_state,
            turn_plan=turn_plan,
            player_action=player_action,
        )

        state["npc_decisions"] = decisions
        return state

    async def _compose_narrative(self, state: OrchestratorState) -> OrchestratorState:
        """Director가 모든 결과를 통합된 서술로 조합"""
        game_state = state["game_state"]
        player_action = state["player_action"]
        turn_plan = state["turn_plan"]
        npc_decisions = state["npc_decisions"]
        system_messages = state.get("system_messages", [])
        triggered_payoffs = state.get("triggered_payoffs", [])

        if turn_plan is None:
            turn_plan = TurnPlan(narrative_focus="플레이어 행동", scene_mood="tense")

        # Director가 서술 생성 (세계관 컨텍스트 전달)
        narrative = await self.director.compose_narrative(
            game_state=game_state,
            player_action=player_action,
            turn_plan=turn_plan,
            npc_decisions=npc_decisions,
            session_id=game_state.session_id,
            world_context=self.knowledge.world_description,
        )

        # 복선 회수 처리 (서술에 반영된 것으로 간주)
        # 실제로는 LLM이 복선을 활용했는지 확인해야 하지만,
        # 여기서는 트리거된 복선을 회수된 것으로 처리
        for pp in triggered_payoffs:
            self.story_manager.resolve_plot_point(
                session_id=game_state.session_id,
                plot_point_id=pp.plot_point_id,
                payoff_narrative=f"[{pp.payoff_description}]",  # 실제 서술은 LLM이 생성
                turn=game_state.turn_count,
            )
            # 스토리 비트 추가
            self.story_manager.add_story_beat(
                session_id=game_state.session_id,
                turn=game_state.turn_count,
                summary=f"복선 회수: {pp.seed_description}",
                significance=pp.payoff_description,
                resolved_plot_points=[pp.plot_point_id],
            )

        # 시스템 메시지 추가
        if system_messages:
            system_msg_block = "\n[SYSTEM_MESSAGE]\n" + "\n".join(system_messages) + "\n[/SYSTEM_MESSAGE]"
            if "[SYSTEM_MESSAGE]" not in narrative:
                # 서술 시작 부분에 추가
                narrative = system_msg_block + "\n\n" + narrative

        state["gm_response"] = narrative
        state["messages"] = [*state["messages"], AIMessage(content=narrative)]

        return state

    async def _update_state(self, state: OrchestratorState) -> OrchestratorState:
        """응답에서 상태 변경 추출 및 적용"""
        game_state = state["game_state"]
        response = state["gm_response"]
        npc_decisions = state["npc_decisions"]
        player_action = state["player_action"]

        # 클리어 전 상태 기록 (도깨비 처리용)
        was_cleared_before = game_state.first_kill_completed
        old_position = game_state.player.position

        # 도깨비: 자살 시도 감지 (상태 변경 전에 체크)
        rule_event = self.dokkaebi.detect_rule_event(
            player_action=player_action,
            game_state=game_state,
        )

        if rule_event == "suicide_attempt":
            # 자살 시도는 무효 처리 - 도깨비가 막음
            suicide_warning = await self.dokkaebi.generate_suicide_warning(
                game_state=game_state,
                player_action=player_action,
            )
            state["gm_response"] = suicide_warning
            state["game_state"] = game_state
            return state

        # NPC 의사결정 적용
        self.director.apply_decisions_to_state(
            game_state=game_state,
            decisions=npc_decisions,
            turn=game_state.turn_count,
        )

        # STATE_UPDATE 파싱 및 적용
        killed_target_name = None
        new_position = None
        match = re.search(r"\[STATE_UPDATE\](.*?)\[/STATE_UPDATE\]", response, re.DOTALL)
        if match:
            try:
                update = json.loads(match.group(1).strip())
                new_position = update.get("new_position")
                killed_target_name = self._apply_state_update(game_state, update)
            except json.JSONDecodeError:
                pass

        # 도깨비 브리핑 수집
        dokkaebi_briefings = []

        # 도깨비: 구역 이동 브리핑
        if new_position and new_position != old_position:
            if new_position not in game_state.discovered_locations:
                area_desc = self.director._get_location_description(new_position)
                area_briefing = await self.dokkaebi.generate_area_transition_briefing(
                    game_state=game_state,
                    new_position=new_position,
                    area_description=area_desc,
                )
                if area_briefing:
                    dokkaebi_briefings.append(area_briefing)

        # 도깨비: 시나리오 클리어 체크 및 발표
        # NPC 살해 또는 환경 생명체(곤충 등) 살해 모두 체크
        if not was_cleared_before:
            # 먼저 NPC 살해로 이미 클리어된 경우 체크
            # (_apply_state_update에서 first_kill_completed=True, status="completed" 설정됨)
            npc_kill_cleared = game_state.first_kill_completed

            # 환경 생명체(곤충, 강아지 등) 살해 체크
            is_cleared, clear_method = self.dokkaebi.check_scenario_clear(
                game_state=game_state,
                player_action=player_action,
                killed_target=killed_target_name,
                narrative=response,  # Director 서술도 전달하여 거짓말 방지
            )

            # NPC 살해로 클리어된 경우도 처리
            if npc_kill_cleared and not is_cleared:
                is_cleared = True
                if killed_target_name:
                    if "강아지" in killed_target_name or "개" in killed_target_name:
                        clear_method = "kill_animal"
                    else:
                        clear_method = "kill_human"
                else:
                    clear_method = "kill_unknown"

            if is_cleared:
                # 곤충/강아지 살해인 경우 상태 업데이트 (NPC가 아닌 생명체)
                # kill_animal은 NPC가 아닌 강아지 살해 시에도 반환됨
                if clear_method in ("kill_insect", "kill_animal") and not game_state.first_kill_completed:
                    game_state.first_kill_completed = True
                    if game_state.current_scenario:
                        game_state.current_scenario.status = "completed"
                        game_state.player.coins += game_state.current_scenario.reward_coins
                        game_state.player.experience += game_state.current_scenario.reward_exp
                        game_state.completed_scenarios.append(game_state.current_scenario.scenario_id)

                # 강아지 살해인 경우 killed_target 설정 (NPC가 아니므로 직접 지정)
                display_target = killed_target_name
                if clear_method == "kill_animal" and not killed_target_name:
                    display_target = "강아지"

                clear_announcement, clear_record = await self.dokkaebi.generate_clear_announcement(
                    game_state=game_state,
                    clear_method=clear_method or "kill_unknown",
                    killed_target=display_target,
                )
                if clear_announcement:
                    dokkaebi_briefings.append(clear_announcement)

                # 다음 시나리오로 자동 전환
                self._transition_to_next_scenario(game_state)

        # 게임 오버 체크
        if game_state.player.health <= 0:
            game_state.game_over = True
            # 도깨비: 사망 브리핑
            death_briefing = await self.dokkaebi.generate_death_briefing(
                game_state=game_state,
                cause_of_death="체력 소진",
            )
            if death_briefing:
                dokkaebi_briefings.append(death_briefing)

        # 도깨비: 시간 경고 체크 (완료된 시나리오는 제외)
        scenario = game_state.current_scenario
        if scenario and scenario.remaining_time == 3 and scenario.status != "completed":
            time_warning = await self.dokkaebi.generate_time_warning(game_state)
            if time_warning:
                dokkaebi_briefings.append(time_warning)

        # 시나리오 클리어 체크 (위치 기반)
        if game_state.player.position == "지하철_플랫폼":
            game_state.scenario_cleared = True

        game_state.turn_count += 1

        # 도깨비 브리핑을 응답에 추가
        if dokkaebi_briefings:
            current_response = state["gm_response"]
            state["gm_response"] = current_response + "\n\n" + "\n\n".join(dokkaebi_briefings)

        # 영속성 저장
        if self.persistence:
            self.persistence.save_session(
                session_id=game_state.session_id,
                game_state_dict=game_state.model_dump(),
                memory_stores=self.memory_manager.get_stores(),
            )

        state["game_state"] = game_state
        return state

    def _apply_state_update(self, game_state: GameState, update: dict) -> Optional[str]:
        """상태 업데이트 적용. 죽인 대상 이름 반환 (있으면)"""
        killed_target_name = None

        # 체력 변경
        if update.get("health_change"):
            game_state.player.health = max(
                0, min(game_state.player.max_health, game_state.player.health + update["health_change"])
            )

        # 스태미나 변경
        if update.get("stamina_change"):
            game_state.player.stamina = max(0, min(100, game_state.player.stamina + update["stamina_change"]))

        # 코인 변경
        if update.get("coins_change"):
            game_state.player.coins = max(0, game_state.player.coins + update["coins_change"])

        # 경험치 변경
        if update.get("exp_change"):
            game_state.player.experience += update["exp_change"]
            while game_state.player.experience >= game_state.player.exp_to_next_level:
                game_state.player.experience -= game_state.player.exp_to_next_level
                game_state.player.level += 1
                game_state.player.attribute_points += 3
                game_state.player.exp_to_next_level = int(game_state.player.exp_to_next_level * 1.5)

        # 공포도 변경
        if update.get("fear_change"):
            game_state.player.fear_level = max(0, min(100, game_state.player.fear_level + update["fear_change"]))

        # 위치 변경
        if update.get("new_position"):
            new_pos = update["new_position"]
            valid_locations = [loc.name for loc in self.knowledge.locations]
            if new_pos in valid_locations:
                game_state.player.position = new_pos
                if new_pos not in game_state.discovered_locations:
                    game_state.discovered_locations.append(new_pos)
                if new_pos in SUBWAY_COORDINATES:
                    game_state.player.coordinates = SUBWAY_COORDINATES[new_pos].model_copy()

        # 아이템 획득
        if update.get("new_items"):
            items = update["new_items"]
            if isinstance(items, str):
                items = [items]
            for item_name in items:
                if item_name:
                    new_item = ItemInstance(
                        item_id=str(uuid.uuid4())[:8],
                        name=item_name,
                        item_type="misc",
                    )
                    game_state.player.inventory.append(new_item)

        # NPC 살해
        if update.get("killed_npc_id"):
            npc_id = update["killed_npc_id"]
            for npc in game_state.npcs:
                if npc.id == npc_id:
                    killed_target_name = npc.name  # 도깨비용 기록
                    npc.is_alive = False
                    npc.health = 0
                    game_state.killed_npcs.append(npc_id)

                    if not game_state.first_kill_completed:
                        game_state.first_kill_completed = True
                        if game_state.current_scenario:
                            game_state.current_scenario.status = "completed"
                            game_state.player.coins += game_state.current_scenario.reward_coins
                            game_state.player.experience += game_state.current_scenario.reward_exp
                            game_state.completed_scenarios.append(game_state.current_scenario.scenario_id)

                    # 목격자에게 기억 추가
                    witnesses = [
                        n for n in game_state.npcs
                        if n.position == game_state.player.position and n.is_alive and n.id != npc_id
                    ]
                    for witness in witnesses:
                        self.memory_manager.add_memory(
                            npc_id=witness.id,
                            npc_name=witness.name,
                            event_type="witnessed",
                            summary=f"{npc.name}의 죽음을 목격함",
                            turn=game_state.turn_count,
                            location=witness.position,
                            involves_player=True,
                            importance=9,
                            emotional_valence=-0.8,
                            emotional_intensity=0.9,
                        )
                        self.memory_manager.update_relationship(
                            npc_id=witness.id,
                            npc_name=witness.name,
                            target_id="player",
                            target_type="player",
                            target_name=game_state.player.name,
                            interaction_type="attack",  # 간접 목격이지만 공포 유발
                            intensity=30,
                            turn=game_state.turn_count,
                        )
                        witness.emotional_state = "terrified"
                    break

        # 패닉 레벨 변경
        if update.get("panic_change"):
            game_state.panic_level = max(0, min(100, game_state.panic_level + update["panic_change"]))

        # 시나리오 진행 업데이트
        if update.get("scenario_progress") and game_state.current_scenario:
            game_state.current_scenario.progress = update["scenario_progress"]

        return killed_target_name

    def _transition_to_next_scenario(self, game_state: GameState) -> None:
        """
        현재 시나리오 완료 후 다음 시나리오로 전환.

        시나리오 1 (생존 적합성 테스트) 완료 후 시나리오 2 (한강 대교)로 전환.
        """
        current = game_state.current_scenario
        if not current or current.status != "completed":
            return

        # 다음 시나리오 찾기
        current_index = -1
        for i, scenario in enumerate(self.knowledge.scenarios):
            if scenario.scenario_id == current.scenario_id:
                current_index = i
                break

        # 다음 시나리오가 있으면 설정
        if current_index >= 0 and current_index + 1 < len(self.knowledge.scenarios):
            next_scenario = self.knowledge.scenarios[current_index + 1]
            game_state.current_scenario = ScenarioState(
                scenario_id=next_scenario.scenario_id,
                title=next_scenario.title,
                difficulty=next_scenario.difficulty,
                objective=next_scenario.objective,
                time_limit=next_scenario.time_limit,
                remaining_time=next_scenario.time_limit,
                reward_coins=next_scenario.reward_coins,
                reward_exp=next_scenario.reward_exp,
                status="active",
            )

    async def _constellation_react(self, state: OrchestratorState) -> OrchestratorState:
        """성좌 반응 생성 (ConstellationAgent 사용)"""
        game_state = state["game_state"]
        player_action = state["player_action"]
        npc_decisions = state["npc_decisions"]
        gm_response = state.get("gm_response", "")

        # 관전 성좌 초기화 (첫 턴)
        if not game_state.watching_constellations:
            game_state.watching_constellations = [
                c.name for c in random.sample(self.knowledge.constellations, min(3, len(self.knowledge.constellations)))
            ]

        # ConstellationAgent로 반응 생성
        reactions = await self.constellation_agent.generate_reactions(
            game_state=game_state,
            player_action=player_action,
            npc_decisions=npc_decisions,
            narrative=gm_response,
        )

        # 반응을 게임 상태에 적용하고 시스템 메시지 생성
        constellation_messages = self.constellation_agent.apply_reactions(
            game_state=game_state,
            reactions=reactions,
        )

        # 성좌 메시지를 서술에 추가
        if constellation_messages and gm_response:
            constellation_block = "\n\n[SYSTEM_MESSAGE]\n" + "\n".join(constellation_messages) + "\n[/SYSTEM_MESSAGE]"
            # 서술 끝에 추가 (CHOICES 태그 앞에)
            if "[CHOICES]" in gm_response:
                gm_response = gm_response.replace("[CHOICES]", constellation_block + "\n\n[CHOICES]")
            else:
                gm_response += constellation_block
            state["gm_response"] = gm_response

        state["game_state"] = game_state
        return state

    async def run(
        self,
        game_state: GameState,
        player_action: str,
        message_history: list,
    ) -> tuple[GameState, str, list[str]]:
        """
        턴 실행.

        Returns:
            (업데이트된 GameState, GM 응답, 선택지 목록)
        """
        # 히스토리를 메시지로 변환
        history_messages = []
        for msg in message_history[-10:]:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                clean_content = re.sub(
                    r"\[STATE_UPDATE\].*?\[/STATE_UPDATE\]", "", msg["content"], flags=re.DOTALL
                )
                clean_content = re.sub(
                    r"\[CHOICES\].*?\[/CHOICES\]", "", clean_content, flags=re.DOTALL
                ).strip()
                if clean_content:
                    history_messages.append(AIMessage(content=clean_content))

        # 초기 상태
        initial_state: OrchestratorState = {
            "messages": [*history_messages, HumanMessage(content=player_action)],
            "game_state": game_state,
            "player_action": player_action,
            "turn_plan": None,
            "npc_decisions": [],
            "gm_response": "",
            "system_messages": [],
            "story_context": None,
            "triggered_payoffs": [],
        }

        # 워크플로우 실행
        result = await self._graph.ainvoke(initial_state)

        # 응답 파싱
        response = result["gm_response"]

        # 선택지 추출
        choices: list[str] = []
        choices_match = re.search(r"\[CHOICES\](.*?)\[/CHOICES\]", response, re.DOTALL)
        if choices_match:
            choices_text = choices_match.group(1).strip()
            for line in choices_text.split("\n"):
                line = line.strip()
                if line and line[0].isdigit():
                    choice = re.sub(r"^\d+\.\s*", "", line)
                    if choice:
                        choices.append(choice)

        # 태그 제거한 응답
        clean_response = re.sub(
            r"\[STATE_UPDATE\].*?\[/STATE_UPDATE\]", "", response, flags=re.DOTALL
        )
        clean_response = re.sub(
            r"\[CHOICES\].*?\[/CHOICES\]", "", clean_response, flags=re.DOTALL
        ).strip()

        return result["game_state"], clean_response, choices
