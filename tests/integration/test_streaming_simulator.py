from __future__ import annotations

import csv
import json
from pathlib import Path

from dischem_orchestrator.streaming import build_streaming_alerts


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def test_streaming_simulator_builds_alerts(tmp_path: Path) -> None:
    events = tmp_path / "events.csv"
    kpi = tmp_path / "kpi.csv"
    forecast = tmp_path / "forecast.csv"
    output = tmp_path / "alerts.csv"
    report = tmp_path / "alerts_quality.json"

    _write_csv(
        events,
        ["event_id", "event_ts", "date", "store_id", "sku_id", "event_type", "delta_units", "resulting_stock_units", "risk_score"],
        [["EV0001", "2025-01-01T10:00:00", "2025-01-01", "ST001", "SKU1", "stockout_risk", -4, 2, 0.9]],
    )

    _write_csv(
        kpi,
        [
            "date",
            "store_id",
            "current_inventory_value",
            "inventory_days",
            "stock_turn_rate",
            "expiry_wastage_exposure",
            "schedule6_dispensing_auditability",
            "chronic_patient_basket_penetration",
            "reorder_risk_index",
            "store_service_risk",
        ],
        [["2025-01-01", "ST001", 1000, 10, 2, 100, 1, 0.1, 0.8, 0.7]],
    )

    _write_csv(
        forecast,
        ["forecast_date", "store_id", "sku_id", "predicted_units", "model_version", "run_id"],
        [["2025-01-02", "ST001", "SKU1", 12.0, "baseline", "run1"]],
    )

    artifacts = build_streaming_alerts(events, kpi, forecast, output, report)
    assert artifacts.alert_rows == 1

    quality = json.loads(report.read_text(encoding="utf-8"))
    assert quality["checks"]["alerts_not_empty"] == "passed"
