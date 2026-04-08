"""Silver-layer transformations and validation checks."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class SilverBuildError(Exception):
    """Raised when Silver build or quality checks fail."""


@dataclass
class BuildArtifacts:
    dim_products_rows: int
    inventory_rows: int
    dispensing_rows: int
    sales_daily_rows: int
    quality_report_path: Path


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_csv(path: Path) -> csv.DictReader:
    f = path.open("r", encoding="utf-8", newline="")
    return csv.DictReader(f)


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> int:
    _ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return len(rows)


def build_dim_products_hc(raw_products_path: Path, silver_path: Path) -> int:
    if not raw_products_path.exists():
        raise SilverBuildError(f"Missing source dim products file: {raw_products_path}")

    reader = _read_csv(raw_products_path)
    rows: list[list[object]] = []
    for r in reader:
        rows.append(
            [
                r["sku_id"],
                r["category"],
                r["subcategory"],
                float(r["unit_cost"]),
                float(r["unit_price"]),
                int(r["shelf_life_days"]),
                int(r["is_controlled_substance"]),
                1 if r["category"] in {"chronic_rx", "acute_otc", "respiratory"} else 0,
                "pharmacy" if r["category"] in {"chronic_rx", "acute_otc", "respiratory"} else "front_shop",
            ]
        )

    headers = [
        "sku_id",
        "category",
        "subcategory",
        "unit_cost",
        "unit_price",
        "shelf_life_days",
        "is_controlled_substance",
        "is_healthcare_sku",
        "business_domain",
    ]
    return _write_csv(silver_path, headers, rows)


def build_fct_inventory_snapshots(bronze_sap_path: Path, silver_path: Path) -> tuple[int, float]:
    if not bronze_sap_path.exists():
        raise SilverBuildError(f"Missing SAP bronze file: {bronze_sap_path}")

    reader = _read_csv(bronze_sap_path)
    rows: list[list[object]] = []
    total_inventory_value = 0.0

    for r in reader:
        opening = int(r["opening_stock_units"])
        receipts = int(r["receipts_units"])
        closing = int(r["closing_stock_units"])
        unit_cost = float(r["unit_cost"])
        lead_time_days = int(r["lead_time_days"])

        if opening < 0 or receipts < 0 or closing < 0:
            raise SilverBuildError("Negative stock values detected in SAP source.")

        inventory_value = round(closing * unit_cost, 2)
        total_inventory_value += inventory_value

        safety_stock_flag = 1 if closing <= int(r["reorder_point_units"]) else 0

        rows.append(
            [
                r["snapshot_id"],
                r["date"],
                r["store_id"],
                r["sku_id"],
                opening,
                receipts,
                closing,
                int(r["reorder_point_units"]),
                lead_time_days,
                unit_cost,
                inventory_value,
                r["expiry_date"],
                int(r["is_controlled_substance"]),
                safety_stock_flag,
            ]
        )

    headers = [
        "snapshot_id",
        "date",
        "store_id",
        "sku_id",
        "opening_stock_units",
        "receipts_units",
        "closing_stock_units",
        "reorder_point_units",
        "lead_time_days",
        "unit_cost",
        "inventory_value",
        "expiry_date",
        "is_controlled_substance",
        "is_below_reorder_point",
    ]
    return _write_csv(silver_path, headers, rows), round(total_inventory_value, 2)


def build_fct_dispensing_log(bronze_clinic_path: Path, silver_path: Path) -> tuple[int, int]:
    if not bronze_clinic_path.exists():
        raise SilverBuildError(f"Missing clinic bronze file: {bronze_clinic_path}")

    reader = _read_csv(bronze_clinic_path)
    rows: list[list[object]] = []
    total_dispensed = 0

    for r in reader:
        qty = int(r["quantity_dispensed"])
        if qty < 1:
            raise SilverBuildError("Invalid clinic quantity_dispensed < 1 detected.")
        total_dispensed += qty

        rows.append(
            [
                r["script_line_id"],
                r["script_ts"],
                r["date"],
                r["clinic_id"],
                r["store_id"],
                r["patient_segment"],
                r["sku_id"],
                qty,
                r["diagnosis_group"],
                int(r["is_schedule_6"]),
                1 if r["patient_segment"] == "chronic" else 0,
            ]
        )

    headers = [
        "script_line_id",
        "script_ts",
        "date",
        "clinic_id",
        "store_id",
        "patient_segment",
        "sku_id",
        "quantity_dispensed",
        "diagnosis_group",
        "is_schedule_6",
        "is_chronic_patient",
    ]
    return _write_csv(silver_path, headers, rows), total_dispensed


def build_fct_sales_daily(bronze_pos_path: Path, silver_path: Path) -> tuple[int, int, float]:
    if not bronze_pos_path.exists():
        raise SilverBuildError(f"Missing POS bronze file: {bronze_pos_path}")

    reader = _read_csv(bronze_pos_path)
    grouped: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(lambda: {
        "tx_count": 0,
        "units": 0,
        "gross_sales": 0.0,
        "discount": 0.0,
        "net_sales": 0.0,
    })

    source_units_total = 0
    source_net_sales_total = 0.0

    for r in reader:
        qty = int(r["quantity"])
        unit_price = float(r["unit_price"])
        discount_amount = float(r["discount_amount"])
        net_sales = float(r["net_sales_amount"])

        key = (r["date"], r["store_id"], r["sku_id"], r["channel"])
        g = grouped[key]
        g["tx_count"] += 1
        g["units"] += qty
        g["gross_sales"] += round(unit_price * qty, 2)
        g["discount"] += round(discount_amount * qty, 2)
        g["net_sales"] += net_sales

        source_units_total += qty
        source_net_sales_total += net_sales

    rows: list[list[object]] = []
    for (day, store_id, sku_id, channel), g in grouped.items():
        rows.append(
            [
                day,
                store_id,
                sku_id,
                channel,
                int(g["tx_count"]),
                int(g["units"]),
                round(g["gross_sales"], 2),
                round(g["discount"], 2),
                round(g["net_sales"], 2),
            ]
        )

    headers = [
        "date",
        "store_id",
        "sku_id",
        "channel",
        "transactions_count",
        "units_sold",
        "gross_sales_amount",
        "discount_amount",
        "net_sales_amount",
    ]
    return _write_csv(silver_path, headers, rows), source_units_total, round(source_net_sales_total, 2)


def build_silver_layer(
    raw_products_path: Path,
    bronze_pos_path: Path,
    bronze_sap_path: Path,
    bronze_clinic_path: Path,
    silver_dir: Path,
) -> BuildArtifacts:
    silver_dir.mkdir(parents=True, exist_ok=True)

    dim_products_rows = build_dim_products_hc(raw_products_path, silver_dir / "dim_products_hc.csv")
    inventory_rows, total_inventory_value = build_fct_inventory_snapshots(
        bronze_sap_path, silver_dir / "fct_inventory_snapshots.csv"
    )
    dispensing_rows, total_dispensed = build_fct_dispensing_log(
        bronze_clinic_path, silver_dir / "fct_dispensing_log.csv"
    )
    sales_daily_rows, source_pos_units, source_pos_net_sales = build_fct_sales_daily(
        bronze_pos_path, silver_dir / "fct_sales_daily.csv"
    )

    # Reconciliation checks.
    agg_sales_units = 0
    agg_sales_net = 0.0
    with (silver_dir / "fct_sales_daily.csv").open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            agg_sales_units += int(row["units_sold"])
            agg_sales_net += float(row["net_sales_amount"])

    if agg_sales_units != source_pos_units:
        raise SilverBuildError(
            f"Reconciliation failed for POS units: source={source_pos_units}, silver={agg_sales_units}"
        )

    if round(agg_sales_net, 2) != round(source_pos_net_sales, 2):
        raise SilverBuildError(
            f"Reconciliation failed for POS net sales: source={source_pos_net_sales}, silver={round(agg_sales_net, 2)}"
        )

    quality_report_path = silver_dir / "_quality_report.json"
    quality_report = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "checks": {
            "pos_reconciliation_units": "passed",
            "pos_reconciliation_net_sales": "passed",
            "clinic_dispensing_non_negative": "passed",
            "sap_inventory_non_negative": "passed",
        },
        "metrics": {
            "dim_products_rows": dim_products_rows,
            "inventory_rows": inventory_rows,
            "dispensing_rows": dispensing_rows,
            "sales_daily_rows": sales_daily_rows,
            "total_inventory_value": total_inventory_value,
            "total_dispensed_units": total_dispensed,
            "source_pos_units": source_pos_units,
            "source_pos_net_sales": source_pos_net_sales,
        },
    }

    with quality_report_path.open("w", encoding="utf-8") as f:
        json.dump(quality_report, f, indent=2)

    return BuildArtifacts(
        dim_products_rows=dim_products_rows,
        inventory_rows=inventory_rows,
        dispensing_rows=dispensing_rows,
        sales_daily_rows=sales_daily_rows,
        quality_report_path=quality_report_path,
    )
