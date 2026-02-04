from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Sentence Space API"
    app_version: str = "0.1.0"
    debug: bool = False

    host: str = "0.0.0.0"
    port: int = 8000

    openrouter_api_key: str = ""
    llm_model: str = "anthropic/claude-3.5-sonnet"

    # 데이터 저장 디렉토리 (기억 영속성)
    data_dir: str = "data"

    # Langfuse 설정 (비용 추적)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
