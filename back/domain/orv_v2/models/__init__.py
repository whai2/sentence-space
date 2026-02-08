"""
ORV v2 Models

MongoDB 문서 구조 + LLM Structured Output
"""
from .base import (
    Coordinate,
    ItemInstance,
    SkillInstance,
    AttributePoints,
    PlayerState,
    NPCRelationship,
    NPCPersonality,
    NPCState,
    CurrentScenario,
    GameMode,
    GameState,
)

from .scenario import (
    ScenarioPhase,
    NPCSpawn,
    ScenarioTemplate,
    KeyDecision,
    ScenarioSummary,
    ScenarioContext,
)

from .agent_output import (
    StateChange,
    OrchestratorDecision,
    NarratorOutput,
    TurnResult,
)

from .graph_state import GraphState

__all__ = [
    # base
    "Coordinate",
    "ItemInstance",
    "SkillInstance",
    "AttributePoints",
    "PlayerState",
    "NPCRelationship",
    "NPCPersonality",
    "NPCState",
    "CurrentScenario",
    "GameMode",
    "GameState",
    # scenario
    "ScenarioPhase",
    "NPCSpawn",
    "ScenarioTemplate",
    "KeyDecision",
    "ScenarioSummary",
    "ScenarioContext",
    # agent_output
    "StateChange",
    "OrchestratorDecision",
    "NarratorOutput",
    "TurnResult",
    # graph_state
    "GraphState",
]
