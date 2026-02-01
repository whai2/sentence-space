"""Notion Agent Constants"""

from typing import Literal


# Node Names
class NodeNames:
    """그래프 노드 이름 상수"""
    REASON = "reason"
    ACT = "act"
    OBSERVE = "observe"
    FINALIZE = "finalize"


# Edge Decision Types
EdgeDecision = Literal["act", "finalize"]


# Event Types for Streaming
class EventTypes:
    """스트리밍 이벤트 타입 상수"""
    NODE_START = "node_start"
    NODE_END = "node_end"
    TOOL_RESULT = "tool_result"
    FINAL = "final"
