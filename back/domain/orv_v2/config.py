"""
ORV v2 설정

Agent별 모델 할당 - 직접 API 호출 (OpenRouter보다 빠름)
"""
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


class AgentModels(BaseModel):
    """Agent별 모델 설정"""

    # Orchestrator: 높은 추론력 필요 (설계, 개연성 검증)
    orchestrator_model: str = "claude-sonnet-4-5-20250514"
    orchestrator_temperature: float = 0.3  # 낮은 temperature (일관성)

    # Narrator: 서술 품질 (웹소설 스타일)
    narrator_model: str = "gpt-4o"
    narrator_temperature: float = 0.7  # 높은 temperature (창의성)

    # NPC Agent: 가벼운 모델 (비용 절감)
    npc_model: str = "claude-haiku-4-5-20250514"
    npc_temperature: float = 0.5


class LLMFactory:
    """
    LLM 팩토리

    직접 API 호출 (OpenRouter 프록시 레이턴시 제거)
    - Anthropic 모델: ChatAnthropic 직접 호출
    - OpenAI 모델: ChatOpenAI 직접 호출
    """

    def __init__(
        self,
        anthropic_api_key: str = "",
        openai_api_key: str = "",
        openrouter_api_key: str = "",  # fallback
        models: AgentModels | None = None,
    ):
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.openrouter_api_key = openrouter_api_key
        self.models = models or AgentModels()

        # 직접 API 사용 가능 여부 확인
        self.use_direct_anthropic = bool(anthropic_api_key)
        self.use_direct_openai = bool(openai_api_key)

    def get_orchestrator_llm(self) -> ChatAnthropic | ChatOpenAI:
        """
        Orchestrator LLM (Claude Sonnet 4.5)

        높은 추론력 + 낮은 temperature
        """
        if self.use_direct_anthropic:
            return ChatAnthropic(
                model=self.models.orchestrator_model,
                temperature=self.models.orchestrator_temperature,
                api_key=self.anthropic_api_key,
            )
        # Fallback to OpenRouter
        return ChatOpenAI(
            model="anthropic/claude-sonnet-4.5",
            temperature=self.models.orchestrator_temperature,
            openai_api_key=self.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
        )

    def get_narrator_llm(self) -> ChatOpenAI:
        """
        Narrator LLM (GPT-4o)

        서술 품질 + 창의성
        """
        if self.use_direct_openai:
            return ChatOpenAI(
                model=self.models.narrator_model,
                temperature=self.models.narrator_temperature,
                api_key=self.openai_api_key,
            )
        # Fallback to OpenRouter
        return ChatOpenAI(
            model="openai/gpt-4o",
            temperature=self.models.narrator_temperature,
            openai_api_key=self.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
        )

    def get_npc_llm(self) -> ChatAnthropic | ChatOpenAI:
        """
        NPC LLM (Claude Haiku 4.5)

        가벼운 모델로 비용 절감
        """
        if self.use_direct_anthropic:
            return ChatAnthropic(
                model=self.models.npc_model,
                temperature=self.models.npc_temperature,
                api_key=self.anthropic_api_key,
            )
        # Fallback to OpenRouter
        return ChatOpenAI(
            model="anthropic/claude-haiku-4.5",
            temperature=self.models.npc_temperature,
            openai_api_key=self.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
        )
