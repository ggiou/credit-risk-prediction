"""Spring Boot 전용 내부 예측 API를 제공한다."""

import hashlib
import json
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.explanation_service import ExplanationService
from app.services.model_service import ModelNotLoadedError, ModelService


router = APIRouter(prefix="/internal/v1", tags=["내부 예측"])


@lru_cache
def get_model_service() -> ModelService:
    """요청에서 사용할 모델 서비스를 생성한다."""

    # FastAPI 의존성 재정의를 통해 테스트에서는 가짜 모델을 주입할 수 있다.
    return ModelService(get_settings())


@lru_cache
def get_explanation_service() -> ExplanationService:
    """요청에서 사용할 LLM 설명 서비스를 생성한다."""

    return ExplanationService(get_settings())


@router.get("/health")
def health(
    settings: Settings = Depends(get_settings),
    model_service: ModelService = Depends(get_model_service),
) -> dict:
    """모델과 LLM 설정 상태를 확인한다."""

    # 규칙 기반 개발 모드는 실제 모델 로드 상태와 구분해 운영 오판을 방지한다.
    return {
        "status": "UP",
        "modelLoaded": model_service.loaded,
        "modelMode": "LIGHTGBM" if model_service.loaded else "RULE_BASED_DEVELOPMENT" if settings.allow_rule_based_fallback else "UNAVAILABLE",
        "modelVersion": settings.model_version,
        "featureSchemaVersion": settings.feature_schema_version,
        "llmConfigured": bool(settings.openai_api_key and settings.openai_model),
    }


@router.post("/predictions", response_model=PredictionResponse, response_model_by_alias=True)
async def predict(
    request: PredictionRequest,
    settings: Settings = Depends(get_settings),
    model_service: ModelService = Depends(get_model_service),
    explanation_service: ExplanationService = Depends(get_explanation_service),
) -> PredictionResponse:
    """파생 피처 계산, LightGBM 추론, LLM 설명을 순서대로 수행한다."""

    if request.feature_schema_version != settings.feature_schema_version:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "FEATURE_SCHEMA_MISMATCH", "message": "지원하지 않는 피처 스키마 버전입니다."},
        )
    if request.expected_model_version != settings.model_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "MODEL_VERSION_MISMATCH", "message": "요청 모델 버전과 서버 모델 버전이 다릅니다."},
        )

    try:
        prediction, risk_factors = model_service.predict(
            request.current_features, request.previous_features
        )
    except ModelNotLoadedError as exception:
        # 모델 미탑재는 입력 오류가 아니라 배포 준비 실패이므로 503으로 구분한다.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_NOT_LOADED", "message": str(exception)},
        ) from exception

    explanation, used_keys, llm = await explanation_service.explain(
        prediction,
        risk_factors,
        request.prompt_version,
        request.generate_explanation,
    )
    input_hash = calculate_input_hash(request, settings.model_version)
    return PredictionResponse(
        requestId=request.request_id,
        customerId=request.customer_id,
        baseYm=request.base_ym,
        featureSnapshotId=request.feature_snapshot_id,
        featureSchemaVersion=request.feature_schema_version,
        modelVersion=settings.model_version,
        prediction=prediction,
        riskFactors=risk_factors,
        explanation=explanation,
        usedFeatureKeys=used_keys,
        llm=llm,
        inputHash=input_hash,
        predictedAt=datetime.now(timezone.utc),
    )


def calculate_input_hash(request: PredictionRequest, model_version: str) -> str:
    """동일 입력 결과 재사용을 위한 결정적 SHA-256 해시를 계산한다."""

    # 키 순서와 공백 차이에 영향을 받지 않도록 정렬된 UTF-8 JSON을 사용한다.
    payload = {
        "modelVersion": model_version,
        "featureSchemaVersion": request.feature_schema_version,
        "promptVersion": request.prompt_version,
        "generateExplanation": request.generate_explanation,
        "currentFeatures": request.current_features,
        "previousFeatures": request.previous_features,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
