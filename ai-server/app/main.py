from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import settings
from .explanation_context import build_llm_input
from .llm import RiskExplanationClient
from .model_bundle import ModelBundle, ModelContractError
from .schemas import LlmMeta, PredictRequest, PredictResponse, PredictionValues

LOGGER = logging.getLogger("miribom.ai.api")

app = FastAPI(
    title="Credit Risk AI Server",
    docs_url="/internal/docs",
    openapi_url="/internal/openapi.json",
)


@app.exception_handler(RequestValidationError)
async def log_request_validation_error(request: Request, exception: RequestValidationError) -> JSONResponse:
    safe_errors = [
        {
            "location": list(error.get("loc", ())),
            "type": error.get("type"),
            "message": error.get("msg"),
        }
        for error in exception.errors()
    ]
    LOGGER.warning(
        "AI request validation failed path=%s errors=%s",
        request.url.path,
        safe_errors,
    )
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exception.errors())})


@lru_cache(maxsize=1)
def get_model() -> ModelBundle:
    if not settings.model_path.exists():
        raise FileNotFoundError(
            f"model file not found: {settings.model_path}. "
            "Place the supplied model_lgbm.json locally; do not commit it."
        )
    return ModelBundle.from_path(
        settings.model_path,
        expected_sha256=settings.expected_model_sha256,
    )


@lru_cache(maxsize=1)
def get_llm() -> RiskExplanationClient | None:
    if not settings.openai_api_key:
        return None
    return RiskExplanationClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        prompt_version=settings.prompt_version,
        prompt_cache_enabled=settings.openai_prompt_cache_enabled,
        prompt_cache_mode=settings.openai_prompt_cache_mode,
        prompt_cache_ttl=settings.openai_prompt_cache_ttl,
        prompt_cache_key_prefix=settings.openai_prompt_cache_key_prefix,
        timeout_seconds=settings.llm_timeout_seconds,
    )


@app.get("/internal/v1/health")
def health() -> dict:
    try:
        model = get_model()
        loaded = True
        version = model.model_version
    except Exception:
        loaded = False
        version = None
    return {
        "status": "UP" if loaded else "DEGRADED",
        "modelLoaded": loaded,
        "predictionSource": "LIGHTGBM_JSON" if loaded else None,
        "modelVersion": version,
        "featureSchemaVersion": settings.feature_schema_version,
        "llmConfigured": bool(settings.openai_api_key),
    }


@app.post("/internal/v1/predictions", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    try:
        model = get_model()
    except (FileNotFoundError, ModelContractError, ValueError, KeyError) as exc:
        LOGGER.exception(
            "AI model unavailable requestId=%s customerId=%s baseYm=%s",
            request.requestId,
            request.customerId,
            request.baseYm,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI model unavailable: {exc}",
        ) from exc

    if request.featureSchemaVersion != settings.feature_schema_version:
        LOGGER.warning(
            "Feature schema mismatch requestId=%s customerId=%s baseYm=%s expected=%s actual=%s",
            request.requestId, request.customerId, request.baseYm,
            settings.feature_schema_version, request.featureSchemaVersion,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "featureSchemaVersion mismatch: "
                f"expected={settings.feature_schema_version}, "
                f"actual={request.featureSchemaVersion}"
            ),
        )
    if request.expectedModelVersion != model.model_version:
        LOGGER.warning(
            "Model version mismatch requestId=%s customerId=%s baseYm=%s expected=%s actual=%s",
            request.requestId, request.customerId, request.baseYm,
            request.expectedModelVersion, model.model_version,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "expectedModelVersion mismatch: "
                f"expected={request.expectedModelVersion}, actual={model.model_version}"
            ),
        )
    if request.promptVersion != settings.prompt_version:
        LOGGER.warning(
            "Prompt version mismatch requestId=%s customerId=%s baseYm=%s expected=%s actual=%s",
            request.requestId, request.customerId, request.baseYm,
            settings.prompt_version, request.promptVersion,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "promptVersion mismatch: "
                f"expected={settings.prompt_version}, actual={request.promptVersion}"
            ),
        )

    try:
        prediction, enriched = model.predict(
            request.currentFeatures,
            request.previousFeatures,
        )
        risk_factors = model.risk_factors(
            request.currentFeatures,
            request.previousFeatures,
            enriched,
            limit=settings.max_risk_factors,
        )
    except (ModelContractError, TypeError, ValueError) as exc:
        LOGGER.exception(
            "LightGBM JSON inference failed requestId=%s customerId=%s baseYm=%s errorType=%s",
            request.requestId,
            request.customerId,
            request.baseYm,
            type(exc).__name__,
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    prediction_body = {
        "hazard1m": prediction.hazard_1m,
        "hazard2m": prediction.hazard_2m,
        "hazard3m": prediction.hazard_3m,
        "cumulativeRisk3m": prediction.cumulative_risk_3m,
        "riskGrade": prediction.risk_grade,
        "topRiskPercent": prediction.top_risk_percent,
        "percentile": prediction.percentile,
    }
    llm_input = build_llm_input(
        model_version=model.model_version,
        prompt_version=request.promptVersion,
        prediction=prediction,
        reasons=risk_factors,
        current=request.currentFeatures,
        previous=request.previousFeatures,
    )

    llm_status = "NOT_REQUESTED"
    explanation = None
    recommendation = None
    llm_output = None
    used_feature_keys: list[str] = []
    llm_error = None

    if request.generateExplanation:
        llm = get_llm()
        if llm is None:
            llm_status = "FAILED"
            llm_error = "OPENAI_API_KEY is not configured"
            LOGGER.error(
                "LLM configuration missing requestId=%s customerId=%s baseYm=%s",
                request.requestId,
                request.customerId,
                request.baseYm,
            )
        else:
            llm_result = llm.generate(
                input_payload=llm_input,
                request_id=request.requestId,
                customer_id=request.customerId,
                base_ym=request.baseYm,
                previous_features_available=request.previousFeatures is not None,
            )
            llm_status = llm_result.status
            explanation = llm_result.explanation
            llm_output = llm_result.structured_output
            if llm_result.review_points:
                recommendation = "\n".join(
                    f"{point['priority']}. {point['text']}"
                    for point in llm_result.review_points
                )
            used_feature_keys = llm_result.used_feature_keys
            llm_error = llm_result.error_message
            if llm_status == "FAILED":
                LOGGER.error(
                    "LLM explanation failed requestId=%s customerId=%s baseYm=%s error=%s",
                    request.requestId,
                    request.customerId,
                    request.baseYm,
                    (llm_error or "unknown")[:500],
                )

    return PredictResponse(
        requestId=request.requestId,
        customerId=request.customerId,
        baseYm=request.baseYm,
        featureSnapshotId=request.featureSnapshotId,
        featureSchemaVersion=request.featureSchemaVersion,
        modelVersion=model.model_version,
        predictionSource="LIGHTGBM_JSON",
        prediction=PredictionValues(**prediction_body),
        riskFactors=risk_factors,
        observedChanges=llm_input["observedChanges"],
        explanation=explanation,
        recommendation=recommendation,
        llmOutput=llm_output,
        usedFeatureKeys=used_feature_keys,
        llm=LlmMeta(
            status=llm_status,
            promptVersion=request.promptVersion,
            errorMessage=llm_error,
        ),
        predictedAt=datetime.now(timezone.utc),
    )
