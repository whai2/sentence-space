"""
ORV v3 설정

Step ① - Narrator 전용 설정
OpenRouter를 통한 Gemini 2.5 Flash 호출
"""
import os
from dataclasses import dataclass

from langchain_openai import ChatOpenAI


@dataclass
class NarratorConfig:
    """Narrator LLM 설정"""

    model: str = "google/gemini-2.5-flash"
    temperature: float = 0.75
    max_tokens: int = 4096
    openrouter_api_key: str = ""

    @classmethod
    def from_env(cls) -> "NarratorConfig":
        """환경변수에서 설정 로드"""
        return cls(
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )


def create_narrator_llm(config: NarratorConfig | None = None) -> ChatOpenAI:
    """
    Narrator LLM 생성

    Gemini 2.5 Flash via OpenRouter
    """
    if config is None:
        config = NarratorConfig.from_env()

    return ChatOpenAI(
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        openai_api_key=config.openrouter_api_key,
        openai_api_base="https://openrouter.ai/api/v1",
    )
