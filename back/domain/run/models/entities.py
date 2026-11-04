"""
런(Run) 세계관 엔티티 모델

4개 엔티티: Concept, Character, Event, WorldSetting
각각 Pinecone 벡터 + Neo4j 노드로 저장된다.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """엔티티 유형"""
    CONCEPT = "concept"
    CHARACTER = "character"
    EVENT = "event"
    WORLD_SETTING = "world_setting"


class RunEntity(BaseModel):
    """런 세계관 엔티티 공통 베이스"""
    id: str = Field(description="고유 ID (run_{type}_{name})")
    entity_type: EntityType
    title: str = Field(description="엔티티 이름")
    content: str = Field(default="", description="본문 전체")
    tags: list[str] = Field(default_factory=list)
    source_url: str = Field(default="", description="Notion 페이지 URL")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_searchable_text(self) -> str:
        """벡터 검색용 텍스트"""
        return f"{self.title}\n{self.content}"


class RunConcept(RunEntity):
    """
    세계관 개념 (31개)

    예: 기억 오염, 팬텀 커넥톰, 인지적 고리 등
    각 개념은 정의/목적/세계에서의 위치로 구성
    """
    entity_type: EntityType = EntityType.CONCEPT
    definition: str = Field(default="", description="정의")
    purpose: str = Field(default="", description="왜 존재하는가")
    world_position: str = Field(default="", description="세계에서의 위치")
    related_concepts: list[str] = Field(default_factory=list, description="관련 개념 ID")

    def get_searchable_text(self) -> str:
        parts = [
            self.title,
            f"정의: {self.definition}",
            f"목적: {self.purpose}",
            f"세계에서의 위치: {self.world_position}",
        ]
        return "\n".join(filter(None, parts))


class RunCharacter(RunEntity):
    """
    인물 (9명)

    예: 주인공, 테스, 카우트, 린, 세르게이 등
    기본 정보 + 사건 연표로 구성
    """
    entity_type: EntityType = EntityType.CHARACTER
    role: str = Field(default="", description="직업/역할")
    traits: list[str] = Field(default_factory=list, description="특징")
    abilities: list[str] = Field(default_factory=list, description="능력")
    affiliations: list[str] = Field(default_factory=list, description="소속 조직")
    timeline: list[str] = Field(default_factory=list, description="사건 연표")
    status: str = Field(default="", description="현재 상태")

    def get_searchable_text(self) -> str:
        parts = [
            self.title,
            f"역할: {self.role}",
            f"특징: {', '.join(self.traits)}" if self.traits else "",
            f"능력: {', '.join(self.abilities)}" if self.abilities else "",
            f"소속: {', '.join(self.affiliations)}" if self.affiliations else "",
            self.content,
        ]
        return "\n".join(filter(None, parts))

    def get_timeline_text(self) -> str:
        """사건 연표 검색용 텍스트"""
        return f"{self.title} 사건 연표:\n" + "\n".join(
            f"{i+1}. {event}" for i, event in enumerate(self.timeline)
        )


class RunEvent(RunEntity):
    """
    사건 (타임라인)

    예: 노틸러스 프로젝트, 38층 침투 작전, 노르드 괴멸 보고 등
    시간순 정렬 + 참여 인물/개념 연결
    """
    entity_type: EntityType = EntityType.EVENT
    time_period: str = Field(default="", description="시기 (원과거/근과거/현재_날1)")
    location: str = Field(default="", description="장소")
    participants: list[str] = Field(default_factory=list, description="참여 인물 ID")
    concepts_used: list[str] = Field(default_factory=list, description="관련 개념 ID")
    outcome: str = Field(default="", description="결과/의미")
    order_index: int = Field(default=0, description="시간순 정렬 인덱스")

    def get_searchable_text(self) -> str:
        parts = [
            self.title,
            f"시기: {self.time_period}",
            f"장소: {self.location}" if self.location else "",
            self.content,
            f"결과: {self.outcome}" if self.outcome else "",
        ]
        return "\n".join(filter(None, parts))


class RunWorldSetting(RunEntity):
    """
    세계관 설정 (섹션별)

    예: 시대 배경, 오펀, 커넥톰 기술, 보이스, 경제 체계 등
    카테고리별로 분류
    """
    entity_type: EntityType = EntityType.WORLD_SETTING
    category: str = Field(default="", description="카테고리 (기술/조직/장소/경제/사회)")
    sub_items: list[dict] = Field(default_factory=list, description="하위 항목")

    def get_searchable_text(self) -> str:
        parts = [
            self.title,
            f"카테고리: {self.category}",
            self.content,
        ]
        for item in self.sub_items:
            name = item.get("name", "")
            desc = item.get("description", "")
            if name:
                parts.append(f"- {name}: {desc}")
        return "\n".join(filter(None, parts))
