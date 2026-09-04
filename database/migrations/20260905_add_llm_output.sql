USE credit_risk;

ALTER TABLE prediction_result
ADD COLUMN llm_output JSON NULL
AFTER recommendation;
