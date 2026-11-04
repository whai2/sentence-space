"""멸살법 데이터 모델"""
from .beast import (
    BeastEntry,
    BeastLayer,
    BeastStats,
    CombatPattern,
    StatGrade,
)
from .rules import (
    ElementalAffinity,
    GradeStatRange,
    MyeolsalRules,
    SpeciesTraits,
)

__all__ = [
    "BeastLayer",
    "StatGrade",
    "BeastStats",
    "CombatPattern",
    "BeastEntry",
    "GradeStatRange",
    "SpeciesTraits",
    "ElementalAffinity",
    "MyeolsalRules",
]
