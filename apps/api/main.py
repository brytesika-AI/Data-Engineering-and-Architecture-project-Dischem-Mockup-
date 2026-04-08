from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from dischem_orchestrator.agent import AgentError, explain_inventory_exception
from dischem_orchestrator.api_data import DataServiceError, get_forecast, get_inventory_health, get_kpis_summary

app = FastAPI(title="Dis-Chem Inventory API", version="0.2.0")

KPI_PATH = Path("data/gold/kpi_summary.csv")
INVENTORY_HEALTH_PATH = Path("data/gold/mart_inventory_health.csv")
FORECAST_PATH = Path("data/gold/forecast_sku_store_daily.csv")
ALERTS_PATH = Path("data/gold/streaming_alerts.csv")
POLICY_PATH = Path("config/policies/agent_policy.json")
PROMPT_PATH = Path("config/prompts/inventory_agent_prompt.txt")
AUDIT_LOG_PATH = Path("models/llmops/agent_explanations_log.jsonl")


class AgentExplainRequest(BaseModel):
    date: str
    store_id: str
    sku_id: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/kpis")
def kpis(date: str | None = None, store_id: str | None = None) -> dict[str, object]:
    try:
        return get_kpis_summary(KPI_PATH, date=date, store_id=store_id)
    except DataServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/inventory/health")
def inventory_health(
    date: str | None = None,
    store_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, object]:
    try:
        return get_inventory_health(INVENTORY_HEALTH_PATH, date=date, store_id=store_id, limit=limit)
    except DataServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/forecast")
def forecast(
    store_id: str | None = None,
    sku_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
) -> dict[str, object]:
    try:
        return get_forecast(
            FORECAST_PATH,
            store_id=store_id,
            sku_id=sku_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    except DataServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/agent/explain")
def agent_explain(payload: AgentExplainRequest) -> dict[str, object]:
    try:
        response = explain_inventory_exception(
            day=payload.date,
            store_id=payload.store_id,
            sku_id=payload.sku_id,
            kpi_path=KPI_PATH,
            alerts_path=ALERTS_PATH,
            forecast_path=FORECAST_PATH,
            policy_path=POLICY_PATH,
            prompt_path=PROMPT_PATH,
            audit_log_path=AUDIT_LOG_PATH,
        )
        return response.as_dict()
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
