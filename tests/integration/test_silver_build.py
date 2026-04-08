from __future__ import annotations

import csv
import json
from pathlib import Path

from dischem_orchestrator.silver import build_silver_layer


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def test_build_silver_layer_creates_expected_outputs(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    bronze = tmp_path / "bronze"
    silver = tmp_path / "silver"

    _write_csv(
        raw / "dim_products.csv",
        ["sku_id", "category", "subcategory", "unit_cost", "unit_price", "shelf_life_days", "is_controlled_substance"],
        [["SKU1", "chronic_rx", "chronic", 20.0, 35.0, 180, 1]],
    )

    _write_csv(
        bronze / "pos_transactions_raw.csv",
        [
            "transaction_line_id",
            "transaction_ts",
            "date",
            "store_id",
            "sku_id",
            "quantity",
            "unit_price",
            "discount_amount",
            "net_sales_amount",
            "channel",
            "payment_type",
        ],
        [
            ["TX1", "2025-01-01T10:00:00", "2025-01-01", "ST001", "SKU1", 2, 35.0, 0.0, 70.0, "store", "card"],
            ["TX2", "2025-01-01T11:00:00", "2025-01-01", "ST001", "SKU1", 1, 35.0, 0.0, 35.0, "store", "card"],
        ],
    )

    _write_csv(
        bronze / "sap_inventory_levels_raw.csv",
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
            "expiry_date",
            "is_controlled_substance",
        ],
        [["SN1", "2025-01-01", "ST001", "SKU1", 10, 5, 12, 8, 3, 20.0, "2025-06-30", 1]],
    )

    _write_csv(
        bronze / "clinic_scripts_raw.csv",
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
        ],
        [["SC1", "2025-01-01T12:00:00", "2025-01-01", "CL001", "ST001", "chronic", "SKU1", 1, "chronic_care", 1]],
    )

    artifacts = build_silver_layer(
        raw_products_path=raw / "dim_products.csv",
        bronze_pos_path=bronze / "pos_transactions_raw.csv",
        bronze_sap_path=bronze / "sap_inventory_levels_raw.csv",
        bronze_clinic_path=bronze / "clinic_scripts_raw.csv",
        silver_dir=silver,
    )

    assert artifacts.dim_products_rows == 1
    assert artifacts.inventory_rows == 1
    assert artifacts.dispensing_rows == 1
    assert artifacts.sales_daily_rows == 1

    report = json.loads((silver / "_quality_report.json").read_text(encoding="utf-8"))
    assert report["checks"]["pos_reconciliation_units"] == "passed"
    assert report["checks"]["pos_reconciliation_net_sales"] == "passed"
