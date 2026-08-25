from __future__ import annotations

import bisect
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .features import DERIVED_FEATURES, derive_features

GRADE_CODE_BY_KOREAN = {
    "정상": "NORMAL",
    "관심": "INTEREST",
    "주의": "CAUTION",
    "경고": "WARNING",
}

DISPLAY_NAMES = {
    "남녀구분코드": "성별",
    "연령": "연령대",
    "입회경과개월수_신용": "신용카드 가입 경과 개월 수",
    "회원여부_연체": "회원 연체 여부",
    "유효카드수_신용": "유효 신용카드 수",
    "이용가능카드수_신용": "이용 가능 신용카드 수",
    "이용카드수_신용": "이용 신용카드 수",
    "이용금액_R3M_신용": "최근 3개월 신용카드 이용금액",
    "Life_Stage": "라이프 스테이지",
    "카드이용한도금액": "카드 이용한도",
    "CA한도금액": "현금서비스 이용한도",
    "RV약정청구율": "리볼빙 약정 청구율",
    "자발한도감액횟수_R12M": "최근 12개월 자발적 한도 감액 횟수",
    "강제한도감액횟수_R12M": "최근 12개월 강제 한도 감액 횟수",
    "강제한도감액금액_R12M": "최근 12개월 강제 한도 감액금액",
    "한도증액횟수_R12M": "최근 12개월 한도 증액 횟수",
    "카드이용한도금액_B1M": "전월 카드 이용한도",
    "한도심사요청건수": "한도 심사 요청 건수",
    "한도요청거절건수": "한도 요청 거절 건수",
    "시장단기연체여부_R6M": "최근 6개월 시장 단기연체 여부",
    "시장단기연체여부_R3M": "최근 3개월 시장 단기연체 여부",
    "청구금액_B0": "기준월 청구금액",
    "청구금액_R3M": "최근 3개월 청구금액",
    "상환개월수_결제일_R3M": "최근 3개월 결제일 상환 개월 수",
    "선결제건수_R3M": "최근 3개월 선결제 건수",
    "연체건수_R6M": "최근 6개월 연체 건수",
    "연체건수_R3M": "최근 3개월 연체 건수",
    "잔액_B0M": "기준월 총 카드 잔액",
    "잔액_일시불_B0M": "기준월 일시불 잔액",
    "잔액_할부_B0M": "기준월 할부 잔액",
    "잔액_현금서비스_B0M": "기준월 현금서비스 잔액",
    "잔액_리볼빙일시불이월_B0M": "기준월 리볼빙 일시불 이월잔액",
    "잔액_카드론_B0M": "기준월 카드론 잔액",
    "잔액_현금서비스_B1M": "전월 현금서비스 잔액",
    "잔액_카드론_B1M": "전월 카드론 잔액",
    "월중평잔": "월중 평균잔액",
    "f_사용률": "카드 한도 사용률",
    "f_현금서비스비중": "현금서비스 비중",
    "f_카드론비중": "카드론 비중",
    "f_리볼빙비중": "리볼빙 비중",
    "f_현금서비스증가": "현금서비스 잔액 증가",
    "f_카드론증가": "카드론 잔액 증가",
    "f_한도변화": "카드 이용한도 변화",
    "f_잔액증가율": "총잔액 증가율",
    "f_사용률변화": "카드 한도 사용률 변화",
    "f_청구금액증가": "청구금액 증가",
    "f_카드가용비율": "이용 가능 카드 비율",
}

RATIO_FEATURES = {
    "f_사용률",
    "f_현금서비스비중",
    "f_카드론비중",
    "f_리볼빙비중",
    "f_잔액증가율",
    "f_사용률변화",
    "f_카드가용비율",
}


@dataclass(frozen=True)
class ModelPrediction:
    hazard_1m: float
    hazard_2m: float
    hazard_3m: float
    cumulative_risk_3m: float
    risk_grade: str
    percentile: float


class ModelContractError(RuntimeError):
    pass


class ModelBundle:
    """
    Runtime for the compact `model_lgbm.json` artifact supplied by the AI teammate.

    The artifact contains one-split LightGBM trees as:
      [featureIndex, isCategorical, thresholdOrCategoryIds,
       defaultLeft, zeroAsMissing, leftLeaf, rightLeaf]

    Leaf values are already trained model values. This server does not retrain,
    alter, rescale, or rewrite the model artifact.
    """

    def __init__(self, payload: dict[str, Any], source_sha256: str):
        self.payload = payload
        self.source_sha256 = source_sha256
        self.model_version = str(payload["model_version"])
        self.features = list(payload["features"])
        self.horizon_index = int(payload["horizon_index"])
        self.cat_features = dict(payload.get("cat_features", {}))
        self.grade_thresholds = dict(payload.get("grade_thresholds", {}))
        self.c3_quantiles = [float(v) for v in payload.get("c3_quantiles", [])]
        self.trees = list(payload["trees"])
        self._validate_contract()

    @classmethod
    def from_path(cls, path: Path, expected_sha256: str = "") -> "ModelBundle":
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if expected_sha256 and digest.lower() != expected_sha256.lower():
            raise ModelContractError(
                f"model SHA-256 mismatch: expected={expected_sha256}, actual={digest}"
            )
        payload = json.loads(raw.decode("utf-8"))
        return cls(payload=payload, source_sha256=digest)

    def _validate_contract(self) -> None:
        if self.payload.get("objective") != "binary-sigmoid":
            raise ModelContractError("only binary-sigmoid model artifacts are supported")
        if len(self.features) != 48:
            raise ModelContractError(f"expected 48 model features, got {len(self.features)}")
        if self.features[self.horizon_index] != "horizon":
            raise ModelContractError("horizon_index does not point to the horizon feature")
        if not self.trees:
            raise ModelContractError("model contains no trees")
        for idx, tree in enumerate(self.trees):
            if not isinstance(tree, list) or len(tree) != 7:
                raise ModelContractError(f"tree[{idx}] must contain exactly 7 values")
            feature_index = int(tree[0])
            if feature_index < 0 or feature_index >= len(self.features):
                raise ModelContractError(f"tree[{idx}] has invalid feature index")

    @staticmethod
    def _sigmoid(raw_score: float) -> float:
        if raw_score >= 0:
            z = math.exp(-raw_score)
            return 1.0 / (1.0 + z)
        z = math.exp(raw_score)
        return z / (1.0 + z)

    def _normalize_category(self, feature_name: str, value: Any) -> int | None:
        categories = self.cat_features.get(feature_name)
        if not categories:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        text = str(value)
        if text in categories:
            return categories.index(text)
        for idx, category in enumerate(categories):
            suffix = category.split(".", 1)[-1]
            if text == suffix:
                return idx
        return None

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or (isinstance(value, float) and math.isnan(value))

    def _vector(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
        horizon: int,
    ) -> tuple[list[Any], dict[str, Any]]:
        enriched = derive_features(current, previous)
        enriched["horizon"] = horizon
        vector: list[Any] = []
        missing = []
        for name in self.features:
            value = enriched.get(name)
            if name in self.cat_features and value is not None:
                encoded = self._normalize_category(name, value)
                if encoded is None:
                    raise ModelContractError(
                        f"unsupported category for {name}: {value!r}"
                    )
                value = encoded
            if value is None and name not in DERIVED_FEATURES:
                missing.append(name)
            vector.append(value)
        if missing:
            raise ModelContractError(
                "missing required base model features: " + ", ".join(missing)
            )
        return vector, enriched

    def _tree_leaf(self, tree: list[Any], vector: list[Any]) -> tuple[float, float, str]:
        feature_index = int(tree[0])
        is_categorical = bool(tree[1])
        threshold = tree[2]
        default_left = bool(tree[3])
        zero_as_missing = bool(tree[4])
        left_leaf = float(tree[5])
        right_leaf = float(tree[6])

        value = vector[feature_index]
        missing = self._is_missing(value) or (
            zero_as_missing and isinstance(value, (int, float)) and value == 0
        )
        if missing:
            go_left = default_left
        elif is_categorical:
            go_left = int(value) in {int(v) for v in threshold}
        else:
            go_left = float(value) <= float(threshold)

        selected = left_leaf if go_left else right_leaf
        midpoint = (left_leaf + right_leaf) / 2.0
        contribution = selected - midpoint
        return selected, contribution, self.features[feature_index]

    def _predict_horizon(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
        horizon: int,
    ) -> tuple[float, dict[str, float], dict[str, Any]]:
        vector, enriched = self._vector(current, previous, horizon)
        raw_score = 0.0
        contributions: dict[str, float] = {}
        for tree in self.trees:
            leaf, local_delta, feature_name = self._tree_leaf(tree, vector)
            raw_score += leaf
            contributions[feature_name] = contributions.get(feature_name, 0.0) + local_delta
        return self._sigmoid(raw_score), contributions, enriched

    def _risk_grade(self, cumulative_risk_3m: float) -> str:
        interest = float(self.grade_thresholds.get("관심", 0.03))
        caution = float(self.grade_thresholds.get("주의", 0.08))
        warning = float(self.grade_thresholds.get("경고", 0.15))
        if cumulative_risk_3m >= warning:
            return "WARNING"
        if cumulative_risk_3m >= caution:
            return "CAUTION"
        if cumulative_risk_3m >= interest:
            return "INTEREST"
        return "NORMAL"

    def _percentile(self, cumulative_risk_3m: float) -> float:
        if not self.c3_quantiles:
            return 0.0
        if len(self.c3_quantiles) == 1:
            return 100.0
        # 전달 모델의 predict.js와 동일하게 누적위험이 큰 고객부터 상위 백분위를 계산한다.
        index = max(0, bisect.bisect_right(self.c3_quantiles, cumulative_risk_3m) - 1)
        upper_percentile = (1.0 - index / (len(self.c3_quantiles) - 1)) * 100.0
        return round(max(0.001, upper_percentile), 4)

    def predict(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
    ) -> tuple[ModelPrediction, dict[str, float], dict[str, Any]]:
        h1, _, _ = self._predict_horizon(current, previous, 1)
        h2, _, _ = self._predict_horizon(current, previous, 2)
        h3, contributions, enriched = self._predict_horizon(current, previous, 3)
        cumulative = 1.0 - ((1.0 - h1) * (1.0 - h2) * (1.0 - h3))
        prediction = ModelPrediction(
            hazard_1m=h1,
            hazard_2m=h2,
            hazard_3m=h3,
            cumulative_risk_3m=cumulative,
            risk_grade=self._risk_grade(cumulative),
            percentile=self._percentile(cumulative),
        )
        return prediction, contributions, enriched

    def risk_factors(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
        contributions: dict[str, float],
        enriched: dict[str, Any],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        candidates = [
            (key, score)
            for key, score in contributions.items()
            if key != "horizon" and score > 0
        ]
        if not candidates:
            candidates = [
                (key, score)
                for key, score in contributions.items()
                if key != "horizon"
            ]
        candidates.sort(key=lambda item: abs(item[1]), reverse=True)

        previous_enriched = derive_features(previous, None) if previous else {}
        result = []
        for feature_key, contribution in candidates[:limit]:
            current_value = enriched.get(feature_key)
            previous_value = previous_enriched.get(feature_key)
            if feature_key not in DERIVED_FEATURES:
                current_value = current.get(feature_key)
                previous_value = previous.get(feature_key) if previous else None

            change_value = None
            change_rate = None
            if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
                change_value = float(current_value) - float(previous_value)
                if float(previous_value) != 0:
                    change_rate = change_value / float(previous_value)

            result.append(
                {
                    "featureKey": feature_key,
                    "displayName": DISPLAY_NAMES.get(feature_key, feature_key),
                    "direction": "INCREASE" if contribution >= 0 else "DECREASE",
                    "previousValue": previous_value,
                    "currentValue": current_value,
                    "changeValue": change_value,
                    "changeRate": change_rate,
                    "unit": "RATIO" if feature_key in RATIO_FEATURES else "VALUE",
                    "contribution": contribution,
                }
            )
        return result
