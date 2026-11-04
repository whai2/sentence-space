"""
ORV v2 Models

MongoDB 문서 구조 + LLM Structured Output
"""
from .agent_output import (
    NarratorOutput,
    OrchestratorDecision,
    StateChange,
    TurnResult,
)
from .base import (
    AttributePoints,
    Coordinate,
    CurrentScenario,
    GameMode,
    GameState,
    ItemInstance,
    NPCPersonality,
    NPCRelationship,
    NPCState,
    PlayerState,
    SkillInstance,
)
from .graph_state import GraphState
from .scenario import (
    KeyDecision,
    NPCSpawn,
    ScenarioContext,
    ScenarioPhase,
    ScenarioSummary,
    ScenarioTemplate,
)

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
