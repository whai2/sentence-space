"""
NPC 에이전트

개별 NPC의 독립적인 의사결정과 기억을 관리합니다.
"""

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from domain.orv.model.state import NPCInstance, NPCPersonality
from domain.orv.model.memory import (
    NPCMemoryStore,
    NPCContext,
    NPCDecision,
    MemoryEntry,
    RelationshipMemory,
)
from domain.orv.memory.search import KeywordMemorySearch
from domain.orv.agent.prompts import (
    NPC_SYSTEM_PROMPT,
    NPC_DECIDE_PROMPT,
    NPC_RESPOND_PROMPT,
    format_memory_for_context,
    format_relationship_for_context,
    format_goal_for_context,
)


class NPCAgent:
    """
    개별 NPC의 독립적인 에이전트.

    특징:
    - 자신만의 기억 저장소
    - 성격 기반 의사결정
    - LLM을 통한 자연스러운 응답 생성
    """

    def __init__(
        self,
        npc: NPCInstance,
        memory_store: NPCMemoryStore,
        llm: ChatOpenAI,
    ):
        self.npc = npc
        self.memory = memory_store
        self.llm = llm
        self.search = KeywordMemorySearch()

    def _build_system_prompt(self) -> str:
        """NPC 시스템 프롬프트 생성"""
        personality = self.npc.personality

        # 성격 요약 생성
        personality_summary = self._summarize_personality(personality)

        return NPC_SYSTEM_PROMPT.format(
            npc_name=self.npc.name,
            npc_description=self.npc.description,
            personality_summary=personality_summary,
            emotional_state=self.npc.emotional_state,
            health=self.npc.health,
            max_health=self.npc.max_health,
            bravery=personality.bravery,
            aggression=personality.aggression,
            empathy=personality.empathy,
            selfishness=personality.selfishness,
            rationality=personality.rationality,
        )

    def _summarize_personality(self, p: NPCPersonality) -> str:
        """성격 특성을 자연어로 요약"""
        traits = []

        if p.bravery >= 70:
            traits.append("용감한")
        elif p.bravery <= 30:
            traits.append("겁이 많은")

        if p.aggression >= 70:
            traits.append("공격적인")
        elif p.aggression <= 30:
            traits.append("온순한")

        if p.empathy >= 70:
            traits.append("공감 능력이 높은")
        elif p.empathy <= 30:
            traits.append("냉담한")

        if p.selfishness >= 70:
            traits.append("이기적인")
        elif p.selfishness <= 30:
            traits.append("이타적인")

        if p.rationality >= 70:
            traits.append("이성적인")
        elif p.rationality <= 30:
            traits.append("감정적인")

        if not traits:
            return "평범한"

        return ", ".join(traits)

    def _get_relevant_memories(
        self,
        context: NPCContext,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """상황에 관련된 기억 검색"""
        all_memories = self.memory.get_all_memories()
        if not all_memories:
            return []

        # 플레이어 행동을 쿼리로 사용
        query = context.turn_context.player_action

        return self.search.search(
            query=query,
            memories=all_memories,
            current_turn=context.turn_context.turn_number,
            limit=limit,
        )

    def _format_memories(self, memories: list[MemoryEntry]) -> str:
        """기억 목록을 문자열로 포맷팅"""
        if not memories:
            return "관련 기억 없음"

        lines = []
        for m in memories:
            lines.append(format_memory_for_context(
                summary=m.summary,
                turn_occurred=m.turn_occurred,
                importance=m.importance,
                emotional_valence=m.emotional_valence,
            ))
        return "\n".join(lines)

    def _format_relationship(self, rel: RelationshipMemory | None) -> str:
        """관계 정보를 문자열로 포맷팅"""
        if rel is None:
            return "처음 만남 (관계 정보 없음)"

        return format_relationship_for_context(
            target_name=rel.target_name,
            trust=rel.trust,
            fear=rel.fear,
            affinity=rel.affinity,
            relationship_label=rel.relationship_label,
        )

    def _format_goals(self) -> str:
        """활성 목표를 문자열로 포맷팅"""
        active_goals = self.memory.get_active_goals()
        if not active_goals:
            return "특별한 목표 없음 (생존)"

        lines = []
        for g in active_goals:
            lines.append(format_goal_for_context(
                description=g.description,
                priority=g.priority,
                status=g.status,
            ))
        return "\n".join(lines)

    async def decide(self, context: NPCContext) -> NPCDecision:
        """
        현재 상황에서의 의사결정.

        1. 관련 기억 검색
        2. 성격 + 감정 상태 고려
        3. LLM으로 행동/대사 생성
        """
        # 관련 기억 검색
        relevant_memories = self._get_relevant_memories(context)

        # 플레이어와의 관계
        player_rel = self.memory.get_relationship("player")

        # 프롬프트 구성
        system_prompt = self._build_system_prompt()

        user_prompt = NPC_DECIDE_PROMPT.format(
            turn_number=context.turn_context.turn_number,
            location_name=context.turn_context.location_name,
            location_description=context.turn_context.location_description,
            player_action=context.turn_context.player_action,
            panic_level=context.turn_context.panic_level,
            player_relationship=self._format_relationship(player_rel),
            relevant_memories=self._format_memories(relevant_memories),
            active_goals=self._format_goals(),
            nearby_context=self._format_nearby_context(context),
            npc_name=self.npc.name,
        )

        # LLM 호출
        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        # 응답 파싱
        return self._parse_decision(response.content)

    async def respond_to(
        self,
        speaker_id: str,
        speaker_name: str,
        message: str,
        context: NPCContext,
    ) -> NPCDecision:
        """
        다른 NPC/플레이어의 말에 반응.
        """
        # 화자와의 관계
        speaker_rel = self.memory.get_relationship(speaker_id)

        # 관련 기억 (화자 관련)
        all_memories = self.memory.get_all_memories()
        relevant_memories = self.search.search_by_entity(
            memories=all_memories,
            entity_id=speaker_id,
            entity_type="player" if speaker_id == "player" else "npc",
            limit=3,
        )

        # 프롬프트 구성
        system_prompt = self._build_system_prompt()

        user_prompt = NPC_RESPOND_PROMPT.format(
            speaker_name=speaker_name,
            message=message,
            context=f"턴 {context.turn_context.turn_number}, 위치: {context.turn_context.location_name}",
            speaker_relationship=self._format_relationship(speaker_rel),
            relevant_memories=self._format_memories(relevant_memories),
            npc_name=self.npc.name,
        )

        # LLM 호출
        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        return self._parse_decision(response.content)

    def _format_nearby_context(self, context: NPCContext) -> str:
        """주변 상황 포맷팅"""
        lines = []

        # 주변 NPC
        if context.turn_context.nearby_npc_names:
            lines.append(f"주변 인물: {', '.join(context.turn_context.nearby_npc_names)}")

        # 최근 이벤트
        if context.turn_context.recent_events:
            lines.append("최근 일어난 일:")
            for event in context.turn_context.recent_events[-3:]:
                lines.append(f"  - {event}")

        return "\n".join(lines) if lines else "특별한 상황 없음"

    def _parse_decision(self, response: str) -> NPCDecision:
        """LLM 응답을 NPCDecision으로 파싱"""
        # JSON 추출 시도
        json_match = re.search(r"\{[\s\S]*\}", response)

        if json_match:
            try:
                data = json.loads(json_match.group())
                return NPCDecision(
                    npc_id=self.npc.id,
                    npc_name=self.npc.name,
                    action_type=data.get("action_type", "none"),
                    action_description=data.get("action_description", ""),
                    dialogue=data.get("dialogue"),
                    dialogue_target=data.get("dialogue_target"),
                    dialogue_tone=data.get("dialogue_tone", "neutral"),
                    internal_thought=data.get("internal_thought"),
                    new_emotional_state=data.get("new_emotional_state"),
                    memory_summary=data.get("memory_summary"),
                    memory_importance=data.get("memory_importance", 5),
                )
            except json.JSONDecodeError:
                pass

        # 파싱 실패 시 기본 반응
        return NPCDecision(
            npc_id=self.npc.id,
            npc_name=self.npc.name,
            action_type="observe",
            action_description="상황을 지켜본다",
            internal_thought="무슨 일이지...",
            new_emotional_state=self.npc.emotional_state,
        )

    def decide_simple(self, threat_level: int) -> NPCDecision:
        """
        규칙 기반 간단한 의사결정 (LLM 없이).

        비용 절약을 위해 단순한 상황에서 사용.
        """
        personality = self.npc.personality
        player_rel = self.memory.get_relationship("player")
        fear = player_rel.fear if player_rel else 0

        action_type = "observe"
        action_description = "상황을 지켜본다"
        dialogue = None

        # 공포가 높고 용기가 낮으면 도망
        if fear > 70 and personality.bravery < 30:
            action_type = "flee"
            action_description = "도망치려 한다"
            dialogue = "으... 으악!"

        # 적대적이고 공격성이 높으면 공격
        elif self.npc.disposition == "hostile" and personality.aggression > 60:
            action_type = "attack"
            action_description = "공격적으로 다가온다"
            dialogue = "죽여버릴 거야!"

        # 플레이어와 친밀하면 도움
        elif player_rel and player_rel.affinity > 50:
            action_type = "help"
            action_description = "도우려 한다"
            dialogue = "괜찮아요?"

        # 위협 수준이 높으면 숨기
        elif threat_level > 50:
            action_type = "react"
            action_description = "움츠러든다"

        return NPCDecision(
            npc_id=self.npc.id,
            npc_name=self.npc.name,
            action_type=action_type,
            action_description=action_description,
            dialogue=dialogue,
            dialogue_tone="fearful" if fear > 50 else "neutral",
            new_emotional_state="terrified" if fear > 70 else self.npc.emotional_state,
        )

    def apply_decision(self, decision: NPCDecision) -> None:
        """의사결정 결과를 NPC 상태에 적용"""
        # 감정 상태 업데이트
        if decision.new_emotional_state:
            self.npc.emotional_state = decision.new_emotional_state

        # 현재 목표 업데이트
        if decision.action_type == "flee":
            self.npc.current_goal = "flee"
        elif decision.action_type == "attack":
            self.npc.current_goal = "fight"
        elif decision.action_type == "help":
            self.npc.current_goal = "help_player"
