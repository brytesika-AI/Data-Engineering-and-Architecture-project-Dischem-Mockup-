"""Streaming simulator and alert generation for inventory events."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


class StreamingError(Exception):
    """Raised when streaming simulation fails."""


@dataclass
class StreamingArtifacts:
    alert_rows: int
    quality_report_path: Path
    output_path: Path


def _read_csv(path: Path) -> csv.DictReader:
    f = path.open("r", encoding="utf-8", newline="")
    return csv.DictReader(f)


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return len(rows)


def _safe_float(v: str | None, default: float = 0.0) -> float:
    if v in (None, ""):
        return default
    return float(v)


def _lag_seconds(event_id: str) -> int:
    digest = hashlib.md5(event_id.encode("utf-8")).hexdigest()  # deterministic for reproducibility
    return (int(digest[:6], 16) % 120) + 5


def _severity(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _recommendation(event_type: str) -> str:
    if event_type == "stockout_risk":
        return "Expedite replenishment and rebalance stock from nearest low-risk store."
    if event_type == "overstock_risk":
        return "Throttle reorder quantity and trigger promo markdown review."
    if event_type == "expiry_risk":
        return "Prioritize FEFO transfer and targeted sell-through campaign."
    if event_type == "reorder_trigger":
        return "Validate lead time and approve automated replenishment run."
    return "Review inventory adjustment and confirm root-cause classification."


def build_streaming_alerts(
    events_path: Path,
    kpi_summary_path: Path,
    forecast_path: Path,
    output_path: Path,
    quality_report_path: Path,
) -> StreamingArtifacts:
    if not events_path.exists():
        raise StreamingError(f"Missing events source: {events_path}")
    if not kpi_summary_path.exists():
        raise StreamingError(f"Missing KPI source: {kpi_summary_path}")
    if not forecast_path.exists():
        raise StreamingError(f"Missing forecast source: {forecast_path}")

    # KPI context by (date, store).
    kpi_by_day_store: dict[tuple[str, str], dict[str, float]] = {}
    with kpi_summary_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            kpi_by_day_store[(r["date"], r["store_id"])] = {
                "reorder_risk_index": _safe_float(r.get("reorder_risk_index")),
                "store_service_risk": _safe_float(r.get("store_service_risk")),
                "expiry_wastage_exposure": _safe_float(r.get("expiry_wastage_exposure")),
            }

    # Forecast pressure by (store, sku): mean predicted units.
    forecast_agg: dict[tuple[str, str], tuple[float, int]] = {}
    with forecast_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = (r["store_id"], r["sku_id"])
            total, n = forecast_agg.get(key, (0.0, 0))
            forecast_agg[key] = (total + _safe_float(r.get("predicted_units")), n + 1)

    forecast_avg = {k: (v[0] / v[1]) for k, v in forecast_agg.items() if v[1] > 0}

    alert_rows: list[list[object]] = []
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_lag = 0

    with events_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            event_id = r["event_id"]
            event_ts = datetime.fromisoformat(r["event_ts"])
            day = r["date"]
            store = r["store_id"]
            sku = r["sku_id"]
            event_type = r["event_type"]
            resulting_stock = max(0.0, _safe_float(r.get("resulting_stock_units"), 0.0))
            base_risk = _safe_float(r.get("risk_score"), 0.0)

            kpi = kpi_by_day_store.get((day, store), {})
            reorder = kpi.get("reorder_risk_index", 0.0)
            service = kpi.get("store_service_risk", 0.0)
            expiry = min(kpi.get("expiry_wastage_exposure", 0.0) / 50000.0, 1.0)
            kpi_signal = min(1.0, (0.5 * reorder) + (0.3 * service) + (0.2 * expiry))

            f_units = forecast_avg.get((store, sku), 0.0)
            forecast_signal = min(1.0, f_units / max(resulting_stock, 1.0))

            score = (0.5 * base_risk) + (0.3 * kpi_signal) + (0.2 * forecast_signal)
            if event_type == "reorder_trigger":
                score = max(0.0, score - 0.15)
            if event_type == "stockout_risk":
                score = min(1.0, score + 0.15)
            if event_type == "expiry_risk":
                score = min(1.0, score + 0.10)

            score = round(score, 4)
            sev = _severity(score)
            sev_counts[sev] += 1

            lag = _lag_seconds(event_id)
            total_lag += lag
            emitted_ts = event_ts + timedelta(seconds=lag)

            alert_rows.append(
                [
                    f"AL{event_id[2:]}",
                    event_id,
                    event_type,
                    day,
                    store,
                    sku,
                    round(base_risk, 4),
                    round(kpi_signal, 4),
                    round(forecast_signal, 4),
                    score,
                    sev,
                    _recommendation(event_type),
                    event_ts.isoformat(),
                    emitted_ts.isoformat(),
                    lag,
                ]
            )

    headers = [
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
    ]
    row_count = _write_csv(output_path, headers, alert_rows)

    report = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "metrics": {
            "alerts_generated": row_count,
            "avg_event_to_alert_lag_seconds": round(total_lag / max(row_count, 1), 2),
            "severity_counts": sev_counts,
        },
        "checks": {
            "alerts_not_empty": "passed" if row_count > 0 else "failed",
            "severity_distribution_present": "passed" if any(v > 0 for v in sev_counts.values()) else "failed",
        },
    }

    quality_report_path.parent.mkdir(parents=True, exist_ok=True)
    with quality_report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return StreamingArtifacts(alert_rows=row_count, quality_report_path=quality_report_path, output_path=output_path)
