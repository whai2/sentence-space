"""MongoDB 인덱스 생성 스크립트"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# 환경 변수 로드
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


async def create_indexes():
    """
    MongoDB 컬렉션 인덱스 생성

    Sessions 컬렉션:
    - session_id (unique)

    Chats 컬렉션:
    - session_id
    - created_at
    - (session_id, created_at) 복합 인덱스
    """
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("Error: MONGO_URI environment variable is not set")
        return

    client = AsyncIOMotorClient(mongo_uri)
    db = client.get_default_database()

    print(f"Connected to MongoDB: {db.name}")
    print("Creating indexes...")

    # Sessions 컬렉션 인덱스
    sessions_collection = db["sessions"]
    await sessions_collection.create_index("session_id", unique=True)
    print("✓ Created unique index on sessions.session_id")

    # Chats 컬렉션 인덱스
    chats_collection = db["chats"]
    await chats_collection.create_index("session_id")
    print("✓ Created index on chats.session_id")

    await chats_collection.create_index("created_at")
    print("✓ Created index on chats.created_at")

    # 복합 인덱스: 세션별 시간순 조회 최적화
    await chats_collection.create_index([("session_id", 1), ("created_at", 1)])
    print("✓ Created compound index on chats.(session_id, created_at)")

    # 인덱스 목록 확인
    print("\nSessions collection indexes:")
    async for index in sessions_collection.list_indexes():
        print(f"  - {index['name']}: {index.get('key', {})}")

    print("\nChats collection indexes:")
    async for index in chats_collection.list_indexes():
        print(f"  - {index['name']}: {index.get('key', {})}")

    client.close()
    print("\n✓ All indexes created successfully")


if __name__ == "__main__":
    asyncio.run(create_indexes())
