"""
괴수 데이터 모델

멸살법 제1권: 괴수종 생존 도감의 핵심 스키마
"""
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class BeastLayer(str, Enum):
    """데이터 계층 (신뢰도 순)"""
    CANON = "canon"                      # Layer 1: 원작 정보 (나무위키)
    INTERPOLATED = "interpolated"        # Layer 2: LLM 보간
    GENERATED = "generated"              # Layer 3: 실시간 생성
    USER_CONTRIBUTED = "user_contributed"  # Layer 4: 사용자 기여


class StatGrade(str, Enum):
    """스탯 등급 (E ~ S)"""
    E = "E"
    D_MINUS = "D-"
    D = "D"
    D_PLUS = "D+"
    C_MINUS = "C-"
    C = "C"
    C_PLUS = "C+"
    B_MINUS = "B-"
    B = "B"
    B_PLUS = "B+"
    A_MINUS = "A-"
    A = "A"
    A_PLUS = "A+"
    S = "S"

    @classmethod
    def from_string(cls, value: str) -> "StatGrade":
        """문자열에서 StatGrade로 변환"""
        mapping = {
            "E": cls.E, "D-": cls.D_MINUS, "D": cls.D, "D+": cls.D_PLUS,
            "C-": cls.C_MINUS, "C": cls.C, "C+": cls.C_PLUS,
            "B-": cls.B_MINUS, "B": cls.B, "B+": cls.B_PLUS,
            "A-": cls.A_MINUS, "A": cls.A, "A+": cls.A_PLUS, "S": cls.S
        }
        return mapping.get(value, cls.E)

    def to_numeric(self) -> int:
        """스탯 비교를 위한 숫자 변환"""
        order = [
            "E", "D-", "D", "D+", "C-", "C", "C+",
            "B-", "B", "B+", "A-", "A", "A+", "S"
        ]
        return order.index(self.value)


class BeastStats(BaseModel):
    """괴수 스탯"""
    hp: str = Field(description="체력 (E ~ S)")
    atk: str = Field(description="공격력 (E ~ S)")
    defense: str = Field(description="방어력 (E ~ S)")  # 'def'는 예약어
    spd: str = Field(description="속도 (E ~ S)")
    spc: str = Field(description="특수 능력 (E ~ S)")


class CombatPattern(BaseModel):
    """전투 패턴"""
    name: str = Field(description="패턴 이름")
    trigger: str = Field(description="발동 조건 (always, hp_below_50, enraged 등)")
    description: str = Field(description="패턴 설명")
    damage_type: str | None = Field(default=None, description="피해 유형")
    cooldown: int | None = Field(default=None, description="쿨다운 (턴)")


class BeastEntry(BaseModel):
    """
    멸살법 괴수 항목

    ChromaDB와 Neo4j에 저장되는 핵심 엔티티
    """
    # === 메타데이터 (벡터 DB 필터링용) ===
    id: str = Field(description="고유 ID (beast_{species}_{grade}_{name})")
    layer: BeastLayer = Field(default=BeastLayer.CANON, description="데이터 계층")
    confidence: float = Field(ge=0, le=1, default=1.0, description="신뢰도")
    source: str = Field(default="", description="출처 (namu:/설정, generated:claude)")
    volume: int = Field(default=1, description="멸살법 권수")
    tags: list[str] = Field(default_factory=list, description="검색 태그")

    # === 기본 정보 ===
    title: str = Field(description="괴수 이름")
    grade: str = Field(description="등급 (9급 ~ 특급)")
    species: str = Field(description="종 (괴수종, 악마종, 거신, 재앙)")
    danger_class: str = Field(default="보통", description="위험도 (안전, 보통, 위험, 치명)")

    # === 서사 블록 (각각 독립 검색 가능) ===
    description: str = Field(description="기본 설명")
    combat_patterns: list[CombatPattern] = Field(
        default_factory=list,
        description="전투 패턴 목록"
    )
    survival_guide: str = Field(default="", description="생존 지침")
    warnings: list[str] = Field(default_factory=list, description="주의사항")
    lore_notes: str = Field(default="", description="세계관 메모 (원작 연관 정보)")

    # === 스탯 ===
    stats: BeastStats = Field(description="능력치")
    weaknesses: list[str] = Field(default_factory=list, description="약점 속성")
    resistances: list[str] = Field(default_factory=list, description="저항 속성")
    coin_reward_range: tuple[int, int] = Field(default=(0, 0), description="코인 보상 범위")

    # === 관계 (Neo4j 그래프용) ===
    related_entries: list[str] = Field(default_factory=list, description="관련 항목 ID")
    evolution_line: list[str] = Field(default_factory=list, description="진화 계통")
    appearance_scenarios: list[str] = Field(default_factory=list, description="출현 시나리오 ID")

    # === 타임스탬프 ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_searchable_text(self) -> str:
        """벡터 검색용 텍스트 생성"""
        parts = [
            f"{self.title} ({self.grade} {self.species})",
            self.description,
            self.survival_guide,
            " ".join(self.warnings),
            self.lore_notes,
        ]
        return " ".join(filter(None, parts))

    def get_combat_text(self) -> str:
        """전투 패턴 검색용 텍스트"""
        patterns = [f"{p.name}: {p.description}" for p in self.combat_patterns]
        return " ".join(patterns)

    def get_survival_text(self) -> str:
        """생존 가이드 검색용 텍스트"""
        return f"{self.survival_guide} {' '.join(self.warnings)}"
