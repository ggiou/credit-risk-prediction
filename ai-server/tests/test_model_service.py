"""모델 미탑재와 개발용 대체 계산의 경계를 검증한다."""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.model_service import ModelNotLoadedError, ModelService


def settings(tmp_path: Path, allow_fallback: bool) -> Settings:
    """존재하지 않는 모델 경로를 사용하는 테스트 설정을 만든다."""

    return Settings(
        model_path=tmp_path / "missing-model.txt",
        feature_order_path=tmp_path / "missing-order.json",
        allow_rule_based_fallback=allow_fallback,
    )


def test_missing_model_fails_without_fallback(tmp_path: Path) -> None:
    """대체 모드를 켜지 않으면 모델 미탑재를 성공으로 처리하지 않는다."""

    service = ModelService(settings(tmp_path, False))
    with pytest.raises(ModelNotLoadedError):
        service.predict({"카드이용한도금액": 1_000_000, "잔액_B0M": 500_000}, None)


def test_development_fallback_returns_bounded_risk(tmp_path: Path) -> None:
    """명시적으로 활성화한 개발 모드는 0~1 위험률만 반환한다."""

    service = ModelService(settings(tmp_path, True))
    prediction, _ = service.predict(
        {
            "카드이용한도금액": 1_000_000,
            "잔액_B0M": 500_000,
            "잔액_현금서비스_B0M": 100_000,
            "잔액_카드론_B0M": 100_000,
            "잔액_리볼빙일시불이월_B0M": 50_000,
        },
        None,
    )

    assert 0 <= prediction.hazard_1m <= prediction.hazard_2m <= prediction.hazard_3m <= 1

