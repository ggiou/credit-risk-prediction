from app.hashing import prediction_input_hash


def test_input_hash_is_stable_for_key_order():
    a = prediction_input_hash(
        model_version="m1",
        feature_schema_version="v1",
        prompt_version="p1",
        generate_explanation=True,
        current_features={"b": 2, "a": 1},
        previous_features={"y": 2, "x": 1},
    )
    b = prediction_input_hash(
        model_version="m1",
        feature_schema_version="v1",
        prompt_version="p1",
        generate_explanation=True,
        current_features={"a": 1, "b": 2},
        previous_features={"x": 1, "y": 2},
    )
    assert a == b
    assert len(a) == 64
