"""
NPC 기억 저장소 관리

각 NPC의 기억을 관리하고 검색 기능을 제공합니다.
"""

import uuid
from datetime import datetime

from domain.orv.model.memory import (
    MemoryEntry,
    NPCMemoryStore,
    RelationshipMemory,
    NPCGoal,
)


class MemoryManager:
    """
    세션 내 모든 NPC의 기억을 관리하는 매니저.

    기능:
    - NPC별 기억 저장소 관리
    - 기억 추가/조회
    - 관계 업데이트
    - 목표 관리
    """

    def __init__(self) -> None:
        self._stores: dict[str, NPCMemoryStore] = {}

    def get_or_create_store(self, npc_id: str, npc_name: str) -> NPCMemoryStore:
        """NPC의 기억 저장소 조회 또는 생성"""
        if npc_id not in self._stores:
            self._stores[npc_id] = NPCMemoryStore(npc_id=npc_id, npc_name=npc_name)
        return self._stores[npc_id]

    def get_store(self, npc_id: str) -> NPCMemoryStore | None:
        """NPC의 기억 저장소 조회"""
        return self._stores.get(npc_id)

    def add_memory(
        self,
        npc_id: str,
        npc_name: str,
        event_type: str,
        summary: str,
        turn: int,
        location: str,
        involves_player: bool = False,
        involves_npcs: list[str] | None = None,
        speaker_id: str | None = None,
        importance: int = 5,
        emotional_valence: float = 0,
        emotional_intensity: float = 0.5,
        keywords: list[str] | None = None,
        detailed_content: str | None = None,
    ) -> MemoryEntry:
        """기억 추가"""
        store = self.get_or_create_store(npc_id, npc_name)

        memory = MemoryEntry(
            memory_id=str(uuid.uuid4())[:8],
            npc_id=npc_id,
            event_type=event_type,
            summary=summary,
            detailed_content=detailed_content,
            turn_occurred=turn,
            location=location,
            involves_player=involves_player,
            involves_npcs=involves_npcs or [],
            speaker_id=speaker_id,
            importance=importance,
            emotional_valence=emotional_valence,
            emotional_intensity=emotional_intensity,
            keywords=keywords or self._extract_keywords(summary),
        )

        store.add_memory(memory)
        return memory

    def _extract_keywords(self, text: str) -> list[str]:
        """텍스트에서 키워드 추출 (간단한 구현)"""
        # 불용어 목록
        stopwords = {
            "이", "가", "은", "는", "을", "를", "의", "에", "에서", "로", "으로",
            "와", "과", "도", "만", "만큼", "처럼", "같이", "보다", "부터", "까지",
            "하다", "되다", "있다", "없다", "이다", "아니다",
            "그", "저", "이것", "저것", "그것", "여기", "저기", "거기",
            "나", "너", "우리", "당신", "그녀", "그들",
        }

        # 단어 분리 및 필터링
        words = text.replace(".", " ").replace(",", " ").replace("!", " ").replace("?", " ").split()
        keywords = []

        for word in words:
            word = word.strip()
            if len(word) >= 2 and word not in stopwords:
                keywords.append(word)

        return list(set(keywords))[:10]  # 최대 10개

    def update_relationship(
        self,
        npc_id: str,
        npc_name: str,
        target_id: str,
        target_type: str,
        target_name: str,
        interaction_type: str,
        intensity: int = 10,
        turn: int | None = None,
    ) -> RelationshipMemory:
        """관계 업데이트"""
        store = self.get_or_create_store(npc_id, npc_name)
        return store.update_relationship(
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            interaction_type=interaction_type,
            intensity=intensity,
            turn=turn,
        )

    def get_relationship(
        self,
        npc_id: str,
        target_id: str,
    ) -> RelationshipMemory | None:
        """관계 조회"""
        store = self.get_store(npc_id)
        if store is None:
            return None
        return store.get_relationship(target_id)

    def add_goal(
        self,
        npc_id: str,
        npc_name: str,
        goal_type: str,
        description: str,
        turn: int,
        priority: int = 5,
        target_entity_id: str | None = None,
        deadline_turn: int | None = None,
    ) -> NPCGoal:
        """목표 추가"""
        store = self.get_or_create_store(npc_id, npc_name)

        goal = NPCGoal(
            goal_id=str(uuid.uuid4())[:8],
            goal_type=goal_type,
            description=description,
            priority=priority,
            target_entity_id=target_entity_id,
            created_turn=turn,
            deadline_turn=deadline_turn,
        )

        store.goals.append(goal)
        return goal

    def complete_goal(self, npc_id: str, goal_id: str) -> bool:
        """목표 완료 처리"""
        store = self.get_store(npc_id)
        if store is None:
            return False

        for goal in store.goals:
            if goal.goal_id == goal_id:
                goal.status = "completed"
                goal.progress = 1.0
                return True
        return False

    def get_all_memories(self, npc_id: str) -> list[MemoryEntry]:
        """NPC의 모든 기억 반환"""
        store = self.get_store(npc_id)
        if store is None:
            return []
        return store.get_all_memories()

    def get_recent_memories(self, npc_id: str, limit: int = 5) -> list[MemoryEntry]:
        """NPC의 최근 기억 반환"""
        store = self.get_store(npc_id)
        if store is None:
            return []

        memories = store.short_term_memories
        return sorted(memories, key=lambda m: m.turn_occurred, reverse=True)[:limit]

    def clear_working_memory(self, npc_id: str) -> None:
        """작업 기억 초기화"""
        store = self.get_store(npc_id)
        if store:
            store.clear_working_memory()

    def set_working_memory(self, npc_id: str, context: list[str]) -> None:
        """작업 기억 설정"""
        store = self.get_store(npc_id)
        if store:
            store.working_memory = context

    def get_stores(self) -> dict[str, NPCMemoryStore]:
        """모든 저장소 반환 (영속성용)"""
        return self._stores

    def load_stores(self, stores: dict[str, NPCMemoryStore]) -> None:
        """저장소 로드 (영속성용)"""
        self._stores = stores

    def broadcast_memory(
        self,
        npc_ids: list[str],
        event_type: str,
        summary: str,
        turn: int,
        location: str,
        importance: int = 5,
        emotional_valence: float = 0,
        speaker_id: str | None = None,
    ) -> None:
        """여러 NPC에게 동일한 기억 추가 (목격 등)"""
        for npc_id in npc_ids:
            store = self.get_store(npc_id)
            if store:
                self.add_memory(
                    npc_id=npc_id,
                    npc_name=store.npc_name,
                    event_type=event_type,
                    summary=summary,
                    turn=turn,
                    location=location,
                    importance=importance,
                    emotional_valence=emotional_valence,
                    speaker_id=speaker_id,
                )
