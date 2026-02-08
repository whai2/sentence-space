"""
멸살법 규칙 DB

등급별 스탯 범위, 종별 특성, 속성 상성 정의
"""
from pydantic import BaseModel, Field


class GradeStatRange(BaseModel):
    """등급별 스탯 범위"""
    grade: str = Field(description="등급 (9급 ~ 특급)")
    hp_range: tuple[str, str] = Field(description="HP 범위 (min, max)")
    atk_range: tuple[str, str] = Field(description="ATK 범위")
    def_range: tuple[str, str] = Field(description="DEF 범위")
    spd_range: tuple[str, str] = Field(description="SPD 범위")
    spc_range: tuple[str, str] = Field(description="SPC 범위")


class SpeciesTraits(BaseModel):
    """종별 특성"""
    species: str = Field(description="종 이름")
    physical_vulnerability: str = Field(description="물리 취약도 (high, medium, low)")
    elemental_weakness_clarity: str = Field(description="속성 약점 명확도")
    behavior_predictability: str = Field(description="행동 예측 가능성")
    intelligence: str = Field(description="지능 수준 (low, medium, high, genius)")
    negotiable: bool = Field(description="협상 가능 여부")
    special_traits: list[str] = Field(default_factory=list, description="특수 특성")


class ElementalAffinity(BaseModel):
    """속성 상성"""
    element: str = Field(description="속성 이름")
    strong_against: list[str] = Field(default_factory=list, description="유리한 속성")
    weak_against: list[str] = Field(default_factory=list, description="불리한 속성")
    neutral: list[str] = Field(default_factory=list, description="상성 없음")


class DangerClassCriteria(BaseModel):
    """위험도 분류 기준"""
    danger_class: str = Field(description="위험도 등급")
    description: str = Field(description="분류 기준 설명")
    grade_range: list[str] = Field(description="해당 등급 범위")


class MyeolsalRules(BaseModel):
    """
    멸살법 규칙 DB (Layer 0)

    가장 높은 신뢰도를 가지며, 다른 Layer와 충돌 시 우선함
    """
    grade_stat_ranges: list[GradeStatRange] = Field(
        default_factory=list,
        description="등급별 스탯 범위"
    )
    species_traits: list[SpeciesTraits] = Field(
        default_factory=list,
        description="종별 특성"
    )
    elemental_affinities: list[ElementalAffinity] = Field(
        default_factory=list,
        description="속성 상성표"
    )
    danger_class_criteria: list[DangerClassCriteria] = Field(
        default_factory=list,
        description="위험도 분류 기준"
    )

    def get_stat_range_for_grade(self, grade: str) -> GradeStatRange | None:
        """특정 등급의 스탯 범위 조회"""
        for range_info in self.grade_stat_ranges:
            if range_info.grade == grade:
                return range_info
        return None

    def get_species_traits(self, species: str) -> SpeciesTraits | None:
        """특정 종의 특성 조회"""
        for traits in self.species_traits:
            if traits.species == species:
                return traits
        return None

    def get_element_affinity(self, element: str) -> ElementalAffinity | None:
        """특정 속성의 상성 조회"""
        for affinity in self.elemental_affinities:
            if affinity.element == element:
                return affinity
        return None

    def validate_stats_for_grade(self, grade: str, stats: dict) -> tuple[bool, list[str]]:
        """
        스탯이 해당 등급 범위 내인지 검증

        Returns:
            (valid, errors): 유효성 여부와 오류 메시지 리스트
        """
        range_info = self.get_stat_range_for_grade(grade)
        if not range_info:
            return False, [f"알 수 없는 등급: {grade}"]

        # 스탯 순서 매핑
        stat_order = ["E", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+", "S"]

        def in_range(value: str, min_val: str, max_val: str) -> bool:
            try:
                return stat_order.index(min_val) <= stat_order.index(value) <= stat_order.index(max_val)
            except ValueError:
                return False

        errors = []
        stat_ranges = {
            "hp": range_info.hp_range,
            "atk": range_info.atk_range,
            "defense": range_info.def_range,
            "spd": range_info.spd_range,
            "spc": range_info.spc_range,
        }

        for stat_name, (min_val, max_val) in stat_ranges.items():
            if stat_name in stats:
                if not in_range(stats[stat_name], min_val, max_val):
                    errors.append(
                        f"{stat_name}: {stats[stat_name]}은(는) {grade}의 범위 "
                        f"({min_val}~{max_val})를 벗어남"
                    )

        return len(errors) == 0, errors
