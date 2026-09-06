import json
import random
import subprocess
from pathlib import Path

from app.model_bundle import ModelBundle


def test_python_json_runtime_matches_javascript_reference_for_300_rows():
    root = Path(__file__).parents[1]
    model_path = root / "models" / "model_lgbm.json"
    model = ModelBundle.from_path(model_path)
    rng = random.Random(20260905)
    vectors = []
    expected = []
    expected_predictions = []

    for _ in range(300):
        current = {}
        previous = {}
        for feature in model.features[:36]:
            # 실제 합성 데이터처럼 0을 충분히 포함해야 missingType=NaN과
            # missingType=Zero의 분기 차이를 parity 검증에서 놓치지 않는다.
            current[feature] = 0 if rng.random() < 0.2 else rng.randint(1, 1_000_000)
            previous[feature] = 0 if rng.random() < 0.2 else rng.randint(1, 1_000_000)
        current["연령"] = rng.choice(model.cat_features["연령"])
        current["Life_Stage"] = rng.choice(model.cat_features["Life_Stage"])
        previous["연령"] = rng.choice(model.cat_features["연령"])
        previous["Life_Stage"] = rng.choice(model.cat_features["Life_Stage"])
        prediction, _ = model.predict(current, previous)
        expected.extend([prediction.hazard_1m, prediction.hazard_2m, prediction.hazard_3m])
        expected_predictions.append(prediction)
        vectors.extend(item["values"] for item in model.model_inputs(current, previous))

    completed = subprocess.run(
        ["node", str(Path(__file__).with_name("javascript_reference_predictor.js"))],
        input=json.dumps({"modelPath": str(model_path), "vectors": vectors}),
        text=True,
        capture_output=True,
        check=True,
    )
    actual = json.loads(completed.stdout)

    assert len(actual["hazards"]) == 900
    assert max(abs(left - right) for left, right in zip(actual["hazards"], expected)) <= 1e-12
    for reference, python_prediction in zip(actual["predictions"], expected_predictions):
        assert abs(reference["c3"] - python_prediction.cumulative_risk_3m) <= 1e-12
        assert reference["grade"] == python_prediction.risk_grade
        assert reference["topRiskPercent"] == python_prediction.top_risk_percent
