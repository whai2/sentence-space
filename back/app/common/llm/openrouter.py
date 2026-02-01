"""OpenRouter API Client for unified LLM access"""

import os
from typing import Optional, List, Dict, Any, Iterator
import openai
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class OpenRouterClient:
    """OpenRouter 클라이언트 - 통합 LLM API 관리

    OpenRouter를 통해 여러 AI 모델(OpenAI, Anthropic, Google, Meta 등)에
    단일 API로 접근할 수 있습니다.

    환경변수:
        OPENROUTER_API_KEY: OpenRouter API 키 (필수)
        OPENROUTER_BASE_URL: OpenRouter API 엔드포인트 (기본값: https://openrouter.ai/api/v1)

    사용 예시:
        ```python
        client = OpenRouterClient()

        # 동기 호출
        response = client.chat_completion(
            model="anthropic/claude-3-sonnet",
            messages=[{"role": "user", "content": "Hello!"}]
        )

        # 스트리밍 호출
        for chunk in client.chat_completion_stream(
            model="anthropic/claude-3-sonnet",
            messages=[{"role": "user", "content": "Hello!"}]
        ):
            print(chunk)
        ```
    """

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    # 자주 사용되는 모델들
    MODELS = {
        # Anthropic Claude
        "claude-3-opus": "anthropic/claude-3-opus",
        "claude-3-sonnet": "anthropic/claude-3-sonnet",
        "claude-3-haiku": "anthropic/claude-3-haiku",
        "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",

        # OpenAI GPT
        "gpt-4-turbo": "openai/gpt-4-turbo",
        "gpt-4": "openai/gpt-4",
        "gpt-3.5-turbo": "openai/gpt-3.5-turbo",

        # Google Gemini
        "gemini-pro": "google/gemini-pro",
        "gemini-pro-vision": "google/gemini-pro-vision",

        # Meta Llama
        "llama-3-70b": "meta-llama/llama-3-70b-instruct",
        "llama-3-8b": "meta-llama/llama-3-8b-instruct",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        app_name: Optional[str] = None,
        site_url: Optional[str] = None,
    ):
        """OpenRouter 클라이언트 초기화

        Args:
            api_key: OpenRouter API 키 (미제공시 환경변수에서 로드)
            base_url: OpenRouter API 엔드포인트 (미제공시 기본값 사용)
            app_name: 애플리케이션 이름 (OpenRouter 대시보드에 표시)
            site_url: 사이트 URL (OpenRouter 대시보드에 표시)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key is required. "
                "Set OPENROUTER_API_KEY environment variable or pass api_key parameter."
            )

        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", self.DEFAULT_BASE_URL)
        self.app_name = app_name or os.getenv("OPENROUTER_APP_NAME")
        self.site_url = site_url or os.getenv("OPENROUTER_SITE_URL")

        # OpenAI 클라이언트 초기화 (OpenRouter는 OpenAI API와 호환)
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        # 기본 헤더 설정
        self.default_headers = {}
        if self.app_name:
            self.default_headers["X-Title"] = self.app_name
        if self.site_url:
            self.default_headers["HTTP-Referer"] = self.site_url

    def get_model_name(self, model_alias: str) -> str:
        """모델 별칭을 실제 모델 이름으로 변환

        Args:
            model_alias: 모델 별칭 (예: "claude-3-sonnet") 또는 전체 이름

        Returns:
            실제 모델 이름 (예: "anthropic/claude-3-sonnet")
        """
        return self.MODELS.get(model_alias, model_alias)

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        extra_headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ChatCompletion:
        """채팅 완성 API 호출 (동기)

        Args:
            model: 모델 이름 또는 별칭
            messages: 대화 메시지 리스트
            temperature: 샘플링 온도 (0.0 ~ 2.0)
            max_tokens: 최대 생성 토큰 수
            top_p: nucleus sampling 파라미터
            frequency_penalty: 빈도 페널티
            presence_penalty: 존재 페널티
            extra_headers: 추가 HTTP 헤더
            **kwargs: 추가 파라미터

        Returns:
            ChatCompletion: 완성된 응답
        """
        headers = {**self.default_headers, **(extra_headers or {})}

        return self.client.chat.completions.create(
            model=self.get_model_name(model),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            extra_headers=headers,
            **kwargs
        )

    def chat_completion_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        extra_headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Iterator[ChatCompletionChunk]:
        """채팅 완성 API 호출 (스트리밍)

        Args:
            model: 모델 이름 또는 별칭
            messages: 대화 메시지 리스트
            temperature: 샘플링 온도 (0.0 ~ 2.0)
            max_tokens: 최대 생성 토큰 수
            top_p: nucleus sampling 파라미터
            frequency_penalty: 빈도 페널티
            presence_penalty: 존재 페널티
            extra_headers: 추가 HTTP 헤더
            **kwargs: 추가 파라미터

        Yields:
            ChatCompletionChunk: 스트리밍 청크
        """
        headers = {**self.default_headers, **(extra_headers or {})}

        stream = self.client.chat.completions.create(
            model=self.get_model_name(model),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stream=True,
            extra_headers=headers,
            **kwargs
        )

        for chunk in stream:
            yield chunk

    def get_available_models(self) -> List[str]:
        """사용 가능한 모델 별칭 목록 반환

        Returns:
            모델 별칭 리스트
        """
        return list(self.MODELS.keys())

    def simple_chat(
        self,
        prompt: str,
        model: str = "claude-3-sonnet",
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
    ) -> str:
        """간단한 채팅 인터페이스

        Args:
            prompt: 사용자 프롬프트
            model: 모델 이름 또는 별칭
            temperature: 샘플링 온도
            max_tokens: 최대 토큰 수
            system_message: 시스템 메시지 (선택사항)

        Returns:
            응답 텍스트
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        response = self.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content
