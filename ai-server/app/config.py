from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


@dataclass(frozen=True)
class Settings:
    model_path: Path
    expected_model_sha256: str
    feature_schema_version: str
    openai_api_key: str | None
    openai_model: str
    prompt_version: str
    openai_prompt_cache_enabled: bool
    openai_prompt_cache_mode: str
    openai_prompt_cache_ttl: str
    openai_prompt_cache_key_prefix: str
    llm_timeout_seconds: float
    max_risk_factors: int

    @classmethod
    def from_env(cls) -> "Settings":
        default_model_path = Path(__file__).resolve().parents[1] / "models" / "model_lgbm.json"
        prompt_cache_mode = os.getenv("OPENAI_PROMPT_CACHE_MODE", "explicit").strip()
        prompt_cache_ttl = os.getenv("OPENAI_PROMPT_CACHE_TTL", "30m").strip()
        prompt_cache_key_prefix = os.getenv(
            "OPENAI_PROMPT_CACHE_KEY_PREFIX",
            "miribom-risk-explanation",
        ).strip()
        if prompt_cache_mode != "explicit":
            raise ValueError("OPENAI_PROMPT_CACHE_MODE must be 'explicit'")
        if prompt_cache_ttl != "30m":
            raise ValueError("OPENAI_PROMPT_CACHE_TTL must be '30m'")
        if not prompt_cache_key_prefix:
            raise ValueError("OPENAI_PROMPT_CACHE_KEY_PREFIX must not be empty")
        return cls(
            model_path=Path(os.getenv("AI_MODEL_PATH", str(default_model_path))),
            expected_model_sha256=os.getenv(
                "AI_MODEL_SHA256",
                "71494be683a0c6865d78f001c69a58f25de9adcda543295954c3f0503fe0f5ac",
            ).strip(),
            feature_schema_version=os.getenv("AI_FEATURE_SCHEMA_VERSION", "v1"),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
            prompt_version=os.getenv("AI_PROMPT_VERSION", "v3.7"),
            openai_prompt_cache_enabled=_read_bool("OPENAI_PROMPT_CACHE_ENABLED", True),
            openai_prompt_cache_mode=prompt_cache_mode,
            openai_prompt_cache_ttl=prompt_cache_ttl,
            openai_prompt_cache_key_prefix=prompt_cache_key_prefix,
            llm_timeout_seconds=float(os.getenv("AI_LLM_TIMEOUT_SECONDS", "60")),
            max_risk_factors=int(os.getenv("AI_MAX_RISK_FACTORS", "5")),
        )


settings = Settings.from_env()
