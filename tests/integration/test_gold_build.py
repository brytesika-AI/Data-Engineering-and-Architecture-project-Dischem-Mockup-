from __future__ import annotations

import csv
import json
from pathlib import Path

from dischem_orchestrator.gold import build_gold_layer


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def test_build_gold_layer_outputs(tmp_path: Path) -> None:
    silver = tmp_path / "silver"
    gold = tmp_path / "gold"

    _write_csv(
        silver / "dim_products_hc.csv",
        [
            "sku_id",
            "category",
            "subcategory",
            "unit_cost",
            "unit_price",
            "shelf_life_days",
            "is_controlled_substance",
            "is_healthcare_sku",
            "business_domain",
        ],
        [["SKU1", "chronic_rx", "chronic", 20.0, 35.0, 180, 1, 1, "pharmacy"]],
    )

    _write_csv(
        silver / "fct_inventory_snapshots.csv",
        [
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
        ],
        [["SN1", "2025-01-01", "ST001", "SKU1", 10, 0, 8, 8, 3, 20.0, 160.0, "2025-03-01", 1, 1]],
    )

    _write_csv(
        silver / "fct_sales_daily.csv",
        [
            "date",
            "store_id",
            "sku_id",
            "channel",
            "transactions_count",
            "units_sold",
            "gross_sales_amount",
            "discount_amount",
            "net_sales_amount",
        ],
        [["2025-01-01", "ST001", "SKU1", "store", 1, 2, 70.0, 0.0, 70.0]],
    )

    _write_csv(
        silver / "fct_dispensing_log.csv",
        [
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
        ],
        [["SC1", "2025-01-01T10:00:00", "2025-01-01", "CL001", "ST001", "chronic", "SKU1", 1, "chronic_care", 1, 1]],
    )

    artifacts = build_gold_layer(silver, gold)

    assert artifacts.inventory_health_rows == 1
    assert artifacts.financial_rows == 1
    assert artifacts.customer_rows == 1
    assert artifacts.kpi_rows == 1

    report = json.loads((gold / "_quality_report.json").read_text(encoding="utf-8"))
    assert report["checks"]["kpi_summary_not_empty"] == "passed"
