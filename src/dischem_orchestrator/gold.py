"""Gold-layer marts and KPI computation."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path


class GoldBuildError(Exception):
    """Raised when Gold marts fail validation."""


@dataclass
class GoldArtifacts:
    inventory_health_rows: int
    financial_rows: int
    customer_rows: int
    kpi_rows: int
    quality_report_path: Path


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_csv(path: Path) -> csv.DictReader:
    f = path.open("r", encoding="utf-8", newline="")
    return csv.DictReader(f)


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> int:
    _ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    return len(rows)


def _to_date(v: str) -> date:
    return date.fromisoformat(v)


def build_gold_layer(silver_dir: Path, gold_dir: Path) -> GoldArtifacts:
    required = [
        silver_dir / "dim_products_hc.csv",
        silver_dir / "fct_inventory_snapshots.csv",
        silver_dir / "fct_dispensing_log.csv",
        silver_dir / "fct_sales_daily.csv",
    ]
    for p in required:
        if not p.exists():
            raise GoldBuildError(f"Missing Silver input: {p}")

    gold_dir.mkdir(parents=True, exist_ok=True)

    dim_map: dict[str, dict[str, object]] = {}
    with (silver_dir / "dim_products_hc.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            dim_map[r["sku_id"]] = {
                "unit_cost": float(r["unit_cost"]),
                "is_healthcare_sku": int(r["is_healthcare_sku"]),
                "is_controlled_substance": int(r["is_controlled_substance"]),
            }

    sales_store_day = defaultdict(lambda: {"units": 0, "net_sales": 0.0, "online_units": 0, "clinic_pickup_units": 0, "healthcare_units": 0})
    sales_store_month = defaultdict(lambda: {"units": 0, "net_sales": 0.0, "cogs": 0.0})

    with (silver_dir / "fct_sales_daily.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            d = r["date"]
            month = d[:7]
            store = r["store_id"]
            sku = r["sku_id"]
            channel = r["channel"]
            units = int(r["units_sold"])
            net_sales = float(r["net_sales_amount"])

            key_sd = (d, store)
            sd = sales_store_day[key_sd]
            sd["units"] += units
            sd["net_sales"] += net_sales
            if channel == "online":
                sd["online_units"] += units
            if channel == "clinic_pickup":
                sd["clinic_pickup_units"] += units
            if dim_map.get(sku, {}).get("is_healthcare_sku", 0) == 1:
                sd["healthcare_units"] += units

            key_sm = (month, store)
            sm = sales_store_month[key_sm]
            sm["units"] += units
            sm["net_sales"] += net_sales
            sm["cogs"] += units * dim_map.get(sku, {}).get("unit_cost", 0.0)

    dispensing_store_day = defaultdict(lambda: {"dispensed_units": 0, "schedule6_units": 0, "script_ids": set()})
    with (silver_dir / "fct_dispensing_log.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["date"], r["store_id"])
            qty = int(r["quantity_dispensed"])
            dispensing_store_day[key]["dispensed_units"] += qty
            if int(r["is_schedule_6"]) == 1:
                dispensing_store_day[key]["schedule6_units"] += qty
            dispensing_store_day[key]["script_ids"].add(r["script_line_id"])

    inv_store_day = defaultdict(
        lambda: {
            "inventory_value": 0.0,
            "closing_units": 0,
            "below_reorder": 0,
            "rows": 0,
            "lead_time_sum": 0,
            "expiry_exposure_90d": 0.0,
            "schedule6_units": 0,
            "chronic_breach_rows": 0,
        }
    )
    inv_store_month = defaultdict(lambda: {"inventory_value_sum": 0.0, "days": set(), "expiry_exposure": 0.0})

    with (silver_dir / "fct_inventory_snapshots.csv").open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            d = r["date"]
            store = r["store_id"]
            sku = r["sku_id"]
            month = d[:7]
            key_sd = (d, store)
            key_sm = (month, store)

            closing = int(r["closing_stock_units"])
            inv_val = float(r["inventory_value"])
            below = int(r["is_below_reorder_point"])
            lead_time = int(r["lead_time_days"])
            reorder = int(r["reorder_point_units"])

            sd = inv_store_day[key_sd]
            sd["inventory_value"] += inv_val
            sd["closing_units"] += closing
            sd["below_reorder"] += below
            sd["rows"] += 1
            sd["lead_time_sum"] += lead_time
            if int(r["is_controlled_substance"]) == 1:
                sd["schedule6_units"] += closing
            if dim_map.get(sku, {}).get("is_healthcare_sku", 0) == 1 and closing <= reorder:
                sd["chronic_breach_rows"] += 1

            exp_date = _to_date(r["expiry_date"])
            current = _to_date(d)
            if exp_date <= (current + timedelta(days=90)):
                sd["expiry_exposure_90d"] += inv_val

            sm = inv_store_month[key_sm]
            sm["inventory_value_sum"] += inv_val
            sm["days"].add(d)
            sm["expiry_exposure"] += sd["expiry_exposure_90d"] * 0.0  # retained for shape; daily used below

    # Build mart_inventory_health
    inventory_rows: list[list[object]] = []
    kpi_rows: list[list[object]] = []
    for (d, store), m in sorted(inv_store_day.items()):
        sales_units = sales_store_day[(d, store)]["units"]
        below_rate = (m["below_reorder"] / m["rows"]) if m["rows"] else 0.0
        avg_lead_norm = min((m["lead_time_sum"] / max(m["rows"] * 14, 1)), 1.0)
        demand_spike = min((sales_units / max((m["closing_units"] + 1), 1)), 1.0)
        reorder_risk = round(0.5 * below_rate + 0.3 * avg_lead_norm + 0.2 * demand_spike, 4)

        chronic_breach = (m["chronic_breach_rows"] / m["rows"]) if m["rows"] else 0.0
        sched6_risk = min(m["schedule6_units"] / max(m["closing_units"], 1), 1.0)
        service_risk = round(0.5 * below_rate + 0.3 * chronic_breach + 0.2 * sched6_risk, 4)

        stock_cover_days = round(m["closing_units"] / max(sales_units, 1), 2)
        expiry_exposure = round(m["expiry_exposure_90d"], 2)

        inventory_rows.append(
            [
                d,
                store,
                round(m["inventory_value"], 2),
                round(below_rate, 4),
                stock_cover_days,
                reorder_risk,
                service_risk,
                expiry_exposure,
                m["schedule6_units"],
            ]
        )

        month = d[:7]
        month_inv = inv_store_month[(month, store)]
        avg_inventory_value_month = month_inv["inventory_value_sum"] / max(len(month_inv["days"]), 1)
        sm = sales_store_month[(month, store)]
        stock_turn = round(sm["cogs"] / max(avg_inventory_value_month, 1.0), 4)
        inventory_days = round(avg_inventory_value_month / max(sm["cogs"] / max(len(month_inv["days"]), 1), 1.0), 2)

        disp = dispensing_store_day[(d, store)]
        disp_units = disp["dispensed_units"]
        total_units = sales_units
        chronic_pen = round(disp_units / max(total_units, 1), 4)
        auditability = 1.0 if disp["schedule6_units"] == 0 or len(disp["script_ids"]) > 0 else 0.0

        kpi_rows.append(
            [
                d,
                store,
                round(m["inventory_value"], 2),
                inventory_days,
                stock_turn,
                expiry_exposure,
                auditability,
                chronic_pen,
                reorder_risk,
                service_risk,
            ]
        )

    inventory_headers = [
        "date",
        "store_id",
        "inventory_value",
        "below_reorder_rate",
        "stock_cover_days",
        "reorder_risk_index",
        "store_service_risk",
        "expiry_wastage_exposure",
        "schedule6_inventory_units",
    ]
    inventory_health_rows = _write_csv(gold_dir / "mart_inventory_health.csv", inventory_headers, inventory_rows)

    # Build mart_financial_performance
    baseline_by_store: dict[str, float] = {}
    month_store_avg_inv: dict[tuple[str, str], float] = {}
    for (month, store), m in inv_store_month.items():
        avg_inv = m["inventory_value_sum"] / max(len(m["days"]), 1)
        month_store_avg_inv[(month, store)] = avg_inv

    if month_store_avg_inv:
        first_month = sorted({m for (m, _) in month_store_avg_inv.keys()})[0]
        for (month, store), avg_inv in month_store_avg_inv.items():
            if month == first_month:
                baseline_by_store[store] = avg_inv

    fin_rows: list[list[object]] = []
    for (month, store), sm in sorted(sales_store_month.items()):
        avg_inv = month_store_avg_inv.get((month, store), 0.0)
        days_in_month = len(inv_store_month[(month, store)]["days"]) if (month, store) in inv_store_month else 30
        cogs = sm["cogs"]
        stock_turn = round(cogs / max(avg_inv, 1.0), 4)
        inventory_days = round(avg_inv / max(cogs / max(days_in_month, 1), 1.0), 2)
        baseline = baseline_by_store.get(store, avg_inv)
        working_cap_unlocked = round(max(0.0, baseline - avg_inv), 2)

        # Approximate expiry exposure by summing daily exposure from inventory mart in same month.
        expiry_sum = 0.0
        for r in inventory_rows:
            if r[0].startswith(month) and r[1] == store:
                expiry_sum += float(r[7])

        fin_rows.append(
            [
                month,
                store,
                round(sm["net_sales"], 2),
                round(cogs, 2),
                round(avg_inv, 2),
                stock_turn,
                inventory_days,
                working_cap_unlocked,
                round(expiry_sum, 2),
            ]
        )

    fin_headers = [
        "month",
        "store_id",
        "net_sales_amount",
        "cogs_estimate",
        "avg_inventory_value",
        "stock_turn_rate",
        "inventory_days",
        "working_capital_unlocked",
        "expiry_wastage_exposure",
    ]
    financial_rows = _write_csv(gold_dir / "mart_financial_performance.csv", fin_headers, fin_rows)

    # Build mart_customer_behavior
    cust_rows: list[list[object]] = []
    for (d, store), s in sorted(sales_store_day.items()):
        disp = dispensing_store_day[(d, store)]
        total_units = s["units"]
        chronic_dispensed = disp["dispensed_units"]
        chronic_pen = round(chronic_dispensed / max(total_units, 1), 4)
        clinic_share = round(s["clinic_pickup_units"] / max(total_units, 1), 4)
        online_share = round(s["online_units"] / max(total_units, 1), 4)
        healthcare_share = round(s["healthcare_units"] / max(total_units, 1), 4)

        cust_rows.append(
            [
                d,
                store,
                total_units,
                chronic_dispensed,
                chronic_pen,
                clinic_share,
                online_share,
                healthcare_share,
            ]
        )

    cust_headers = [
        "date",
        "store_id",
        "total_units_sold",
        "chronic_dispensed_units",
        "chronic_patient_basket_penetration",
        "clinic_share_of_units",
        "online_channel_share",
        "healthcare_sku_share",
    ]
    customer_rows = _write_csv(gold_dir / "mart_customer_behavior.csv", cust_headers, cust_rows)

    kpi_headers = [
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
    ]
    kpi_count = _write_csv(gold_dir / "kpi_summary.csv", kpi_headers, kpi_rows)

    report = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "checks": {
            "inventory_health_not_empty": "passed" if inventory_health_rows > 0 else "failed",
            "financial_mart_not_empty": "passed" if financial_rows > 0 else "failed",
            "customer_mart_not_empty": "passed" if customer_rows > 0 else "failed",
            "kpi_summary_not_empty": "passed" if kpi_count > 0 else "failed",
        },
        "metrics": {
            "inventory_health_rows": inventory_health_rows,
            "financial_rows": financial_rows,
            "customer_rows": customer_rows,
            "kpi_rows": kpi_count,
        },
    }

    quality_report_path = gold_dir / "_quality_report.json"
    with quality_report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return GoldArtifacts(
        inventory_health_rows=inventory_health_rows,
        financial_rows=financial_rows,
        customer_rows=customer_rows,
        kpi_rows=kpi_count,
        quality_report_path=quality_report_path,
    )
