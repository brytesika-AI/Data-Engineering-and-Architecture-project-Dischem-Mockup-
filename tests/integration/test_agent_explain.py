from __future__ import annotations

import csv
import json
from pathlib import Path

from dischem_orchestrator.agent import explain_inventory_exception


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def test_agent_explain_logs_and_returns_response(tmp_path: Path) -> None:
    kpi = tmp_path / "kpi.csv"
    alerts = tmp_path / "alerts.csv"
    forecast = tmp_path / "forecast.csv"
    policy = tmp_path / "policy.json"
    prompt = tmp_path / "prompt.txt"
    audit = tmp_path / "audit.jsonl"

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
        [["2025-01-01", "ST001", 1000, 10, 2, 0, 1, 0.1, 0.7, 0.6]],
    )

    _write_csv(
        alerts,
        [
            "alert_id",
            "event_id",
            "event_type",
            "date",
            "store_id",
            "sku_id",
            "event_risk",
            "kpi_signal",
            "forecast_signal",
            "composite_risk_score",
            "severity",
            "recommended_action",
            "event_ts",
            "emitted_ts",
            "event_to_alert_lag_seconds",
        ],
        [["AL1", "EV1", "stockout_risk", "2025-01-01", "ST001", "SKU1", 0.9, 0.8, 0.7, 0.88, "high", "Action", "2025-01-01T10:00:00", "2025-01-01T10:00:30", 30]],
    )

    _write_csv(
        forecast,
        ["forecast_date", "store_id", "sku_id", "predicted_units", "model_version", "run_id"],
        [["2025-01-02", "ST001", "SKU1", 10, "m1", "r1"]],
    )

    policy.write_text(
        json.dumps(
            {
                "version": "1",
                "guardrails": {
                    "max_alerts_in_context": 5,
                    "max_recommendations": 3,
                    "risk_thresholds": {"medium": 0.65, "high": 0.85},
                },
            }
        ),
        encoding="utf-8",
    )
    prompt.write_text("prompt", encoding="utf-8")

    resp = explain_inventory_exception(
        day="2025-01-01",
        store_id="ST001",
        sku_id="SKU1",
        kpi_path=kpi,
        alerts_path=alerts,
        forecast_path=forecast,
        policy_path=policy,
        prompt_path=prompt,
        audit_log_path=audit,
    )

    assert resp.risk_level in {"low", "medium", "high"}
    assert resp.recommended_actions
    assert audit.exists()
