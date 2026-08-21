"""LightGBM 모델 로드, 추론, 위험 요인 추출을 담당한다."""

import json
import math
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from app.core.config import Settings
from app.schemas.prediction import PredictionValues, RiskFactor
from app.services.feature_service import calculate_derived_features, clean_number


DISPLAY_NAMES = {
    "f_사용률": "카드 한도 사용률",
    "f_현금서비스비중": "현금서비스 비중",
    "f_카드론비중": "카드론 비중",
    "f_리볼빙비중": "리볼빙 이월 비중",
    "f_잔액증가율": "총 카드 잔액 증가율",
    "f_사용률변화": "카드 한도 사용률 변화",
    "f_청구금액증가": "청구금액 변화",
}


class ModelNotLoadedError(RuntimeError):
    """실제 모델이 없고 개발용 대체 계산도 허용되지 않은 상태다."""


class ModelService:
    """모델 파일을 한 번 로드하고 요청별 위험률을 계산한다."""

    def __init__(self, settings: Settings):
        """설정된 모델과 고정 피처 순서를 로드한다."""

        self.settings = settings
        self.booster: lgb.Booster | None = None
        self.feature_order: list[str] = []
        if settings.model_path.exists() and settings.feature_order_path.exists():
            # 모델 파일과 학습 열 순서가 모두 있을 때만 실제 추론을 활성화한다.
            self.booster = lgb.Booster(model_file=str(settings.model_path))
            self.feature_order = self._load_feature_order(settings.feature_order_path)

    @property
    def loaded(self) -> bool:
        """실제 LightGBM 모델 로드 여부를 반환한다."""

        return self.booster is not None and bool(self.feature_order)

    def predict(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
    ) -> tuple[PredictionValues, list[RiskFactor]]:
        """1·2·3개월 위험률과 주요 위험 요인을 계산한다."""

        derived = calculate_derived_features(current, previous)
        if self.loaded:
            hazards = [self._predict_horizon(current, derived, horizon) for horizon in (1, 2, 3)]
        elif self.settings.allow_rule_based_fallback:
            # 개발용 대체값은 명시적으로 활성화한 환경에서만 화면·연동 테스트에 사용한다.
            hazards = self._development_hazards(current, derived)
        else:
            raise ModelNotLoadedError("LightGBM 모델과 feature-order.json을 찾을 수 없습니다.")

        cumulative = 1.0 - math.prod(1.0 - value for value in hazards)
        grade = self._risk_grade(hazards[2])
        prediction = PredictionValues(
            hazard1m=hazards[0],
            hazard2m=hazards[1],
            hazard3m=hazards[2],
            cumulativeRisk3m=round(cumulative, 6),
            riskGrade=grade,
            # 실제 운영 백분위는 학습·검증 분포 파일로 교체해야 한다.
            percentile=round(min(100.0, max(0.0, hazards[2] * 100.0)), 2),
        )
        return prediction, self._risk_factors(derived)

    def _load_feature_order(self, path: Path) -> list[str]:
        """학습 시 고정한 모델 입력 열 순서를 읽는다."""

        with path.open("r", encoding="utf-8") as file:
            values = json.load(file)
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError("feature-order.json은 문자열 배열이어야 합니다.")
        return values

    def _predict_horizon(
        self,
        current: dict[str, Any],
        derived: dict[str, float | None],
        horizon: int,
    ) -> float:
        """고정 열 순서에 horizon을 추가해 한 시점의 위험률을 추론한다."""

        values = {**current, **derived, "horizon": horizon}
        row = [np.nan if clean_number(values.get(key)) is None else clean_number(values.get(key)) for key in self.feature_order]
        result = float(self.booster.predict(np.asarray([row], dtype=float))[0])
        return round(min(1.0, max(0.0, result)), 6)

    def _development_hazards(
        self,
        current: dict[str, Any],
        derived: dict[str, float | None],
    ) -> list[float]:
        """실제 모델 연동 전 API 확인에만 사용할 투명한 규칙 기반 값을 계산한다."""

        usage = derived.get("f_사용률") or 0.0
        cash_ratio = derived.get("f_현금서비스비중") or 0.0
        loan_ratio = derived.get("f_카드론비중") or 0.0
        revolving_ratio = derived.get("f_리볼빙비중") or 0.0
        delinquency = clean_number(current.get("시장단기연체여부_R3M")) or 0.0
        raw = -3.2 + usage * 1.8 + cash_ratio * 1.2 + loan_ratio + revolving_ratio + delinquency * 1.4
        base = 1.0 / (1.0 + math.exp(-raw))
        return [round(min(0.999999, base * factor), 6) for factor in (0.75, 1.0, 1.25)]

    def _risk_grade(self, hazard_3m: float) -> str:
        """3개월 위험률을 확정된 API 위험등급으로 구분한다."""

        if hazard_3m < 0.20:
            return "NORMAL"
        if hazard_3m < 0.35:
            return "INTEREST"
        if hazard_3m < 0.55:
            return "CAUTION"
        return "WARNING"

    def _risk_factors(self, derived: dict[str, float | None]) -> list[RiskFactor]:
        """변화 크기가 큰 파생 피처를 설명 입력용 주요 요인으로 선정한다."""

        candidates: list[tuple[str, float]] = []
        for key, value in derived.items():
            if key in DISPLAY_NAMES and value is not None:
                candidates.append((key, abs(float(value))))
        candidates.sort(key=lambda item: item[1], reverse=True)

        factors: list[RiskFactor] = []
        for key, magnitude in candidates[:5]:
            value = derived[key]
            factors.append(
                RiskFactor(
                    featureKey=key,
                    displayName=DISPLAY_NAMES[key],
                    direction="INCREASE" if value and value > 0 else "DECREASE" if value and value < 0 else "MAINTAIN",
                    previousValue=None,
                    currentValue=value,
                    changeValue=value if "변화" in DISPLAY_NAMES[key] or "증가" in DISPLAY_NAMES[key] else None,
                    changeRate=None,
                    unit="AMOUNT" if key == "f_청구금액증가" else "RATIO",
                    contribution=round(magnitude, 6),
                )
            )
        return factors

