"""
시나리오 설명집 데이터 모델

메인 시나리오 패키지: 규칙, 해석 레이어, 무대, 서사 정보
"""
from datetime import datetime
from pydantic import BaseModel, Field


class PlayerPath(BaseModel):
    """플레이어 가능 경로"""
    path: str = Field(description="경로 이름 (예: '곤충 처치')")
    difficulty: str = Field(description="난이도 (쉬움, 중간, 어려움, -)")
    moral_cost: str = Field(description="도덕적 비용 (없음, 낮음, 높음, -)")
    narrative_tone: str = Field(description="서사 톤 (예: '냉정한 판단력 과시')")


class ScenarioRule(BaseModel):
    """시나리오 규칙"""
    type: str = Field(description="시나리오 유형 (main, sub, hidden)")
    objective: str = Field(description="목표")
    clear_condition: str = Field(description="클리어 조건")
    failure_condition: str = Field(description="실패 조건")
    failure_penalty: str = Field(description="실패 시 결과")
    time_limit: str | None = Field(default=None, description="시간 제한")
    participants: str = Field(description="참가자")
    constraints: list[str] = Field(default_factory=list, description="제약 조건")


class Interpretation(BaseModel):
    """
    해석 레이어

    전독시 시나리오의 핵심 — 표면적 해석과 실제 해법이 다른 구조.
    TRPG 나레이터가 플레이어 선택에 따라 장면을 생성하려면 이 정보가 필요.
    """
    surface_reading: str = Field(description="표면적 해석 (대부분의 탑승자가 이해하는 방식)")
    hidden_solution: str = Field(description="숨겨진 해법 (실제 최적해)")
    protagonist_advantage: str = Field(description="주인공의 이점 (김독자가 왜 유리한지)")
    player_possible_paths: list[PlayerPath] = Field(
        default_factory=list,
        description="플레이어가 선택할 수 있는 경로들"
    )


class Stage(BaseModel):
    """무대 정보"""
    name: str = Field(description="무대 이름")
    description: str = Field(description="무대 설명")
    terrain_features: list[str] = Field(default_factory=list, description="지형 특성")
    atmosphere: str = Field(default="", description="분위기")


class Narrative(BaseModel):
    """서사 정보"""
    arc_position: str = Field(description="아크 위치 (예: '시작점 — 세계 붕괴의 첫 순간')")
    tone: str = Field(description="서사 톤 (예: '서바이벌 스릴러 + 도덕적 딜레마')")
    key_events: list[str] = Field(default_factory=list, description="핵심 이벤트")
    plot_hooks: list[str] = Field(default_factory=list, description="플롯 훅 (다음 시나리오 연결)")
    previous_scenario_summary: str = Field(default="없음", description="이전 시나리오 요약")


class ScenarioPackage(BaseModel):
    """
    시나리오 패키지

    메인 시나리오의 모든 정보를 담는 최상위 모델.
    Neo4j에 저장되는 핵심 엔티티.
    """
    id: str = Field(description="고유 ID (scenario_001, scenario_002, ...)")
    name: str = Field(description="시나리오 명칭 (예: '1차 메인 시나리오')")
    title: str = Field(description="시나리오 제목 (예: '가치 증명')")

    scenario_rule: ScenarioRule = Field(description="시나리오 규칙")
    interpretation: Interpretation = Field(description="해석 레이어")
    stage: Stage = Field(description="무대 정보")

    monster_refs: list[str] = Field(default_factory=list, description="연관 괴수 ID 목록")
    character_refs: list[str] = Field(default_factory=list, description="연관 캐릭터 참조")

    narrative: Narrative = Field(description="서사 정보")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
