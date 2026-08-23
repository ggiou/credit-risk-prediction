# Credit Risk AI Server

FastAPI internal service for the Finance AI Challenge credit-card delinquency
early-warning project.

## Runtime boundary

- LightGBM JSON artifact: calculates risk.
- Local feature contribution extraction: selects evidence from the model input.
- OpenAI API: converts supplied risk/evidence into a short explanation only.
- Spring Boot: owns RDS access, result reuse/persistence, and browser-facing APIs.

The LLM must not recalculate risk, invent customer circumstances, or generate
recommendations in the MVP.

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
- returns risk rates, grade, percentile, and local risk factors;
- makes at most one successful LLM explanation call (one retry only for failure);
- keeps LightGBM results even when the LLM fails.

There is no rule-based prediction fallback. A missing, changed, or invalid model
returns model-unavailable rather than fabricating a replacement score.
