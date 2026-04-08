"""Shared data access helpers for API and dashboard."""

from __future__ import annotations

import csv
from pathlib import Path


class DataServiceError(Exception):
    """Raised when required data assets are missing or malformed."""


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise DataServiceError(f"Missing dataset: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _latest_by_date(rows: list[dict[str, str]], date_key: str = "date") -> str | None:
    dates = [r.get(date_key, "") for r in rows if r.get(date_key)]
    return max(dates) if dates else None


def get_kpis_summary(kpi_path: Path, date: str | None = None, store_id: str | None = None) -> dict[str, object]:
    rows = _read_rows(kpi_path)
    if not rows:
        return {"rows": 0, "metrics": {}}

    target_date = date or _latest_by_date(rows, "date")
    filtered = [r for r in rows if r.get("date") == target_date]
    if store_id:
        filtered = [r for r in filtered if r.get("store_id") == store_id]

    if not filtered:
        return {"date": target_date, "store_id": store_id, "rows": 0, "metrics": {}}

    def avg(name: str) -> float:
        vals = [float(r.get(name, 0.0) or 0.0) for r in filtered]
        return round(sum(vals) / len(vals), 4)

    def total(name: str) -> float:
        vals = [float(r.get(name, 0.0) or 0.0) for r in filtered]
        return round(sum(vals), 2)

    return {
        "date": target_date,
        "store_id": store_id,
        "rows": len(filtered),
        "metrics": {
            "inventory_value_total": total("current_inventory_value"),
            "inventory_days_avg": avg("inventory_days"),
            "stock_turn_avg": avg("stock_turn_rate"),
            "expiry_exposure_total": total("expiry_wastage_exposure"),
            "reorder_risk_avg": avg("reorder_risk_index"),
            "service_risk_avg": avg("store_service_risk"),
            "schedule6_auditability_avg": avg("schedule6_dispensing_auditability"),
            "chronic_penetration_avg": avg("chronic_patient_basket_penetration"),
        },
    }


def get_inventory_health(
    mart_path: Path,
    date: str | None = None,
    store_id: str | None = None,
    limit: int = 200,
) -> dict[str, object]:
    rows = _read_rows(mart_path)
    target_date = date or _latest_by_date(rows, "date")

    filtered = [r for r in rows if (not target_date or r.get("date") == target_date)]
    if store_id:
        filtered = [r for r in filtered if r.get("store_id") == store_id]

    filtered.sort(key=lambda x: float(x.get("reorder_risk_index", 0.0) or 0.0), reverse=True)
    return {
        "date": target_date,
        "store_id": store_id,
        "rows": len(filtered),
        "items": filtered[: max(1, min(limit, 1000))],
    }


def get_forecast(
    forecast_path: Path,
    store_id: str | None = None,
    sku_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> dict[str, object]:
    rows = _read_rows(forecast_path)

    filtered = rows
    if store_id:
        filtered = [r for r in filtered if r.get("store_id") == store_id]
    if sku_id:
        filtered = [r for r in filtered if r.get("sku_id") == sku_id]
    if start_date:
        filtered = [r for r in filtered if r.get("forecast_date", "") >= start_date]
    if end_date:
        filtered = [r for r in filtered if r.get("forecast_date", "") <= end_date]

    filtered.sort(key=lambda x: (x.get("forecast_date", ""), x.get("store_id", ""), x.get("sku_id", "")))

    return {
        "rows": len(filtered),
        "items": filtered[: max(1, min(limit, 5000))],
    }
