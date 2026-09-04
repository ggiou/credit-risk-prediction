from __future__ import annotations

import bisect
import hashlib
import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .features import DERIVED_FEATURES, derive_features

LOGGER = logging.getLogger(__name__)

GRADE_CODE_BY_KOREAN = {
    "정상": "NORMAL",
    "관심": "INTEREST",
    "주의": "CAUTION",
    "경고": "WARNING",
}
GRADE_KOREAN_BY_CODE = {code: korean for korean, code in GRADE_CODE_BY_KOREAN.items()}

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
    "청구금액_B0": "당월 청구금액",
    "청구금액_R3M": "최근 3개월 청구금액",
    "상환개월수_결제일_R3M": "최근 3개월 결제일 상환 개월 수",
    "선결제건수_R3M": "최근 3개월 선결제 건수",
    "연체건수_R6M": "최근 6개월 연체 건수",
    "연체건수_R3M": "최근 3개월 연체 건수",
    "잔액_B0M": "당월 총 카드 잔액",
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

LEAKAGE_FEATURES = {"연체잔액_B0M", "연체일수_B1M", "최종연체개월수_R15M"}
EXCLUDED_REASON_FEATURES = {"horizon", "연령", "남녀구분코드", "Life_Stage"} | LEAKAGE_FEATURES

PATTERN_FEATURES = {
    "PAYMENT_REGULARITY": {
        "상환개월수_결제일_R3M", "선결제건수_R3M", "연체건수_R3M", "연체건수_R6M",
        "시장단기연체여부_R3M", "시장단기연체여부_R6M", "회원여부_연체",
    },
    "CREDIT_AVAILABILITY": {
        "f_카드가용비율", "유효카드수_신용", "이용가능카드수_신용",
        "강제한도감액횟수_R12M", "강제한도감액금액_R12M",
        "자발한도감액횟수_R12M", "한도증액횟수_R12M", "카드이용한도금액",
        "카드이용한도금액_B1M", "f_한도변화", "한도심사요청건수", "한도요청거절건수",
    },
    "SHORT_TERM_BORROWING": {
        "잔액_현금서비스_B0M", "잔액_카드론_B0M", "잔액_리볼빙일시불이월_B0M",
        "f_현금서비스비중", "f_카드론비중", "f_리볼빙비중",
        "f_현금서비스증가", "f_카드론증가", "RV약정청구율", "CA한도금액",
    },
    "BALANCE_EXPOSURE": {
        "f_사용률", "f_사용률변화", "f_잔액증가율", "잔액_B0M", "월중평잔",
        "잔액_일시불_B0M", "잔액_할부_B0M",
    },
    "BILLING_PRESSURE": {"청구금액_B0", "청구금액_R3M", "f_청구금액증가"},
    "CARD_ACTIVITY": {"이용금액_R3M_신용", "유효카드수_신용", "이용가능카드수_신용", "이용카드수_신용"},
}

PATTERN_NAMES = {
    "PAYMENT_REGULARITY": "최근 상환 규칙성과 연체 관찰",
    "CREDIT_AVAILABILITY": "카드 이용 가능 상태와 한도 조정 이력",
    "SHORT_TERM_BORROWING": "단기성 신용 이용 구성과 변화",
    "BALANCE_EXPOSURE": "한도 대비 잔액 부담과 잔액 구성",
    "BILLING_PRESSURE": "당월 및 최근 누적 청구 부담",
    "CARD_ACTIVITY": "최근 카드 활동 수준",
}

COUNTERFACTUAL_EVIDENCE = {
    "카드이용한도금액": ("카드이용한도금액", "f_사용률", "f_한도변화", "f_사용률변화"),
    "이용가능카드수_신용": ("이용가능카드수_신용", "f_카드가용비율"),
    "유효카드수_신용": ("유효카드수_신용", "f_카드가용비율"),
    "잔액_B0M": (
        "잔액_B0M", "f_사용률", "f_현금서비스비중", "f_카드론비중",
        "f_리볼빙비중", "f_잔액증가율", "f_사용률변화",
    ),
    "잔액_현금서비스_B0M": ("잔액_현금서비스_B0M", "f_현금서비스비중", "f_현금서비스증가"),
    "잔액_카드론_B0M": ("잔액_카드론_B0M", "f_카드론비중", "f_카드론증가"),
    "잔액_리볼빙일시불이월_B0M": ("잔액_리볼빙일시불이월_B0M", "f_리볼빙비중"),
    "청구금액_B0": ("청구금액_B0", "f_청구금액증가"),
}


@dataclass(frozen=True)
class ModelPrediction:
    hazard_1m: float
    hazard_2m: float
    hazard_3m: float
    cumulative_risk_3m: float
    risk_grade: str
    top_risk_percent: float

    @property
    def percentile(self) -> float:
        """기존 API 소비자를 위한 호환 이름이다."""

        return self.top_risk_percent


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
        required_thresholds = {"관심", "주의", "경고"}
        if set(self.grade_thresholds) != required_thresholds:
            raise ModelContractError("grade_thresholds must contain 관심, 주의, 경고")
        thresholds = [float(self.grade_thresholds[key]) for key in ("관심", "주의", "경고")]
        if thresholds != sorted(thresholds) or len(set(thresholds)) != 3:
            raise ModelContractError("grade_thresholds must be strictly increasing")
        if not self.c3_quantiles or self.c3_quantiles != sorted(self.c3_quantiles):
            raise ModelContractError("c3_quantiles must be a non-empty sorted array")
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
            encoded = int(value)
            return encoded if encoded < len(categories) else None
        if isinstance(value, int):
            return value if 0 <= value < len(categories) else None
        if isinstance(value, float) and value.is_integer():
            encoded = int(value)
            return encoded if 0 <= encoded < len(categories) else None
        text = str(value)
        return categories.index(text) if text in categories else None

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
        for name in self.features:
            value = enriched.get(name)
            if name in self.cat_features and value is not None:
                encoded = self._normalize_category(name, value)
                if encoded is None:
                    raise ModelContractError(
                        f"unsupported category for {name}: {value!r}"
                    )
                value = encoded
            vector.append(value)
        return vector, enriched

    def _tree_leaf(self, tree: list[Any], vector: list[Any]) -> float:
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
        return selected

    def _predict_horizon(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
        horizon: int,
    ) -> tuple[float, dict[str, Any]]:
        vector, enriched = self._vector(current, previous, horizon)
        raw_score = 0.0
        for tree in self.trees:
            raw_score += self._tree_leaf(tree, vector)
        return self._sigmoid(raw_score), enriched

    def _risk_grade(self, cumulative_risk_3m: float) -> str:
        interest = float(self.grade_thresholds["관심"])
        caution = float(self.grade_thresholds["주의"])
        warning = float(self.grade_thresholds["경고"])
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
    ) -> tuple[ModelPrediction, dict[str, Any]]:
        h1, _ = self._predict_horizon(current, previous, 1)
        h2, _ = self._predict_horizon(current, previous, 2)
        h3, enriched = self._predict_horizon(current, previous, 3)
        cumulative = 1.0 - ((1.0 - h1) * (1.0 - h2) * (1.0 - h3))
        prediction = ModelPrediction(
            hazard_1m=h1,
            hazard_2m=h2,
            hazard_3m=h3,
            cumulative_risk_3m=cumulative,
            risk_grade=self._risk_grade(cumulative),
            top_risk_percent=self._percentile(cumulative),
        )
        return prediction, enriched

    def model_inputs(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """parity·감사 검증에 사용할 실제 48개 모델 입력을 horizon별로 반환한다."""

        result = []
        for horizon in (1, 2, 3):
            vector, _ = self._vector(current, previous, horizon)
            result.append({
                "horizon": horizon,
                "values": [None if self._is_missing(value) else value for value in vector],
            })
        return result

    def risk_factors(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
        enriched: dict[str, Any],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """전월값 복원 재채점으로 변화의 모델 방향을 계산한다.

        JSON 산출물만으로는 정확한 SHAP을 계산할 수 없다. 각 원천 피처를 전월값으로
        복원한 뒤 ``derive_features``가 11개 파생값을 전부 다시 만들도록 하며, 결과를
        현재 상태의 확정 원인이 아닌 counterfactual 근거로만 반환한다.
        """

        if not previous:
            return []

        current_prediction, _ = self.predict(current, previous)
        self._monitor_protected_changes(current, previous, current_prediction)
        candidates: list[tuple[float, dict[str, Any]]] = []
        for source_key in self.features:
            if source_key in DERIVED_FEATURES or source_key in EXCLUDED_REASON_FEATURES:
                continue
            if source_key not in current or source_key not in previous:
                continue
            current_value = current.get(source_key)
            previous_value = previous.get(source_key)
            if current_value == previous_value:
                continue

            counterfactual_current = dict(current)
            counterfactual_current[source_key] = previous_value
            counterfactual_prediction, counterfactual_enriched = self.predict(
                counterfactual_current, previous
            )
            delta = (
                current_prediction.cumulative_risk_3m
                - counterfactual_prediction.cumulative_risk_3m
            )
            if math.isclose(delta, 0.0, rel_tol=0.0, abs_tol=1e-15):
                continue

            evidence_keys = list(COUNTERFACTUAL_EVIDENCE.get(source_key, (source_key,)))
            evidence_keys = [
                key for key in evidence_keys
                if enriched.get(key) != counterfactual_enriched.get(key)
            ] or [source_key]
            pattern_code = self._pattern_for(source_key, evidence_keys)
            change_value, change_rate = self._change(current_value, previous_value)
            top_risk_percent_difference = round(abs(
                current_prediction.top_risk_percent
                - counterfactual_prediction.top_risk_percent
            ), 4)
            candidates.append((abs(delta), {
                "featureKey": source_key,
                "displayName": DISPLAY_NAMES.get(source_key, source_key),
                "reasonMethod": "PREVIOUS_VALUE_COUNTERFACTUAL",
                "modelDirection": "INCREASE_RISK" if delta > 0 else "DECREASE_RISK",
                # direction은 기존 화면 소비자를 위한 호환 필드다.
                "direction": "INCREASE" if delta > 0 else "DECREASE",
                "currentValue": current_value,
                "previousValue": previous_value,
                "changeValue": change_value,
                "changeRate": change_rate,
                "counterfactualGrade": GRADE_KOREAN_BY_CODE[counterfactual_prediction.risk_grade],
                "currentTopRiskPercent": current_prediction.top_risk_percent,
                "counterfactualTopRiskPercent": counterfactual_prediction.top_risk_percent,
                "topRiskPercentDifference": top_risk_percent_difference,
                "counterfactualRiskDirection": (
                    "CURRENT_MORE_RISKY" if delta > 0 else "CURRENT_LESS_RISKY"
                ),
                "counterfactualGradeChanged": (
                    current_prediction.risk_grade != counterfactual_prediction.risk_grade
                ),
                "evidenceFeatureKeys": evidence_keys,
                "unit": self._unit_for(source_key),
                "patternCode": pattern_code,
                "patternName": PATTERN_NAMES[pattern_code],
            }))

        # 위험 증가 방향을 먼저 보여주고, 부족한 경우에만 완화 방향 근거를 보충한다.
        candidates.sort(
            key=lambda item: (
                item[1]["modelDirection"] != "INCREASE_RISK",
                -item[0],
                item[1]["featureKey"],
            )
        )
        result = [candidate for _, candidate in candidates[:limit]]
        for rank, reason in enumerate(result, start=1):
            reason["rank"] = rank
            reason["reasonId"] = f"R{rank}"
        return result

    def _monitor_protected_changes(
        self,
        current: dict[str, Any],
        previous: dict[str, Any],
        current_prediction: ModelPrediction,
    ) -> None:
        """보호 성격 피처의 큰 counterfactual 영향은 고객 설명 대신 감사 로그로 남긴다."""

        for feature_key in ("연령", "남녀구분코드", "Life_Stage"):
            if feature_key not in current or feature_key not in previous:
                continue
            if current.get(feature_key) == previous.get(feature_key):
                continue
            counterfactual = dict(current)
            counterfactual[feature_key] = previous.get(feature_key)
            comparison, _ = self.predict(counterfactual, previous)
            delta = current_prediction.cumulative_risk_3m - comparison.cumulative_risk_3m
            if abs(delta) >= 0.01:
                LOGGER.warning(
                    "MODEL_MONITOR_PROTECTED_FEATURE feature=%s abs_c3_delta=%.12f",
                    feature_key,
                    abs(delta),
                )

    @staticmethod
    def _change(current_value: Any, previous_value: Any) -> tuple[float | None, float | None]:
        if not isinstance(current_value, (int, float)) or isinstance(current_value, bool):
            return None, None
        if not isinstance(previous_value, (int, float)) or isinstance(previous_value, bool):
            return None, None
        change = float(current_value) - float(previous_value)
        rate = change / float(previous_value) if float(previous_value) != 0 else None
        return change, rate

    @staticmethod
    def _pattern_for(source_key: str, evidence_keys: list[str]) -> str:
        # 원천 피처의 명시적 업무 패턴을 최우선한다. 잔액_B0M처럼 관련 파생값이
        # 여러 패턴에 걸치는 경우 evidence 문자열 순서로 오분류하지 않는다.
        for pattern_code, feature_keys in PATTERN_FEATURES.items():
            if source_key in feature_keys:
                return pattern_code
        for pattern_code, feature_keys in PATTERN_FEATURES.items():
            if any(key in feature_keys for key in evidence_keys):
                return pattern_code
        return "CARD_ACTIVITY"

    @staticmethod
    def _unit_for(feature_key: str) -> str:
        if feature_key in RATIO_FEATURES or "율" in feature_key or "비율" in feature_key:
            return "RATIO"
        if "여부" in feature_key:
            return "FLAG"
        if any(token in feature_key for token in ("금액", "잔액", "한도")) or feature_key == "월중평잔":
            return "AMOUNT"
        if any(token in feature_key for token in ("횟수", "건수", "카드수", "개월수")):
            return "COUNT"
        return "VALUE"
