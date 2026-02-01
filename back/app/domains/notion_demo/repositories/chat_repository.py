"""Chat Repository for MongoDB operations"""

from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.domains.notion_demo.models.documents import ChatDocument


class ChatRepository:
    """
    채팅 메시지 데이터 관리 리포지토리

    Attributes:
        collection: MongoDB notion_chats 컬렉션
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Args:
            db: MongoDB 데이터베이스 인스턴스
        """
        self.collection = db["notion_chats"]

    async def create_chat(self, chat_doc: ChatDocument) -> str:
        """
        새 채팅 메시지 생성

        Args:
            chat_doc: 채팅 문서

        Returns:
            str: 생성된 문서의 ObjectId (문자열)
        """
        if not chat_doc.created_at:
            chat_doc.created_at = datetime.utcnow()

        chat_doc.updated_at = datetime.utcnow()

        result = await self.collection.insert_one(chat_doc.to_dict())
        return str(result.inserted_id)

    async def get_chat(self, chat_id: str) -> Optional[ChatDocument]:
        """
        채팅 ID로 채팅 조회

        Args:
            chat_id: 채팅 ObjectId (문자열)

        Returns:
            Optional[ChatDocument]: 채팅 문서 또는 None
        """
        if not ObjectId.is_valid(chat_id):
            return None

        doc = await self.collection.find_one({"_id": ObjectId(chat_id)})
        if doc:
            return ChatDocument.from_dict(doc)
        return None

    async def get_chats_by_session(
        self, session_id: str, limit: int = 100, skip: int = 0
    ) -> List[ChatDocument]:
        """
        세션 ID로 채팅 메시지 목록 조회 (생성 시간 순)

        Args:
            session_id: 세션 고유 ID
            limit: 조회할 최대 개수
            skip: 건너뛸 개수 (페이징)

        Returns:
            List[ChatDocument]: 채팅 문서 리스트
        """
        cursor = (
            self.collection.find({"session_id": session_id})
            .sort("created_at", 1)
            .skip(skip)
            .limit(limit)
        )

        chats = []
        async for doc in cursor:
            chats.append(ChatDocument.from_dict(doc))

        return chats

    async def get_latest_chat(self, session_id: str) -> Optional[ChatDocument]:
        """
        세션의 가장 최근 채팅 조회

        Args:
            session_id: 세션 고유 ID

        Returns:
            Optional[ChatDocument]: 최근 채팅 문서 또는 None
        """
        doc = await self.collection.find_one(
            {"session_id": session_id}, sort=[("created_at", -1)]
        )
        if doc:
            return ChatDocument.from_dict(doc)
        return None

    async def get_chat_count(self, session_id: str) -> int:
        """
        세션의 채팅 메시지 개수 조회

        Args:
            session_id: 세션 고유 ID

        Returns:
            int: 채팅 메시지 개수
        """
        return await self.collection.count_documents({"session_id": session_id})

    async def delete_chats_by_session(self, session_id: str) -> int:
        """
        세션의 모든 채팅 삭제

        Args:
            session_id: 세션 고유 ID

        Returns:
            int: 삭제된 문서 개수
        """
        result = await self.collection.delete_many({"session_id": session_id})
        return result.deleted_count

    async def create_indexes(self) -> None:
        """
        컬렉션 인덱스 생성
        """
        await self.collection.create_index("session_id")
        await self.collection.create_index("created_at")
        await self.collection.create_index([("session_id", 1), ("created_at", 1)])
