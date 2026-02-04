"""
기억 영속성 관리

JSON 파일로 기억을 저장하고 로드합니다.
서버 재시작 시에도 기억이 유지됩니다.
"""

import json
from pathlib import Path
from datetime import datetime

from domain.orv.model.memory import (
    MemoryEntry,
    NPCMemoryStore,
    RelationshipMemory,
    NPCGoal,
)


class MemoryPersistence:
    """
    JSON 파일 기반 기억 영속성 관리.

    저장 구조:
    data/
    └── memories/
        └── {session_id}/
            └── {npc_id}/
                ├── memories.json       # 단기 + 장기 기억
                ├── relationships.json  # 관계 데이터
                └── goals.json          # 목표
    """

    def __init__(self, data_dir: str | Path = "data"):
        self.data_dir = Path(data_dir)
        self.memories_dir = self.data_dir / "memories"

    def _ensure_dir(self, path: Path) -> None:
        """디렉토리 생성"""
        path.mkdir(parents=True, exist_ok=True)

    def _get_npc_dir(self, session_id: str, npc_id: str) -> Path:
        """NPC 데이터 디렉토리 경로"""
        return self.memories_dir / session_id / npc_id

    def save_store(self, session_id: str, store: NPCMemoryStore) -> None:
        """NPC 기억 저장소 저장"""
        npc_dir = self._get_npc_dir(session_id, store.npc_id)
        self._ensure_dir(npc_dir)

        # 기억 저장
        memories_data = {
            "npc_id": store.npc_id,
            "npc_name": store.npc_name,
            "short_term_memories": [
                self._memory_to_dict(m) for m in store.short_term_memories
            ],
            "long_term_memories": [
                self._memory_to_dict(m) for m in store.long_term_memories
            ],
            "working_memory": store.working_memory,
        }
        self._write_json(npc_dir / "memories.json", memories_data)

        # 관계 저장
        relationships_data = {
            target_id: self._relationship_to_dict(rel)
            for target_id, rel in store.relationships.items()
        }
        self._write_json(npc_dir / "relationships.json", relationships_data)

        # 목표 저장
        goals_data = [self._goal_to_dict(g) for g in store.goals]
        self._write_json(npc_dir / "goals.json", goals_data)

    def load_store(self, session_id: str, npc_id: str) -> NPCMemoryStore | None:
        """NPC 기억 저장소 로드"""
        npc_dir = self._get_npc_dir(session_id, npc_id)

        memories_file = npc_dir / "memories.json"
        if not memories_file.exists():
            return None

        # 기억 로드
        memories_data = self._read_json(memories_file)
        if memories_data is None:
            return None

        store = NPCMemoryStore(
            npc_id=memories_data["npc_id"],
            npc_name=memories_data.get("npc_name", "Unknown"),
            short_term_memories=[
                self._dict_to_memory(m) for m in memories_data.get("short_term_memories", [])
            ],
            long_term_memories=[
                self._dict_to_memory(m) for m in memories_data.get("long_term_memories", [])
            ],
            working_memory=memories_data.get("working_memory", []),
        )

        # 관계 로드
        relationships_file = npc_dir / "relationships.json"
        if relationships_file.exists():
            relationships_data = self._read_json(relationships_file)
            if relationships_data:
                store.relationships = {
                    target_id: self._dict_to_relationship(rel_data)
                    for target_id, rel_data in relationships_data.items()
                }

        # 목표 로드
        goals_file = npc_dir / "goals.json"
        if goals_file.exists():
            goals_data = self._read_json(goals_file)
            if goals_data:
                store.goals = [self._dict_to_goal(g) for g in goals_data]

        return store

    def save_all_stores(
        self,
        session_id: str,
        stores: dict[str, NPCMemoryStore],
    ) -> None:
        """세션의 모든 NPC 기억 저장"""
        for store in stores.values():
            self.save_store(session_id, store)

    def load_all_stores(self, session_id: str) -> dict[str, NPCMemoryStore]:
        """세션의 모든 NPC 기억 로드"""
        session_dir = self.memories_dir / session_id
        if not session_dir.exists():
            return {}

        stores = {}
        for npc_dir in session_dir.iterdir():
            if npc_dir.is_dir():
                npc_id = npc_dir.name
                store = self.load_store(session_id, npc_id)
                if store:
                    stores[npc_id] = store

        return stores

    def delete_session(self, session_id: str) -> None:
        """세션 기억 삭제"""
        session_dir = self.memories_dir / session_id
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)

    def list_sessions(self) -> list[str]:
        """저장된 세션 목록"""
        if not self.memories_dir.exists():
            return []
        return [d.name for d in self.memories_dir.iterdir() if d.is_dir()]

    # === 직렬화/역직렬화 헬퍼 ===

    def _memory_to_dict(self, memory: MemoryEntry) -> dict:
        """MemoryEntry를 딕셔너리로 변환"""
        data = memory.model_dump()
        # datetime을 ISO 문자열로
        data["timestamp"] = memory.timestamp.isoformat()
        if memory.last_accessed:
            data["last_accessed"] = memory.last_accessed.isoformat()
        return data

    def _dict_to_memory(self, data: dict) -> MemoryEntry:
        """딕셔너리를 MemoryEntry로 변환"""
        # ISO 문자열을 datetime으로
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if isinstance(data.get("last_accessed"), str):
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        return MemoryEntry(**data)

    def _relationship_to_dict(self, rel: RelationshipMemory) -> dict:
        """RelationshipMemory를 딕셔너리로 변환"""
        return rel.model_dump()

    def _dict_to_relationship(self, data: dict) -> RelationshipMemory:
        """딕셔너리를 RelationshipMemory로 변환"""
        return RelationshipMemory(**data)

    def _goal_to_dict(self, goal: NPCGoal) -> dict:
        """NPCGoal을 딕셔너리로 변환"""
        return goal.model_dump()

    def _dict_to_goal(self, data: dict) -> NPCGoal:
        """딕셔너리를 NPCGoal로 변환"""
        return NPCGoal(**data)

    def _write_json(self, path: Path, data: dict | list) -> None:
        """JSON 파일 쓰기"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _read_json(self, path: Path) -> dict | list | None:
        """JSON 파일 읽기"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None


class SessionPersistence:
    """
    게임 세션 전체 영속성 관리.

    GameState + NPC 기억을 함께 저장/로드합니다.
    """

    def __init__(self, data_dir: str | Path = "data"):
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / "sessions"
        self.memory_persistence = MemoryPersistence(data_dir)

    def _ensure_dir(self) -> None:
        """디렉토리 생성"""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save_session(
        self,
        session_id: str,
        game_state_dict: dict,
        memory_stores: dict[str, NPCMemoryStore] | None = None,
    ) -> None:
        """게임 세션 저장"""
        self._ensure_dir()

        # GameState 저장 (NPC 기억 제외)
        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(game_state_dict, f, ensure_ascii=False, indent=2, default=str)

        # NPC 기억 저장
        if memory_stores:
            self.memory_persistence.save_all_stores(session_id, memory_stores)

    def load_session(self, session_id: str) -> tuple[dict | None, dict[str, NPCMemoryStore]]:
        """게임 세션 로드"""
        session_file = self.sessions_dir / f"{session_id}.json"

        # GameState 로드
        game_state_dict = None
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    game_state_dict = json.load(f)
            except json.JSONDecodeError:
                pass

        # NPC 기억 로드
        memory_stores = self.memory_persistence.load_all_stores(session_id)

        return game_state_dict, memory_stores

    def delete_session(self, session_id: str) -> None:
        """세션 삭제"""
        # GameState 삭제
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        # NPC 기억 삭제
        self.memory_persistence.delete_session(session_id)

    def list_sessions(self) -> list[str]:
        """저장된 세션 목록"""
        if not self.sessions_dir.exists():
            return []

        return [
            f.stem for f in self.sessions_dir.iterdir()
            if f.is_file() and f.suffix == ".json"
        ]
