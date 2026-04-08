"""Shared contract definitions for stage-2 ingestion."""

from __future__ import annotations

CONTRACTS: dict[str, dict[str, object]] = {
    "pos_transactions_raw": {
        "required_columns": [
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
        "date_column": "date",
    },
    "sap_inventory_levels_raw": {
        "required_columns": [
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
        "date_column": "date",
    },
    "clinic_scripts_raw": {
        "required_columns": [
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
        "date_column": "date",
    },
}
