from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model_path: Path
    expected_model_sha256: str
    feature_schema_version: str
    openai_api_key: str | None
    openai_model: str
    prompt_version: str
    llm_timeout_seconds: float
    max_risk_factors: int

    @classmethod
    def from_env(cls) -> "Settings":
        default_model_path = Path(__file__).resolve().parents[1] / "models" / "model_lgbm.json"
        return cls(
            model_path=Path(os.getenv("AI_MODEL_PATH", str(default_model_path))),
            expected_model_sha256=os.getenv(
                "AI_MODEL_SHA256",
                "71494be683a0c6865d78f001c69a58f25de9adcda543295954c3f0503fe0f5ac",
            ).strip(),
            feature_schema_version=os.getenv("AI_FEATURE_SCHEMA_VERSION", "v1"),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
            prompt_version=os.getenv("AI_PROMPT_VERSION", "v3.6"),
            llm_timeout_seconds=float(os.getenv("AI_LLM_TIMEOUT_SECONDS", "60")),
            max_risk_factors=int(os.getenv("AI_MAX_RISK_FACTORS", "5")),
        )


settings = Settings.from_env()
