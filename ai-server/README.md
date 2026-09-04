# Credit Risk AI Server

FastAPI internal service for the Finance AI Challenge credit-card delinquency
early-warning project.

## Runtime boundary

- LightGBM JSON artifact: calculates risk.
- Previous-value counterfactual rescoring: ranks observed changes without claiming SHAP.
- OpenAI API: selects backend-approved indicator candidates and writes their interpretation only.
- Spring Boot: owns RDS access, result reuse/persistence, and browser-facing APIs.

The LLM must not recalculate risk, invent customer circumstances, or generate
product recommendations in the MVP. Review points are limited to backend-approved
checks directly linked to model evidence.

## Model file

The trained model is intentionally not committed.

Place the AI teammate's final artifact at:

```text
ai-server/models/model_lgbm.json
```

Expected metadata:

```text
model_version = miribom-lgbm-v0.3
features      = 48 (36 base + horizon + 11 derived)
```

Expected SHA-256:

```text
71494be683a0c6865d78f001c69a58f25de9adcda543295954c3f0503fe0f5ac
```

The runtime verifies this checksum before serving predictions. Do not retrain,
edit, pretty-print, or otherwise rewrite the model JSON.

## Run

```bash
cd ai-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Load `.env` using your local runtime/process manager. Never commit API keys.

Internal endpoints:

```text
GET  /internal/v1/health
POST /internal/v1/predictions
GET  /internal/docs
```

## Prediction contract

The POST contract follows `credit_risk_api_spec.md`:

- receives 36 base features for current month;
- optionally receives previous-month features;
- calculates 11 derived features using the fixed Python formulas;
- runs the same model at `horizon=1,2,3`;
- returns monthly hazards, c3-based grade, top-risk percentage, and counterfactual reasons;
- deterministically calculates observed changes, counterfactual rank differences,
  pattern mappings, indicator candidates, and grade-based management priority;
- stores validated `keyIndicators`, source IDs, and full structured output while
  rendering legacy explanation/recommendation strings for compatibility;
- makes one LLM explanation call, with one correction retry only when the returned JSON fails schema or content validation;
- uses a 60-second OpenAI timeout by default and does not repeat network timeouts;
- keeps LightGBM results even when the LLM fails.

There is no rule-based prediction fallback. A missing, changed, or invalid model
returns model-unavailable rather than fabricating a replacement score.
