"""MongoDB connection manager"""

import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Global MongoDB client
_mongo_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    """
    MongoDB 연결 초기화
    FastAPI lifespan의 startup 이벤트에서 호출
    """
    global _mongo_client, _database

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI environment variable is not set")

    _mongo_client = AsyncIOMotorClient(mongo_uri)
    _database = _mongo_client.get_default_database()

    # 연결 테스트
    await _database.command("ping")
    print(f"✓ Connected to MongoDB: {_database.name}")


async def close_mongo_connection() -> None:
    """
    MongoDB 연결 종료
    FastAPI lifespan의 shutdown 이벤트에서 호출
    """
    global _mongo_client

    if _mongo_client:
        _mongo_client.close()
        print("✓ MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """
    현재 데이터베이스 인스턴스 반환

    Returns:
        AsyncIOMotorDatabase: MongoDB 데이터베이스 인스턴스

    Raises:
        RuntimeError: MongoDB가 초기화되지 않은 경우
    """
    if _database is None:
        raise RuntimeError(
            "MongoDB is not initialized. Call connect_to_mongo() first."
        )
    return _database


def get_client() -> AsyncIOMotorClient:
    """
    현재 MongoDB 클라이언트 반환

    Returns:
        AsyncIOMotorClient: MongoDB 클라이언트 인스턴스

    Raises:
        RuntimeError: MongoDB가 초기화되지 않은 경우
    """
    if _mongo_client is None:
        raise RuntimeError(
            "MongoDB is not initialized. Call connect_to_mongo() first."
        )
    return _mongo_client
