"""
DI Container
"""
from .container import (
    get_game_service,
    get_repository,
    shutdown,
    startup,
)

__all__ = [
    "get_game_service",
    "get_repository",
    "startup",
    "shutdown",
]
