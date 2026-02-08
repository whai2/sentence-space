"""
괴수 검증 에이전트

생성된 괴수가 세계관 규칙에 맞는지 검증
"""
from pydantic import BaseModel, Field

from domain.myeolsal.models import BeastEntry, MyeolsalRules


class ValidationResult(BaseModel):
    """검증 결과"""
    is_valid: bool = Field(description="유효 여부")
    errors: list[str] = Field(default_factory=list, description="오류 메시지")
    warnings: list[str] = Field(default_factory=list, description="경고 메시지")
    suggestions: list[str] = Field(default_factory=list, description="개선 제안")


class BeastValidatorAgent:
    """
    괴수 검증 에이전트

    생성된 괴수가 세계관 규칙을 준수하는지 검증
    """

    def __init__(self, rules: MyeolsalRules):
        """
        Args:
            rules: 멸살법 규칙
        """
        self.rules = rules

    def validate(self, beast: BeastEntry) -> ValidationResult:
        """
        괴수 전체 검증

        Args:
            beast: 검증할 괴수

        Returns:
            검증 결과
        """
        errors = []
        warnings = []
        suggestions = []

        # 1. 스탯 범위 검증
        stat_valid, stat_errors = self._validate_stats(beast)
        errors.extend(stat_errors)

        # 2. 종별 특성 검증
        species_warnings = self._validate_species_traits(beast)
        warnings.extend(species_warnings)

        # 3. 위험도 검증
        danger_valid, danger_msg = self._validate_danger_class(beast)
        if not danger_valid:
            warnings.append(danger_msg)

        # 4. 전투 패턴 검증
        combat_suggestions = self._validate_combat_patterns(beast)
        suggestions.extend(combat_suggestions)

        # 5. 필수 필드 검증
        field_errors = self._validate_required_fields(beast)
        errors.extend(field_errors)

        # 6. 속성 상성 검증
        element_warnings = self._validate_elemental_consistency(beast)
        warnings.extend(element_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def _validate_stats(self, beast: BeastEntry) -> tuple[bool, list[str]]:
        """스탯 범위 검증"""
        stats_dict = {
            "hp": beast.stats.hp,
            "atk": beast.stats.atk,
            "defense": beast.stats.defense,
            "spd": beast.stats.spd,
            "spc": beast.stats.spc,
        }
        return self.rules.validate_stats_for_grade(beast.grade, stats_dict)

    def _validate_species_traits(self, beast: BeastEntry) -> list[str]:
        """종별 특성 검증"""
        warnings = []
        traits = self.rules.get_species_traits(beast.species)

        if not traits:
            warnings.append(f"알 수 없는 종: {beast.species}")
            return warnings

        # 협상 가능 여부 체크
        if traits.negotiable and "협상" not in beast.survival_guide.lower():
            warnings.append(f"{beast.species}은(는) 협상 가능한 종이지만 생존 가이드에 협상 관련 내용이 없습니다")

        # 지능 레벨에 따른 행동 패턴 체크
        if traits.intelligence == "high":
            has_intelligent_pattern = any(
                "지능" in p.description or "전술" in p.description or "함정" in p.description
                for p in beast.combat_patterns
            )
            if not has_intelligent_pattern:
                warnings.append(f"{beast.species}은(는) 고지능 종이지만 지능적 행동 패턴이 없습니다")

        return warnings

    def _validate_danger_class(self, beast: BeastEntry) -> tuple[bool, str]:
        """위험도 등급 검증"""
        grade_to_expected_danger = {
            "9급": ["안전"],
            "8급": ["안전", "보통"],
            "7급": ["보통"],
            "6급": ["보통", "위험"],
            "5급": ["위험"],
            "4급": ["위험", "치명"],
            "3급": ["치명"],
            "2급": ["치명"],
            "1급": ["치명"],
            "특급": ["치명"],
        }

        expected = grade_to_expected_danger.get(beast.grade, [])
        if beast.danger_class not in expected:
            return False, f"{beast.grade}의 권장 위험도는 {expected}이지만 {beast.danger_class}로 설정됨"

        return True, ""

    def _validate_combat_patterns(self, beast: BeastEntry) -> list[str]:
        """전투 패턴 검증"""
        suggestions = []

        if len(beast.combat_patterns) < 2:
            suggestions.append("전투 패턴이 2개 미만입니다. 다양한 패턴 추가 권장")

        if len(beast.combat_patterns) > 5:
            suggestions.append("전투 패턴이 5개를 초과합니다. 핵심 패턴만 유지 권장")

        # trigger 다양성 체크
        triggers = [p.trigger for p in beast.combat_patterns]
        if len(set(triggers)) == 1 and len(triggers) > 1:
            suggestions.append("모든 전투 패턴의 발동 조건이 동일합니다. 다양한 조건 추가 권장")

        # hp 기반 패턴 체크
        has_hp_trigger = any("hp" in t.lower() for t in triggers)
        if not has_hp_trigger and beast.grade in ["4급", "3급", "2급", "1급", "특급"]:
            suggestions.append("고등급 괴수에 HP 기반 패턴 변화가 없습니다. 광폭화 등 추가 권장")

        return suggestions

    def _validate_required_fields(self, beast: BeastEntry) -> list[str]:
        """필수 필드 검증"""
        errors = []

        if not beast.title:
            errors.append("괴수 이름이 비어있습니다")

        if not beast.description:
            errors.append("설명이 비어있습니다")

        if not beast.survival_guide:
            errors.append("생존 가이드가 비어있습니다")

        if len(beast.weaknesses) == 0:
            errors.append("약점이 지정되지 않았습니다")

        if beast.coin_reward_range[0] > beast.coin_reward_range[1]:
            errors.append("코인 보상 범위가 잘못되었습니다 (min > max)")

        return errors

    def _validate_elemental_consistency(self, beast: BeastEntry) -> list[str]:
        """속성 상성 일관성 검증"""
        warnings = []

        # 약점과 저항이 겹치는지 체크
        overlap = set(beast.weaknesses) & set(beast.resistances)
        if overlap:
            warnings.append(f"약점과 저항에 동일 속성 존재: {overlap}")

        # 종별 기본 약점 체크
        species_weaknesses = {
            "해수종": ["화염", "전기"],
            "충왕종": ["화염"],
            "괴수종": [],
            "악마종": ["신성"],
            "거신": [],
            "재앙": [],
        }

        expected_weaknesses = species_weaknesses.get(beast.species, [])
        missing = set(expected_weaknesses) - set(beast.weaknesses)
        if missing:
            warnings.append(f"{beast.species}의 일반적 약점 {missing}이(가) 누락됨")

        return warnings

    def quick_validate(self, beast: BeastEntry) -> bool:
        """빠른 유효성 검사 (에러만 체크)"""
        result = self.validate(beast)
        return result.is_valid

    def fix_stats(self, beast: BeastEntry) -> BeastEntry:
        """
        스탯 범위 자동 수정

        범위를 벗어난 스탯을 범위 내로 조정
        """
        range_info = self.rules.get_stat_range_for_grade(beast.grade)
        if not range_info:
            return beast

        stat_order = ["E", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+", "S"]

        def clamp(value: str, min_val: str, max_val: str) -> str:
            try:
                val_idx = stat_order.index(value)
                min_idx = stat_order.index(min_val)
                max_idx = stat_order.index(max_val)
                clamped_idx = max(min_idx, min(max_idx, val_idx))
                return stat_order[clamped_idx]
            except ValueError:
                return min_val

        # 새 스탯 생성
        from domain.myeolsal.models import BeastStats

        new_stats = BeastStats(
            hp=clamp(beast.stats.hp, range_info.hp_range[0], range_info.hp_range[1]),
            atk=clamp(beast.stats.atk, range_info.atk_range[0], range_info.atk_range[1]),
            defense=clamp(beast.stats.defense, range_info.def_range[0], range_info.def_range[1]),
            spd=clamp(beast.stats.spd, range_info.spd_range[0], range_info.spd_range[1]),
            spc=clamp(beast.stats.spc, range_info.spc_range[0], range_info.spc_range[1]),
        )

        # 새 객체 반환 (불변성)
        return beast.model_copy(update={"stats": new_stats})
