"""
Director 에이전트

전체 이야기를 관장하는 최상위 에이전트.
어떤 NPC가 활성화될지 결정하고, 모든 결과를 통합된 서술로 조합합니다.
"""

import json
import re
from typing import Any, Optional, TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from domain.orv.model.state import GameState, NPCInstance
from domain.orv.model.memory import (
    TurnContext,
    TurnPlan,
    NPCInteraction,
    NPCDecision,
    NPCContext,
)
from domain.orv.model.story import StoryContext
from domain.orv.memory.store import MemoryManager
from domain.orv.agent.npc_agent import NPCAgent
from domain.orv.agent.prompts import (
    DIRECTOR_SYSTEM_PROMPT,
    DIRECTOR_PLAN_PROMPT,
    DIRECTOR_COMPOSE_PROMPT,
    DIRECTOR_STORY_CONTEXT_PROMPT,
    BATCH_NPC_SYSTEM_PROMPT,
    BATCH_NPC_PROMPT,
    format_npc_for_director,
)

if TYPE_CHECKING:
    from domain.orv.story.manager import StoryManager


class DirectorAgent:
    """
    전체 이야기를 관장하는 최상위 에이전트.

    책임:
    1. 플레이어 행동 분석
    2. 어떤 NPC가 반응해야 하는지 결정
    3. NPC 간 상호작용 계획
    4. 최종 서사 통합
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        memory_manager: MemoryManager,
        max_active_npcs: int = 3,
        story_manager: Optional["StoryManager"] = None,
    ):
        self.llm = llm
        self.memory_manager = memory_manager
        self.max_active_npcs = max_active_npcs
        self.story_manager = story_manager
        self._npc_agents: dict[str, NPCAgent] = {}
        self._current_story_context: Optional[StoryContext] = None

    def get_or_create_npc_agent(
        self,
        npc: NPCInstance,
    ) -> NPCAgent:
        """NPC 에이전트 조회 또는 생성"""
        if npc.id not in self._npc_agents:
            memory_store = self.memory_manager.get_or_create_store(npc.id, npc.name)
            self._npc_agents[npc.id] = NPCAgent(
                npc=npc,
                memory_store=memory_store,
                llm=self.llm,
            )
        return self._npc_agents[npc.id]

    def _build_turn_context(
        self,
        game_state: GameState,
        player_action: str,
    ) -> TurnContext:
        """턴 컨텍스트 생성"""
        # 현재 위치의 NPC들
        nearby_npcs = [
            npc for npc in game_state.npcs
            if npc.position == game_state.player.position and npc.is_alive
        ]

        # 최근 이벤트 (메시지 히스토리에서 추출)
        recent_events = []
        for msg in game_state.message_history[-5:]:
            if msg["role"] == "assistant":
                # 간단히 첫 줄만 추출
                content = msg["content"].split("\n")[0][:100]
                recent_events.append(content)

        return TurnContext(
            turn_number=game_state.turn_count,
            player_action=player_action,
            player_position=game_state.player.position,
            player_name=game_state.player.name,
            location_name=game_state.player.position,
            location_description=self._get_location_description(game_state.player.position),
            nearby_npc_ids=[npc.id for npc in nearby_npcs],
            nearby_npc_names=[npc.name for npc in nearby_npcs],
            recent_events=recent_events,
            scenario_objective=game_state.current_scenario.objective if game_state.current_scenario else None,
            panic_level=game_state.panic_level,
        )

    def _get_location_description(self, position: str) -> str:
        """위치 설명 반환 (간단한 매핑)"""
        descriptions = {
            "3호선_객차_1": "지하철 1번 객차. 승객이 적은 편이다.",
            "3호선_객차_2": "지하철 2번 객차. 적당한 수의 승객이 있다.",
            "3호선_객차_3": "지하철 3번 객차. 승객들이 많다.",
            "3호선_객차_4": "지하철 4번 객차. 비명 소리가 들려온다.",
            "3호선_객차_5": "지하철 5번 객차. 혼란스러운 분위기다.",
            "3호선_객차_6": "지하철 6번 객차. 가장 끝 객차로, 문이 보인다.",
            "3호선_운전실": "지하철 운전실. 문이 잠겨 있다.",
            "지하철_플랫폼": "지하철 플랫폼. 탈출 지점이다.",
        }
        return descriptions.get(position, "알 수 없는 장소")

    async def plan_turn(
        self,
        game_state: GameState,
        player_action: str,
        session_id: Optional[str] = None,
    ) -> TurnPlan:
        """
        이번 턴에 무엇이 일어날지 계획.

        Returns:
            TurnPlan: 활성화할 NPC들과 상호작용 계획
        """
        turn_context = self._build_turn_context(game_state, player_action)

        # 스토리 컨텍스트 가져오기
        story_context_str = ""
        if self.story_manager and session_id:
            self._current_story_context = self.story_manager.get_narrative_context(
                session_id, game_state
            )
            if self._current_story_context:
                story_context_str = DIRECTOR_STORY_CONTEXT_PROMPT.format(
                    story_context=self._current_story_context.to_prompt_context(),
                    pacing_guidance=self._current_story_context.pacing_guidance,
                )

        # 현재 위치의 NPC 목록 생성
        nearby_npcs = [
            npc for npc in game_state.npcs
            if npc.position == game_state.player.position and npc.is_alive
        ]

        if not nearby_npcs:
            # NPC가 없으면 빈 계획 반환
            return TurnPlan(
                narrative_focus="플레이어 단독 행동",
                scene_mood="tense",
            )

        # NPC 목록 포맷팅
        npc_list_str = "\n".join([
            format_npc_for_director(
                npc_id=npc.id,
                npc_name=npc.name,
                description=npc.description,
                emotional_state=npc.emotional_state,
                health=npc.health,
                has_weapon=npc.has_weapon,
                weapon_type=npc.weapon_type,
                relationship_with_player=self._get_player_relationship_summary(npc.id),
            )
            for npc in nearby_npcs
        ])

        # 프롬프트 구성
        user_prompt = DIRECTOR_PLAN_PROMPT.format(
            turn_number=turn_context.turn_number,
            player_action=player_action,
            player_position=turn_context.player_position,
            panic_level=turn_context.panic_level,
            scenario_objective=turn_context.scenario_objective or "없음",
            npc_list=npc_list_str,
            recent_events="\n".join(turn_context.recent_events) if turn_context.recent_events else "없음",
        )

        # 스토리 컨텍스트 추가
        if story_context_str:
            user_prompt = story_context_str + "\n\n" + user_prompt

        # LLM 호출
        response = await self.llm.ainvoke([
            SystemMessage(content=DIRECTOR_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])

        # 응답 파싱
        return self._parse_turn_plan(response.content)

    def _get_player_relationship_summary(self, npc_id: str) -> str | None:
        """플레이어와의 관계 요약"""
        rel = self.memory_manager.get_relationship(npc_id, "player")
        if rel is None:
            return None
        return rel.relationship_label

    def _parse_turn_plan(self, response: str) -> TurnPlan:
        """LLM 응답을 TurnPlan으로 파싱"""
        json_match = re.search(r"\{[\s\S]*\}", response)

        if json_match:
            try:
                data = json.loads(json_match.group())

                interactions = []
                for inter in data.get("npc_interactions", []):
                    interactions.append(NPCInteraction(
                        initiator_id=inter.get("initiator_id", ""),
                        target_id=inter.get("target_id", "player"),
                        interaction_type=inter.get("interaction_type", "observe"),
                        context=inter.get("context", ""),
                    ))

                return TurnPlan(
                    active_npc_ids=data.get("active_npc_ids", [])[:self.max_active_npcs],
                    npc_interactions=interactions,
                    narrative_focus=data.get("narrative_focus", ""),
                    scene_mood=data.get("scene_mood", "tense"),
                    special_events=data.get("special_events", []),
                )
            except json.JSONDecodeError:
                pass

        # 파싱 실패 시 기본 계획
        return TurnPlan(
            narrative_focus="상황 관찰",
            scene_mood="tense",
        )

    async def process_npc_decisions(
        self,
        game_state: GameState,
        turn_plan: TurnPlan,
        player_action: str,
    ) -> list[NPCDecision]:
        """
        활성화된 NPC들의 의사결정 처리.

        비용 최적화를 위해 배치 처리 사용.
        """
        if not turn_plan.active_npc_ids:
            return []

        turn_context = self._build_turn_context(game_state, player_action)
        decisions = []

        # 활성 NPC들 가져오기
        active_npcs = [
            npc for npc in game_state.npcs
            if npc.id in turn_plan.active_npc_ids and npc.is_alive
        ]

        if len(active_npcs) == 1:
            # 단일 NPC는 개별 처리
            npc = active_npcs[0]
            agent = self.get_or_create_npc_agent(npc)

            npc_context = self._build_npc_context(npc, turn_context)
            decision = await agent.decide(npc_context)
            decisions.append(decision)

        elif len(active_npcs) > 1:
            # 여러 NPC는 배치 처리
            decisions = await self._batch_process_npcs(active_npcs, turn_context)

        return decisions

    def _build_npc_context(
        self,
        npc: NPCInstance,
        turn_context: TurnContext,
    ) -> NPCContext:
        """NPC 컨텍스트 생성"""
        memory_store = self.memory_manager.get_or_create_store(npc.id, npc.name)

        # 관련 기억 검색
        from domain.orv.memory.search import KeywordMemorySearch
        search = KeywordMemorySearch()
        relevant_memories = search.search(
            query=turn_context.player_action,
            memories=memory_store.get_all_memories(),
            current_turn=turn_context.turn_number,
            limit=5,
        )

        # 플레이어와의 관계
        player_rel = memory_store.get_relationship("player")

        # 성격 요약
        p = npc.personality
        personality_traits = []
        if p.bravery >= 70:
            personality_traits.append("용감")
        elif p.bravery <= 30:
            personality_traits.append("겁쟁이")
        if p.aggression >= 70:
            personality_traits.append("공격적")
        if p.empathy >= 70:
            personality_traits.append("공감력 높음")

        return NPCContext(
            turn_context=turn_context,
            npc_id=npc.id,
            npc_name=npc.name,
            personality_summary=", ".join(personality_traits) if personality_traits else "평범",
            emotional_state=npc.emotional_state,
            health=npc.health,
            position=npc.position,
            relevant_memories=relevant_memories,
            player_relationship=player_rel,
            active_goals=memory_store.get_active_goals(),
        )

    async def _batch_process_npcs(
        self,
        npcs: list[NPCInstance],
        turn_context: TurnContext,
    ) -> list[NPCDecision]:
        """여러 NPC를 배치로 처리"""
        # NPC 컨텍스트 준비
        npc_contexts_str = ""
        for i, npc in enumerate(npcs, 1):
            memory_store = self.memory_manager.get_or_create_store(npc.id, npc.name)
            player_rel = memory_store.get_relationship("player")

            # 관련 기억
            from domain.orv.memory.search import KeywordMemorySearch
            search = KeywordMemorySearch()
            memories = search.search(
                query=turn_context.player_action,
                memories=memory_store.get_all_memories(),
                current_turn=turn_context.turn_number,
                limit=3,
            )
            memories_str = "\n".join([f"  - {m.summary}" for m in memories]) if memories else "  없음"

            # 관계
            rel_str = f"신뢰: {player_rel.trust}, 공포: {player_rel.fear}" if player_rel else "첫 만남"

            npc_contexts_str += f"""
### NPC {i}: {npc.name} (ID: {npc.id})
- 설명: {npc.description}
- 감정: {npc.emotional_state}
- 체력: {npc.health}
- 성격: 용기 {npc.personality.bravery}, 공격성 {npc.personality.aggression}, 공감 {npc.personality.empathy}
- 플레이어와의 관계: {rel_str}
- 관련 기억:
{memories_str}
"""

        # 배치 프롬프트 구성
        user_prompt = BATCH_NPC_PROMPT.format(
            turn_number=turn_context.turn_number,
            location_name=turn_context.location_name,
            player_action=turn_context.player_action,
            panic_level=turn_context.panic_level,
            npc_contexts=npc_contexts_str,
        )

        # LLM 호출
        response = await self.llm.ainvoke([
            SystemMessage(content=BATCH_NPC_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])

        # 응답 파싱
        return self._parse_batch_decisions(response.content, npcs)

    def _parse_batch_decisions(
        self,
        response: str,
        npcs: list[NPCInstance],
    ) -> list[NPCDecision]:
        """배치 응답을 NPCDecision 목록으로 파싱"""
        decisions = []

        # JSON 배열 추출
        json_match = re.search(r"\[[\s\S]*\]", response)
        if json_match:
            try:
                data_list = json.loads(json_match.group())

                for data in data_list:
                    npc_id = data.get("npc_id")
                    # 해당 NPC 찾기
                    npc = next((n for n in npcs if n.id == npc_id), None)
                    if npc:
                        decisions.append(NPCDecision(
                            npc_id=npc_id,
                            npc_name=npc.name,
                            action_type=data.get("action_type", "observe"),
                            action_description=data.get("action_description", ""),
                            dialogue=data.get("dialogue"),
                            dialogue_target=data.get("dialogue_target"),
                            dialogue_tone=data.get("dialogue_tone", "neutral"),
                            internal_thought=data.get("internal_thought"),
                            new_emotional_state=data.get("new_emotional_state"),
                            memory_summary=data.get("memory_summary"),
                            memory_importance=data.get("memory_importance", 5),
                        ))

                return decisions
            except json.JSONDecodeError:
                pass

        # 파싱 실패 시 기본 반응
        for npc in npcs:
            decisions.append(NPCDecision(
                npc_id=npc.id,
                npc_name=npc.name,
                action_type="observe",
                action_description="상황을 지켜본다",
            ))

        return decisions

    async def compose_narrative(
        self,
        game_state: GameState,
        player_action: str,
        turn_plan: TurnPlan,
        npc_decisions: list[NPCDecision],
        session_id: Optional[str] = None,
        world_context: Optional[str] = None,
    ) -> str:
        """
        모든 NPC 응답을 웹소설 스타일로 통합.

        Args:
            world_context: 세계관 설명 (WorldKnowledge.world_description)

        Returns:
            완전한 서술 텍스트 (선택지 포함)
        """
        # NPC 반응 포맷팅
        npc_responses_str = ""
        for decision in npc_decisions:
            response_part = f"**{decision.npc_name}**:\n"
            response_part += f"- 행동: {decision.action_description}\n"
            if decision.dialogue:
                response_part += f"- 대사: \"{decision.dialogue}\"\n"
            if decision.internal_thought:
                response_part += f"- (내면: {decision.internal_thought})\n"
            response_part += f"- 감정: {decision.new_emotional_state or '변화 없음'}\n\n"
            npc_responses_str += response_part

        if not npc_responses_str:
            npc_responses_str = "주변에 반응하는 NPC가 없다."

        # 스토리 컨텍스트 가져오기 (캐싱된 것 사용 또는 새로 가져오기)
        story_context = self._current_story_context
        if not story_context and self.story_manager and session_id:
            story_context = self.story_manager.get_narrative_context(session_id, game_state)

        # 세계관 컨텍스트 (전달되지 않았으면 기본값)
        if not world_context:
            world_context = "지하철 3호선 안. 갑자기 멈춘 지하철. 시나리오가 현실화되어 승객들이 패닉에 빠져있다."

        # 시나리오 컨텍스트 구성
        scenario_context = self._build_scenario_context(game_state)

        # 프롬프트 구성
        user_prompt = DIRECTOR_COMPOSE_PROMPT.format(
            world_context=world_context,
            scenario_context=scenario_context,
            turn_number=game_state.turn_count,
            player_action=player_action,
            player_position=game_state.player.position,
            panic_level=game_state.panic_level,
            narrative_focus=turn_plan.narrative_focus,
            scene_mood=turn_plan.scene_mood,
            npc_responses=npc_responses_str,
        )

        # 스토리 컨텍스트 추가
        if story_context:
            story_guidance = self._build_compose_story_guidance(story_context)
            user_prompt = story_guidance + "\n\n" + user_prompt

        # LLM 호출
        response = await self.llm.ainvoke([
            SystemMessage(content="당신은 웹소설 작가입니다. 주어진 정보를 바탕으로 몰입감 있는 장면을 서술하세요."),
            HumanMessage(content=user_prompt),
        ])

        return response.content

    def _build_scenario_context(self, game_state: GameState) -> str:
        """현재 시나리오 상태를 문자열로 구성"""
        scenario = game_state.current_scenario
        if not scenario:
            return "시나리오 없음"

        # 시나리오 완료 여부 확인
        is_completed = scenario.status == "completed" or game_state.first_kill_completed

        if is_completed:
            # 시나리오 완료 시 명확하게 표시
            lines = [
                "## ✅ 시나리오 클리어!",
                f"**시나리오**: {scenario.title} ({scenario.difficulty}급) - **완료됨**",
                f"**달성한 목표**: {scenario.objective}",
                f"**보상**: {scenario.reward_coins} 코인, {scenario.reward_exp} 경험치 획득",
                "",
                "⚠️ **중요**: 시나리오가 이미 완료되었습니다. 시간 제한이나 죽음 경고를 언급하지 마세요.",
                "플레이어는 이제 자유롭게 탐색하거나 다음 시나리오를 기다릴 수 있습니다.",
            ]
        else:
            lines = [
                f"**시나리오**: {scenario.title} ({scenario.difficulty}급)",
                f"**목표**: {scenario.objective}",
                f"**상태**: {scenario.status}",
            ]

            if scenario.remaining_time is not None:
                lines.append(f"**남은 시간**: {scenario.remaining_time}턴")

            if scenario.progress:
                lines.append(f"**진행 상황**: {scenario.progress}")

        # 게임 상태 추가
        lines.append(f"**패닉 레벨**: {game_state.panic_level}/100")

        return "\n".join(lines)

    def _build_compose_story_guidance(self, story_context: StoryContext) -> str:
        """서술용 스토리 가이드 생성"""
        lines = [
            "## 스토리 가이드",
            f"**현재 단계**: {story_context.current_phase.value}",
            f"**톤**: {story_context.phase_tone}",
            f"**긴장도**: {story_context.tension_level.value} ({story_context.tension_value}/100)",
            "",
        ]

        # 회수 가능한 복선이 있으면 안내
        if story_context.ready_payoffs:
            lines.append("### 활용 가능한 복선 (자연스럽게 통합하세요)")
            for pp in story_context.ready_payoffs[:2]:  # 최대 2개만
                lines.append(f"- {pp.seed_description} → {pp.payoff_description}")
            lines.append("")

        # 기한 초과 복선은 강조
        if story_context.overdue_plot_points:
            lines.append("### ⚠️ 반드시 활용해야 할 복선")
            for pp in story_context.overdue_plot_points[:2]:
                lines.append(f"- **{pp.seed_description}** → {pp.payoff_description}")
            lines.append("")

        lines.append(f"**페이싱**: {story_context.pacing_guidance}")

        return "\n".join(lines)

    def apply_decisions_to_state(
        self,
        game_state: GameState,
        decisions: list[NPCDecision],
        turn: int,
    ) -> None:
        """의사결정 결과를 게임 상태에 적용"""
        for decision in decisions:
            # NPC 찾기
            npc = game_state.get_npc_by_id(decision.npc_id)
            if not npc:
                continue

            # 감정 상태 업데이트
            if decision.new_emotional_state:
                npc.emotional_state = decision.new_emotional_state

            # 현재 목표 업데이트
            if decision.action_type == "flee":
                npc.current_goal = "flee"
            elif decision.action_type == "attack":
                npc.current_goal = "fight"
            elif decision.action_type == "help":
                npc.current_goal = "help_player"

            # 기억 저장
            if decision.memory_summary:
                self.memory_manager.add_memory(
                    npc_id=decision.npc_id,
                    npc_name=npc.name,
                    event_type="turn_event",
                    summary=decision.memory_summary,
                    turn=turn,
                    location=npc.position,
                    involves_player=True,
                    importance=decision.memory_importance,
                )
