"""Governed inventory explanation agent."""

from __future__ import annotations

import csv
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class AgentError(Exception):
    """Raised when agent inputs are missing or invalid."""


@dataclass
class AgentResponse:
    run_id: str
    date: str
    store_id: str
    sku_id: str | None
    summary: str
    risk_level: str
    key_drivers: list[str]
    recommended_actions: list[str]
    confidence: float
    signals: dict[str, float]
    policy_version: str
    prompt_version: str

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "date": self.date,
            "store_id": self.store_id,
            "sku_id": self.sku_id,
            "summary": self.summary,
            "risk_level": self.risk_level,
            "key_drivers": self.key_drivers,
            "recommended_actions": self.recommended_actions,
            "confidence": self.confidence,
            "signals": self.signals,
            "policy_version": self.policy_version,
            "prompt_version": self.prompt_version,
        }


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise AgentError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_kpi_row(kpi_path: Path, day: str, store_id: str) -> dict[str, str]:
    if not kpi_path.exists():
        raise AgentError(f"Missing KPI dataset: {kpi_path}")
    with kpi_path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["date"] == day and r["store_id"] == store_id:
                return r
    raise AgentError(f"No KPI row found for date={day}, store_id={store_id}")


def _load_alert_rows(alerts_path: Path, day: str, store_id: str, sku_id: str | None, max_rows: int) -> list[dict[str, str]]:
    if not alerts_path.exists():
        raise AgentError(f"Missing alerts dataset: {alerts_path}")

    rows: list[dict[str, str]] = []
    with alerts_path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["date"] != day or r["store_id"] != store_id:
                continue
            if sku_id and r["sku_id"] != sku_id:
                continue
            rows.append(r)

    sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    rows.sort(key=lambda x: (sev_order.get(x["severity"], 0), float(x["composite_risk_score"])), reverse=True)
    return rows[:max_rows]


def _forecast_signal(forecast_path: Path, store_id: str, sku_id: str | None) -> float:
    if not forecast_path.exists():
        raise AgentError(f"Missing forecast dataset: {forecast_path}")

    vals = []
    with forecast_path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["store_id"] != store_id:
                continue
            if sku_id and r["sku_id"] != sku_id:
                continue
            vals.append(float(r["predicted_units"]))

    if not vals:
        return 0.0

    avg = sum(vals) / len(vals)
    return min(1.0, avg / 10.0)


def _risk_level(score: float, thresholds: dict[str, float]) -> str:
    if score >= thresholds.get("high", 0.85):
        return "high"
    if score >= thresholds.get("medium", 0.65):
        return "medium"
    return "low"


def _build_actions(alerts: list[dict[str, str]], kpi: dict[str, str], max_actions: int) -> list[str]:
    actions = []
    for a in alerts:
        rec = a.get("recommended_action")
        if rec and rec not in actions:
            actions.append(rec)

    reorder = float(kpi.get("reorder_risk_index", 0.0))
    service = float(kpi.get("store_service_risk", 0.0))

    if reorder > 0.6 and len(actions) < max_actions:
        actions.append("Increase safety stock for top at-risk SKUs and re-check lead time assumptions.")
    if service > 0.6 and len(actions) < max_actions:
        actions.append("Escalate store-level service risk to operations and monitor hourly until stabilized.")

    if not actions:
        actions.append("Continue monitoring; no immediate intervention required.")

    return actions[:max_actions]


def _build_summary(store_id: str, day: str, risk: str, alert_count: int, reorder: float, service: float) -> str:
    return (
        f"Store {store_id} on {day} shows {risk} inventory risk with {alert_count} active alert(s). "
        f"Reorder risk={reorder:.2f}, service risk={service:.2f}."
    )


def _append_audit_log(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def explain_inventory_exception(
    *,
    day: str,
    store_id: str,
    sku_id: str | None,
    kpi_path: Path,
    alerts_path: Path,
    forecast_path: Path,
    policy_path: Path,
    prompt_path: Path,
    audit_log_path: Path,
) -> AgentResponse:
    policy = _read_json(policy_path)
    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

    guardrails = policy.get("guardrails", {})
    thresholds = guardrails.get("risk_thresholds", {"medium": 0.65, "high": 0.85})
    max_alerts = int(guardrails.get("max_alerts_in_context", 5))
    max_actions = int(guardrails.get("max_recommendations", 3))

    kpi = _load_kpi_row(kpi_path, day, store_id)
    alerts = _load_alert_rows(alerts_path, day, store_id, sku_id, max_alerts)
    forecast_signal = _forecast_signal(forecast_path, store_id, sku_id)

    reorder = float(kpi.get("reorder_risk_index", 0.0))
    service = float(kpi.get("store_service_risk", 0.0))
    expiry = min(float(kpi.get("expiry_wastage_exposure", 0.0)) / 50000.0, 1.0)

    top_alert = max((float(a.get("composite_risk_score", 0.0)) for a in alerts), default=0.0)
    composite = round((0.4 * reorder) + (0.3 * service) + (0.2 * top_alert) + (0.1 * forecast_signal) + (0.05 * expiry), 4)
    risk = _risk_level(composite, thresholds)

    drivers = []
    if reorder >= 0.45:
        drivers.append(f"Elevated reorder risk index ({reorder:.2f})")
    if service >= 0.45:
        drivers.append(f"Elevated store service risk ({service:.2f})")
    if top_alert >= 0.45:
        drivers.append(f"High-priority alert pressure ({top_alert:.2f})")
    if forecast_signal >= 0.45:
        drivers.append(f"Demand pressure from forecast ({forecast_signal:.2f})")
    if not drivers:
        drivers.append("No strong negative signal; risk mostly routine.")

    actions = _build_actions(alerts, kpi, max_actions)

    conf = 0.55 + (0.25 if alerts else 0.0) + (0.15 if reorder >= 0.45 or service >= 0.45 else 0.0)
    confidence = round(min(conf, 0.95), 2)

    run_id = f"ag_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"

    response = AgentResponse(
        run_id=run_id,
        date=day,
        store_id=store_id,
        sku_id=sku_id,
        summary=_build_summary(store_id, day, risk, len(alerts), reorder, service),
        risk_level=risk,
        key_drivers=drivers,
        recommended_actions=actions,
        confidence=confidence,
        signals={
            "reorder_risk_index": round(reorder, 4),
            "store_service_risk": round(service, 4),
            "top_alert_risk": round(top_alert, 4),
            "forecast_signal": round(forecast_signal, 4),
            "expiry_signal": round(expiry, 4),
            "composite_risk": composite,
        },
        policy_version=str(policy.get("version", "unknown")),
        prompt_version="inventory_agent_prompt_v1" if prompt_text else "missing_prompt",
    )

    audit_payload = {
        "logged_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "request": {"date": day, "store_id": store_id, "sku_id": sku_id},
        "response": response.as_dict(),
        "context": {
            "alerts_in_context": len(alerts),
            "prompt_hash": hash(prompt_text),
            "policy_file": str(policy_path),
        },
    }
    _append_audit_log(audit_log_path, audit_payload)

    return response
