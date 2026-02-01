"""Session Repository for MongoDB operations"""

from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domains.clickup_demo.models.documents import SessionDocument


class SessionRepository:
    """
    세션 데이터 관리 리포지토리

    Attributes:
        collection: MongoDB sessions 컬렉션
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Args:
            db: MongoDB 데이터베이스 인스턴스
        """
        self.collection = db["sessions"]

    async def create_session(
        self, session_id: str, metadata: dict = None
    ) -> SessionDocument:
        """
        새 세션 생성

        Args:
            session_id: 세션 고유 ID
            metadata: 세션 메타데이터 (선택)

        Returns:
            SessionDocument: 생성된 세션 문서

        Raises:
            Exception: 세션 생성 실패 시
        """
        session_doc = SessionDocument(
            session_id=session_id,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        result = await self.collection.insert_one(session_doc.to_dict())
        session_doc.id = result.inserted_id

        return session_doc

    async def get_session(self, session_id: str) -> Optional[SessionDocument]:
        """
        세션 ID로 세션 조회

        Args:
            session_id: 세션 고유 ID

        Returns:
            Optional[SessionDocument]: 세션 문서 또는 None
        """
        doc = await self.collection.find_one({"session_id": session_id})
        if doc:
            return SessionDocument.from_dict(doc)
        return None

    async def get_all_sessions(
        self, limit: int = 100, skip: int = 0
    ) -> List[SessionDocument]:
        """
        모든 세션 목록 조회 (업데이트 시간 역순)

        Args:
            limit: 조회할 최대 개수
            skip: 건너뛸 개수

        Returns:
            List[SessionDocument]: 세션 문서 리스트
        """
        cursor = (
            self.collection.find({})
            .sort("updated_at", -1)  # 최신순
            .skip(skip)
            .limit(limit)
        )

        sessions = []
        async for doc in cursor:
            sessions.append(SessionDocument.from_dict(doc))

        return sessions

    async def session_exists(self, session_id: str) -> bool:
        """
        세션 존재 여부 확인

        Args:
            session_id: 세션 고유 ID

        Returns:
            bool: 세션 존재 여부
        """
        count = await self.collection.count_documents({"session_id": session_id})
        return count > 0

    async def update_session(self, session_id: str, update_data: dict) -> bool:
        """
        세션 업데이트

        Args:
            session_id: 세션 고유 ID
            update_data: 업데이트할 데이터

        Returns:
            bool: 업데이트 성공 여부
        """
        update_data["updated_at"] = datetime.utcnow()

        result = await self.collection.update_one(
            {"session_id": session_id}, {"$set": update_data}
        )

        return result.modified_count > 0

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 고유 ID

        Returns:
            bool: 삭제 성공 여부
        """
        result = await self.collection.delete_one({"session_id": session_id})
        return result.deleted_count > 0

    async def get_session_count(self) -> int:
        """
        전체 세션 개수 조회

        Returns:
            int: 전체 세션 개수
        """
        return await self.collection.count_documents({})

    async def create_indexes(self) -> None:
        """
        컬렉션 인덱스 생성
        세션 ID에 대한 unique 인덱스 생성
        """
        await self.collection.create_index("session_id", unique=True)

    async def get_sessions_by_metadata(
        self, metadata_filter: dict, limit: int = 100, skip: int = 0
    ) -> List[SessionDocument]:
        """
        메타데이터 기반 세션 목록 조회 (업데이트 시간 역순)

        Args:
            metadata_filter: 메타데이터 필터 조건 (예: {"agent_type": "multi_agent"})
            limit: 조회할 최대 개수
            skip: 건너뛸 개수

        Returns:
            List[SessionDocument]: 세션 문서 리스트
        """
        query = {f"metadata.{k}": v for k, v in metadata_filter.items()}
        cursor = (
            self.collection.find(query)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )

        sessions = []
        async for doc in cursor:
            sessions.append(SessionDocument.from_dict(doc))

        return sessions

    async def count_sessions_by_metadata(self, metadata_filter: dict) -> int:
        """
        메타데이터 기반 세션 개수 조회

        Args:
            metadata_filter: 메타데이터 필터 조건

        Returns:
            int: 세션 개수
        """
        query = {f"metadata.{k}": v for k, v in metadata_filter.items()}
        return await self.collection.count_documents(query)
