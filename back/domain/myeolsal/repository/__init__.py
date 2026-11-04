"""멸살법 저장소"""
from .neo4j_repository import Neo4jMyeolsalRepository
from .pinecone_repository import PineconeBeastRepository

__all__ = [
    "PineconeBeastRepository",
    "Neo4jMyeolsalRepository",
]
