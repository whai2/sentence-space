"""Neo4j connection manager"""

import os
import logging
from typing import Optional
from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)

# Global Neo4j driver
_neo4j_driver: Optional[AsyncDriver] = None


async def connect_to_neo4j() -> None:
    """
    Neo4j 연결 초기화
    FastAPI lifespan의 startup 이벤트에서 호출
    """
    global _neo4j_driver

    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_uri:
        raise ValueError("NEO4J_URI environment variable is not set")

    _neo4j_driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password),
    )

    # 연결 테스트
    async with _neo4j_driver.session() as session:
        result = await session.run("RETURN 1 AS ping")
        await result.single()

    print(f"✓ Connected to Neo4j: {neo4j_uri}")

    # 제약 조건 및 인덱스 생성
    await _ensure_constraints_and_indexes()


async def _ensure_constraints_and_indexes() -> None:
    """Neo4j 스키마 제약 조건 및 인덱스 생성 (멱등성 보장)"""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (q:Query) REQUIRE q.query_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (k:Keyword) REQUIRE k.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (tool:Tool) REQUIRE tool.name IS UNIQUE",
    ]
    async with _neo4j_driver.session() as session:
        for cypher in constraints:
            await session.run(cypher)
    print("✓ Neo4j constraints and indexes ensured")


async def close_neo4j_connection() -> None:
    """
    Neo4j 연결 종료
    FastAPI lifespan의 shutdown 이벤트에서 호출
    """
    global _neo4j_driver

    if _neo4j_driver:
        await _neo4j_driver.close()
        print("✓ Neo4j connection closed")


def get_neo4j_driver() -> AsyncDriver:
    """
    현재 Neo4j 드라이버 인스턴스 반환

    Returns:
        AsyncDriver: Neo4j 비동기 드라이버

    Raises:
        RuntimeError: Neo4j가 초기화되지 않은 경우
    """
    if _neo4j_driver is None:
        raise RuntimeError(
            "Neo4j is not initialized. Call connect_to_neo4j() first."
        )
    return _neo4j_driver
