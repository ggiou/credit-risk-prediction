"""Spring Boot와 교환하는 예측 요청·응답 스키마를 정의한다."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictionRequest(BaseModel):
    """현재·이전 월 피처와 예측 실행 옵션이다."""

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())

    request_id: str = Field(alias="requestId", min_length=1, max_length=100)
    customer_id: str = Field(alias="customerId", min_length=1, max_length=32)
    base_ym: str = Field(alias="baseYm", pattern=r"^(19|20)\d{2}(0[1-9]|1[0-2])$")
    feature_snapshot_id: int = Field(alias="featureSnapshotId", gt=0)
    previous_feature_snapshot_id: int | None = Field(default=None, alias="previousFeatureSnapshotId")
    feature_schema_version: str = Field(alias="featureSchemaVersion", min_length=1)
    expected_model_version: str = Field(alias="expectedModelVersion", min_length=1)
    prompt_version: str = Field(alias="promptVersion", min_length=1)
    generate_explanation: bool = Field(default=True, alias="generateExplanation")
    current_features: dict[str, Any] = Field(alias="currentFeatures")
    previous_features: dict[str, Any] | None = Field(default=None, alias="previousFeatures")

    @model_validator(mode="after")
    def validate_previous_snapshot_pair(self) -> "PredictionRequest":
        """이전 스냅샷 ID와 피처가 함께 전달되었는지 확인한다."""

        # ID와 데이터 중 하나만 있으면 다른 고객·월과 잘못 비교될 수 있으므로 요청을 거부한다.
        has_id = self.previous_feature_snapshot_id is not None
        has_features = self.previous_features is not None
        if has_id != has_features:
            raise ValueError("previousFeatureSnapshotId와 previousFeatures는 함께 전달해야 합니다.")
        return self


class RiskFactor(BaseModel):
    """위험도에 영향을 준 피처의 값과 변화량이다."""

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())

    feature_key: str = Field(alias="featureKey")
    display_name: str = Field(alias="displayName")
    direction: Literal["INCREASE", "DECREASE", "MAINTAIN"]
    previous_value: float | None = Field(alias="previousValue")
    current_value: float | None = Field(alias="currentValue")
    change_value: float | None = Field(alias="changeValue")
    change_rate: float | None = Field(alias="changeRate")
    unit: Literal["RATIO", "AMOUNT", "COUNT", "FLAG"]
    contribution: float


class PredictionValues(BaseModel):
    """LightGBM이 계산한 기간별 위험률과 등급이다."""

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())

    hazard_1m: float = Field(alias="hazard1m", ge=0, le=1)
    hazard_2m: float = Field(alias="hazard2m", ge=0, le=1)
    hazard_3m: float = Field(alias="hazard3m", ge=0, le=1)
    cumulative_risk_3m: float = Field(alias="cumulativeRisk3m", ge=0, le=1)
    risk_grade: Literal["NORMAL", "INTEREST", "CAUTION", "WARNING"] = Field(alias="riskGrade")
    percentile: float = Field(ge=0, le=100)


class LlmResult(BaseModel):
    """LLM 설명 생성 상태와 실패 사유다."""

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())

    status: Literal["NOT_REQUESTED", "COMPLETED", "FAILED"]
    prompt_version: str = Field(alias="promptVersion")
    error_message: str | None = Field(alias="errorMessage")


class PredictionResponse(BaseModel):
    """Spring Boot에 반환할 최종 예측 결과다."""

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())

    request_id: str = Field(alias="requestId")
    customer_id: str = Field(alias="customerId")
    base_ym: str = Field(alias="baseYm")
    feature_snapshot_id: int = Field(alias="featureSnapshotId")
    feature_schema_version: str = Field(alias="featureSchemaVersion")
    model_version: str = Field(alias="modelVersion")
    prediction: PredictionValues
    risk_factors: list[RiskFactor] = Field(alias="riskFactors")
    explanation: str | None
    used_feature_keys: list[str] = Field(alias="usedFeatureKeys")
    llm: LlmResult
    input_hash: str = Field(alias="inputHash")
    predicted_at: datetime = Field(alias="predictedAt")
