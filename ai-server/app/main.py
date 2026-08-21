from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import FastAPI, HTTPException, status

from .config import settings
from .hashing import prediction_input_hash
from .llm import RiskExplanationClient
from .model_bundle import ModelBundle, ModelContractError
from .schemas import LlmMeta, PredictRequest, PredictResponse, PredictionValues

app = FastAPI(
    title="Credit Risk AI Server",
    docs_url="/internal/docs",
    openapi_url="/internal/openapi.json",
)


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
        "modelVersion": version,
        "featureSchemaVersion": settings.feature_schema_version,
        "llmConfigured": bool(settings.openai_api_key),
    }


@app.post("/internal/v1/predictions", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    try:
        model = get_model()
    except (FileNotFoundError, ModelContractError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI model unavailable: {exc}",
        ) from exc

    if request.featureSchemaVersion != settings.feature_schema_version:
        raise HTTPException(
            status_code=422,
            detail=(
                "featureSchemaVersion mismatch: "
                f"expected={settings.feature_schema_version}, "
                f"actual={request.featureSchemaVersion}"
            ),
        )
    if request.expectedModelVersion != model.model_version:
        raise HTTPException(
            status_code=422,
            detail=(
                "expectedModelVersion mismatch: "
                f"expected={request.expectedModelVersion}, actual={model.model_version}"
            ),
        )
    if request.promptVersion != settings.prompt_version:
        raise HTTPException(
            status_code=422,
            detail=(
                "promptVersion mismatch: "
                f"expected={settings.prompt_version}, actual={request.promptVersion}"
            ),
        )

    try:
        prediction, contributions, enriched = model.predict(
            request.currentFeatures,
            request.previousFeatures,
        )
        risk_factors = model.risk_factors(
            request.currentFeatures,
            request.previousFeatures,
            contributions,
            enriched,
            limit=settings.max_risk_factors,
        )
    except (ModelContractError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    prediction_body = {
        "hazard1m": prediction.hazard_1m,
        "hazard2m": prediction.hazard_2m,
        "hazard3m": prediction.hazard_3m,
        "cumulativeRisk3m": prediction.cumulative_risk_3m,
        "riskGrade": prediction.risk_grade,
        "percentile": prediction.percentile,
    }

    llm_status = "NOT_REQUESTED"
    explanation = None
    used_feature_keys: list[str] = []
    llm_error = None

    if request.generateExplanation:
        llm = get_llm()
        if llm is None:
            llm_status = "FAILED"
            llm_error = "OPENAI_API_KEY is not configured"
        else:
            llm_result = llm.generate(
                prediction=prediction_body,
                risk_factors=risk_factors,
            )
            llm_status = llm_result.status
            explanation = llm_result.explanation
            used_feature_keys = llm_result.used_feature_keys
            llm_error = llm_result.error_message

    input_hash = prediction_input_hash(
        model_version=model.model_version,
        feature_schema_version=request.featureSchemaVersion,
        prompt_version=request.promptVersion,
        generate_explanation=request.generateExplanation,
        current_features=request.currentFeatures,
        previous_features=request.previousFeatures,
    )

    return PredictResponse(
        requestId=request.requestId,
        customerId=request.customerId,
        baseYm=request.baseYm,
        featureSnapshotId=request.featureSnapshotId,
        featureSchemaVersion=request.featureSchemaVersion,
        modelVersion=model.model_version,
        prediction=PredictionValues(**prediction_body),
        riskFactors=risk_factors,
        explanation=explanation,
        usedFeatureKeys=used_feature_keys,
        llm=LlmMeta(
            status=llm_status,
            promptVersion=request.promptVersion,
            errorMessage=llm_error,
        ),
        inputHash=input_hash,
        predictedAt=datetime.now(timezone.utc),
    )
