# Dis-Chem Omni-Channel Inventory Orchestrator

A portfolio-grade data + AI platform simulation for executive inventory decision support in an omni-channel pharmacy and healthcare retail context.

## What This Project Delivers

- End-to-end medallion pipeline: `raw -> bronze -> silver -> gold`
- Executive KPI layer and risk marts
- Baseline SKU-store forecasting with backtest metrics and run registry
- Streaming alert simulation with severity scoring
- Governed AI inventory agent with audit logging
- FastAPI service and Streamlit executive dashboard
- CI smoke checks and local run scripts

## Current Repository Layout

```text
apps/
  api/                  FastAPI app (`/health`, `/kpis`, `/inventory/health`, `/forecast`, `/agent/explain`)
  dashboard/            Streamlit executive dashboard
config/
  data_contracts.yaml   Bronze contracts
  kpi_definitions.yaml  KPI definitions
  policies/             Agent guardrails/policies
  prompts/              Agent prompt templates
data/
  raw/                  Synthetic source datasets (generated)
  bronze/               Ingested raw layer
  silver/               Standardized entities/facts
  gold/                 Executive marts, KPIs, forecasts, streaming alerts
models/
  forecasting/          Forecast run metrics + registry
  llmops/               Agent explanation audit logs
orchestration/
  batch/                Batch jobs (ingest/build/train/agent)
  streaming/            Streaming simulator
scripts/
  seed_data.py          Synthetic data generation
  smoke_api.py          API smoke checks
  smoke_artifacts.py    Artifact availability checks
  start_app.ps1         Launch API + dashboard together
src/dischem_orchestrator/
  ingestion.py          Bronze ingestion logic
  silver.py             Silver transformations
  gold.py               Gold marts + KPI summary
  forecasting.py        Baseline forecasting + backtest
  streaming.py          Alert simulation
  agent.py              Governed agent reasoning + audit logs
tests/
  unit/                 Unit tests
  integration/          Pipeline/service integration tests
```

## Quick Start (Windows PowerShell)

### 1. Create and activate environment

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -U pip
python -m pip install -r apps/api/requirements.txt
python -m pip install -r apps/dashboard/requirements.txt
python -m pip install -r requirements-dev.txt
```

### 3. Generate 1-year synthetic data

```powershell
python scripts/seed_data.py --start-date 2025-01-01 --days 365 --stores 25 --skus 600 --seed 42
```

### 4. Run batch pipeline

```powershell
python orchestration/batch/ingest_pos.py
python orchestration/batch/ingest_sap.py
python orchestration/batch/ingest_clinic.py
python orchestration/batch/build_silver.py
python orchestration/batch/build_gold.py
```

### 5. Train forecast baseline

```powershell
python orchestration/batch/train_forecast.py --horizon-days 30 --holdout-days 28 --window-days 7
```

### 6. Run streaming simulator

```powershell
python orchestration/streaming/simulator.py
```

### 7. Run AI agent explanation (example)

```powershell
python orchestration/batch/run_agent_explain.py --date 2025-01-01 --store-id ST001
```

## Run the App

### Option A: Launch both together

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_app.ps1
```

- API docs: `http://127.0.0.1:8000/docs`
- Dashboard: `http://127.0.0.1:8501`

### Option B: Run separately

```powershell
uvicorn apps.api.main:app --reload --port 8000
streamlit run apps/dashboard/streamlit_app.py
```

## API Endpoints

- `GET /health`
- `GET /kpis?date=YYYY-MM-DD&store_id=ST001`
- `GET /inventory/health?date=YYYY-MM-DD&store_id=ST001&limit=200`
- `GET /forecast?store_id=ST001&sku_id=SKU00001&limit=500`
- `POST /agent/explain`

Example payload:

```json
{
  "date": "2025-01-01",
  "store_id": "ST001",
  "sku_id": "SKU00001"
}
```

## Validation / Smoke Checks

```powershell
python scripts/smoke_artifacts.py
python scripts/smoke_api.py
```

## Notes

- Generated datasets and model run artifacts are reproducible and ignored by default via `.gitignore`.
- If local Windows temp folders become lock-protected, they are safely ignored and do not affect pipeline execution.

## License

Use MIT for portfolio simplicity unless you plan to keep the repository private or more restricted.
