from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from dischem_orchestrator.ingestion import IngestionError, ingest_dataset


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def _pos_headers() -> list[str]:
    return [
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
    ]


def test_ingestion_is_idempotent_on_unchanged_input(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "pos_transactions_raw.csv"
    bronze = tmp_path / "bronze"
    log = bronze / "_ingestion_log.jsonl"

    _write_csv(
        source,
        _pos_headers(),
        [
            ["TX1", "2025-01-01T10:00:00", "2025-01-01", "ST001", "SKU1", 1, "10.00", "0.00", "10.00", "store", "card"],
            ["TX2", "2025-01-02T10:00:00", "2025-01-02", "ST001", "SKU2", 2, "15.00", "0.00", "30.00", "store", "card"],
        ],
    )

    first = ingest_dataset("pos_transactions_raw", source, bronze, log)
    second = ingest_dataset("pos_transactions_raw", source, bronze, log)

    assert first.status == "loaded"
    assert second.status == "skipped_unchanged"


def test_schema_drift_raises_error(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "pos_transactions_raw.csv"
    bronze = tmp_path / "bronze"
    log = bronze / "_ingestion_log.jsonl"

    bad_headers = _pos_headers()[:-1]
    _write_csv(
        source,
        bad_headers,
        [["TX1", "2025-01-01T10:00:00", "2025-01-01", "ST001", "SKU1", 1, "10.00", "0.00", "10.00", "store"]],
    )

    with pytest.raises(IngestionError, match="Schema drift"):
        ingest_dataset("pos_transactions_raw", source, bronze, log)


def test_freshness_check_blocks_stale_data(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "pos_transactions_raw.csv"
    bronze = tmp_path / "bronze"
    log = bronze / "_ingestion_log.jsonl"

    _write_csv(
        source,
        _pos_headers(),
        [["TX1", "2025-01-01T10:00:00", "2025-01-01", "ST001", "SKU1", 1, "10.00", "0.00", "10.00", "store", "card"]],
    )

    with pytest.raises(IngestionError, match="Freshness check failed"):
        ingest_dataset(
            "pos_transactions_raw",
            source,
            bronze,
            log,
            min_allowed_date=date(2025, 1, 2),
        )
