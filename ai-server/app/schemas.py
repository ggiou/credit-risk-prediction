from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requestId: str
    customerId: str
    baseYm: str = Field(pattern=r"^\d{6}$")
    featureSnapshotId: int
    previousFeatureSnapshotId: int | None = None
    featureSchemaVersion: str
    expectedModelVersion: str
    promptVersion: str = "v1.0"
    generateExplanation: bool = True
    currentFeatures: dict[str, Any]
    previousFeatures: dict[str, Any] | None = None


class PredictionValues(BaseModel):
    hazard1m: float = Field(ge=0, le=1)
    hazard2m: float = Field(ge=0, le=1)
    hazard3m: float = Field(ge=0, le=1)
    cumulativeRisk3m: float = Field(ge=0, le=1)
    riskGrade: Literal["NORMAL", "INTEREST", "CAUTION", "WARNING"]
    percentile: float = Field(ge=0, le=100)


class RiskFactor(BaseModel):
    featureKey: str
    displayName: str
    direction: Literal["INCREASE", "DECREASE"]
    previousValue: Any | None = None
    currentValue: Any | None = None
    changeValue: float | None = None
    changeRate: float | None = None
    unit: str
    contribution: float


class LlmMeta(BaseModel):
    status: Literal["NOT_REQUESTED", "COMPLETED", "FAILED"]
    promptVersion: str
    errorMessage: str | None = None


class PredictResponse(BaseModel):
    requestId: str
    customerId: str
    baseYm: str
    featureSnapshotId: int
    featureSchemaVersion: str
    modelVersion: str
    prediction: PredictionValues
    riskFactors: list[RiskFactor]
    explanation: str | None = None
    usedFeatureKeys: list[str] = []
    llm: LlmMeta
    inputHash: str
    predictedAt: datetime
