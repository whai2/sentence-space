"""멸살법 저장소"""
from .pinecone_repository import PineconeBeastRepository
from .neo4j_repository import Neo4jMyeolsalRepository

__all__ = [
    "PineconeBeastRepository",
    "Neo4jMyeolsalRepository",
]
