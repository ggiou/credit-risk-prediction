"""환경변수 기반 AI 서버 설정을 정의한다."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """모델, LLM, 타임아웃 관련 환경 설정이다."""

    model_version: str = "miribom-lgbm-v0.3"
    feature_schema_version: str = "v1"
    model_path: Path = Path("models/miribom-lgbm-v0.3.txt")
    feature_order_path: Path = Path("models/feature-order.json")
    allow_rule_based_fallback: bool = False
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_",
        extra="ignore",
        protected_namespaces=("settings_",),
    )


@lru_cache
def get_settings() -> Settings:
    """애플리케이션 전체에서 재사용할 설정 객체를 한 번 생성한다."""

    # 요청마다 환경변수를 다시 읽지 않도록 프로세스 단위로 캐시한다.
    return Settings()
