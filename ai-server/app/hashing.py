from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def prediction_input_hash(
    *,
    model_version: str,
    feature_schema_version: str,
    llm_model: str,
    prompt_version: str,
    generate_explanation: bool,
    current_features: dict[str, Any],
    previous_features: dict[str, Any] | None,
) -> str:
    source = "".join(
        [
            model_version,
            feature_schema_version,
            llm_model,
            prompt_version,
            "true" if generate_explanation else "false",
            canonical_json(current_features),
            canonical_json(previous_features),
        ]
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
