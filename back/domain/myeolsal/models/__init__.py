"""멸살법 데이터 모델"""
from .beast import (
    BeastLayer,
    StatGrade,
    BeastStats,
    CombatPattern,
    BeastEntry,
)
from .rules import (
    GradeStatRange,
    SpeciesTraits,
    ElementalAffinity,
    MyeolsalRules,
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
