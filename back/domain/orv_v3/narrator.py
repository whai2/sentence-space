"""
ORV v3 Narrator Agent

Gemini 2.5 Flash 기반 웹소설 서술 에이전트 (Step ①)

- Standalone: 다른 에이전트에 의존하지 않음
- Raw text output: JSON 구조화 없음, 순수 산문 출력
- Manual inputs: 모든 입력을 수동으로 제공
"""
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from domain.orv_v3.prompts import build_system_prompt


@dataclass
class SceneInput:
    """
    한 장면 서술에 필요한 입력

    모든 필드가 순수 텍스트 (str).
    다른 에이전트나 DB에 의존하지 않음.
    """

    # 세계관 설정 (고정 텍스트)
    world_setting: str

    # 캐릭터 시트 (이름, 성격, 말투, 현재 상태)
    character_sheet: str

    # 현재 서사 단계 ("도입부", "갈등 고조", "클라이맥스" 등)
    narrative_stage: str

    # 직전 장면 요약 또는 원문
    previous_scene: str

    # 플레이어의 선택/행동
    player_action: str

    # (선택) 추가 지시사항
    extra_direction: str = ""


def build_user_message(scene_input: SceneInput) -> str:
    """
    SceneInput으로부터 유저 메시지(프롬프트) 생성

    각 섹션이 명확히 구분되어 있어 LLM이 정보를 쉽게 파악 가능
    """
    sections = [
        f"## 세계관 설정\n\n{scene_input.world_setting}",
        f"## 등장인물\n\n{scene_input.character_sheet}",
        f"## 현재 서사 단계\n\n{scene_input.narrative_stage}",
        f"## 직전 장면\n\n{scene_input.previous_scene}",
        f"## 플레이어 행동\n\n{scene_input.player_action}",
    ]

    if scene_input.extra_direction:
        sections.append(f"## 추가 지시\n\n{scene_input.extra_direction}")

    sections.append(
        "---\n\n"
        "위 정보를 바탕으로 다음 장면을 서술하세요. "
        "서술만 출력하세요. 다른 설명이나 메타 정보는 포함하지 마세요."
    )

    return "\n\n".join(sections)


class NarratorAgent:
    """
    웹소설 장면 서술 에이전트

    Gemini 2.5 Flash via OpenRouter
    Raw text output (no structured JSON)
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        system_prompt: str | None = None,
    ):
        """
        Args:
            llm: LLM 인스턴스 (create_narrator_llm()으로 생성)
            system_prompt: 커스텀 시스템 프롬프트 (None이면 기본값)
        """
        self.llm = llm
        self.system_prompt = system_prompt or build_system_prompt()

    async def narrate(self, scene_input: SceneInput) -> str:
        """
        장면 서술 생성 (비동기)

        Args:
            scene_input: 장면 입력 데이터

        Returns:
            웹소설 스타일 장면 텍스트 (500~1500자)
        """
        user_message = build_user_message(scene_input)

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]

        response = await self.llm.ainvoke(messages)
        return response.content

    def narrate_sync(self, scene_input: SceneInput) -> str:
        """
        장면 서술 생성 (동기)

        테스트/스크립트 편의용.
        """
        user_message = build_user_message(scene_input)

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]

        response = self.llm.invoke(messages)
        return response.content
