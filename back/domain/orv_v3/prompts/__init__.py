"""
ORV v3 프롬프트 모듈

모듈형 구조 - 각 섹션을 독립적으로 교체 가능
"""
from .system_prompt import build_system_prompt
from .style_guide import STYLE_GUIDE
from .reference_texts import REFERENCE_TEXTS

__all__ = [
    "build_system_prompt",
    "STYLE_GUIDE",
    "REFERENCE_TEXTS",
]
