from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requestId: str
    customerId: str
    baseYm: str = Field(pattern=r"^(19|20)\d{2}(0[1-9]|1[0-2])$")
    featureSnapshotId: int
    previousFeatureSnapshotId: int | None = None
    featureSchemaVersion: str
    expectedModelVersion: str
    promptVersion: str = "v3.7"
    generateExplanation: bool = True
    currentFeatures: dict[str, Any]
    previousFeatures: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_previous_snapshot_pair(self) -> "PredictRequest":
        if (self.previousFeatureSnapshotId is None) != (self.previousFeatures is None):
            raise ValueError("previousFeatureSnapshotId and previousFeatures must be provided together")
        return self


class PredictionValues(BaseModel):
    hazard1m: float = Field(ge=0, le=1)
    hazard2m: float = Field(ge=0, le=1)
    hazard3m: float = Field(ge=0, le=1)
    cumulativeRisk3m: float = Field(ge=0, le=1)
    riskGrade: Literal["NORMAL", "INTEREST", "CAUTION", "WARNING"]
    topRiskPercent: float = Field(ge=0, le=100)
    # percentile은 topRiskPercent와 같은 값인 기존 호환 필드다.
    percentile: float = Field(ge=0, le=100)


class RiskFactor(BaseModel):
    reasonId: str
    featureKey: str
    displayName: str
    direction: Literal["INCREASE", "DECREASE"]
    modelDirection: Literal["INCREASE_RISK", "DECREASE_RISK"]
    reasonMethod: Literal["LOCAL_SHAP", "PREVIOUS_VALUE_COUNTERFACTUAL"]
    rank: int = Field(ge=1)
    patternCode: Literal[
        "PAYMENT_REGULARITY", "CREDIT_AVAILABILITY", "SHORT_TERM_BORROWING",
        "BALANCE_EXPOSURE", "BILLING_PRESSURE", "CARD_ACTIVITY",
    ]
    patternName: str
    previousValue: Any | None = None
    currentValue: Any | None = None
    changeValue: float | None = None
    changeRate: float | None = None
    unit: str
    counterfactualGrade: Literal["정상", "관심", "주의", "경고"] | None = None
    currentTopRiskPercent: float | None = Field(default=None, ge=0, le=100)
    counterfactualTopRiskPercent: float | None = Field(default=None, ge=0, le=100)
    topRiskPercentDifference: float | None = Field(default=None, ge=0, le=100)
    counterfactualRiskDirection: Literal["CURRENT_MORE_RISKY", "CURRENT_LESS_RISKY"] | None = None
    counterfactualGradeChanged: bool | None = None
    evidenceFeatureKeys: list[str]


class ReviewPoint(BaseModel):
    priority: int = Field(ge=1, le=2)
    text: str
    reasonIds: list[str]
    signalIds: list[str]


class KeyIndicator(BaseModel):
    title: str
    fact: str
    detail: str = ""
    interpretation: str
    modelRelation: Literal["RISK_INCREASE", "RISK_DECREASE", "MIXED", "CONTEXT"]
    reasonIds: list[str]
    signalIds: list[str]
    featureKeys: list[str]


class LlmOutput(BaseModel):
    summary: str
    modelInterpretation: str
    keyIndicators: list[KeyIndicator] = Field(min_length=1, max_length=4)
    changeContext: str
    reviewPoints: list[ReviewPoint] = Field(min_length=0, max_length=2)
    managementPriority: Literal[
        "ROUTINE_MONITORING", "ENHANCED_MONITORING", "PRIORITY_REVIEW", "URGENT_REVIEW"
    ]
    usedFeatureKeys: list[str]
    usedReasonIds: list[str]
    usedSignalIds: list[str]
    generationMode: Literal["FULL_ANALYSIS"]


class LlmMeta(BaseModel):
    status: Literal["NOT_REQUESTED", "COMPLETED", "FAILED", "SKIPPED_NO_EVIDENCE"]
    promptVersion: str
    errorMessage: str | None = None


class PredictResponse(BaseModel):
    requestId: str
    customerId: str
    baseYm: str
    featureSnapshotId: int
    featureSchemaVersion: str
    modelVersion: str
    predictionSource: Literal["LIGHTGBM_JSON", "RULE_BASED_FALLBACK"]
    prediction: PredictionValues
    riskFactors: list[RiskFactor]
    observedChanges: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str | None = None
    recommendation: str | None = None
    llmOutput: LlmOutput | None = None
    usedFeatureKeys: list[str] = Field(default_factory=list)
    llm: LlmMeta
    predictedAt: datetime
