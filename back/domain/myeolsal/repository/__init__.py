"""멸살법 저장소"""
from .chroma_repository import ChromaBeastRepository
from .neo4j_repository import Neo4jMyeolsalRepository

__all__ = [
    "ChromaBeastRepository",
    "Neo4jMyeolsalRepository",
]
