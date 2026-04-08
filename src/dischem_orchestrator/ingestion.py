"""Bronze ingestion utilities for stage-2 pipelines."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from dischem_orchestrator.contracts import CONTRACTS


class IngestionError(Exception):
    """Raised when ingestion validation fails."""


@dataclass
class IngestionResult:
    dataset: str
    source_path: Path
    target_path: Path
    run_id: str
    status: str
    row_count: int
    source_sha256: str
    max_date: str | None
    ingested_at_utc: str


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return sum(1 for _ in reader)


def csv_headers(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
    if not headers:
        raise IngestionError(f"Empty CSV or missing header: {path}")
    return headers


def max_date_in_column(path: Path, date_column: str) -> date | None:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if date_column not in reader.fieldnames:
            raise IngestionError(f"Date column '{date_column}' missing from {path}")

        max_seen: date | None = None
        for row in reader:
            raw = row.get(date_column)
            if not raw:
                continue
            try:
                current = date.fromisoformat(raw)
            except ValueError as exc:
                raise IngestionError(f"Invalid ISO date '{raw}' in {path}") from exc
            if max_seen is None or current > max_seen:
                max_seen = current
        return max_seen


def validate_schema(path: Path, required_columns: list[str]) -> list[str]:
    headers = csv_headers(path)
    if headers != required_columns:
        raise IngestionError(
            "Schema drift detected. "
            f"Expected columns {required_columns}, got {headers}."
        )
    return headers


def validate_freshness(path: Path, date_column: str, min_allowed_date: date | None) -> date | None:
    max_seen = max_date_in_column(path, date_column)
    if min_allowed_date and max_seen and max_seen < min_allowed_date:
        raise IngestionError(
            f"Freshness check failed for {path.name}: max {max_seen} < required {min_allowed_date}."
        )
    return max_seen


def append_ingestion_log(log_path: Path, result: IngestionResult) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": result.run_id,
        "dataset": result.dataset,
        "source_path": str(result.source_path),
        "target_path": str(result.target_path),
        "status": result.status,
        "row_count": result.row_count,
        "source_sha256": result.source_sha256,
        "max_date": result.max_date,
        "ingested_at_utc": result.ingested_at_utc,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def ingest_dataset(
    dataset: str,
    source_path: Path,
    bronze_dir: Path,
    metadata_log_path: Path,
    min_allowed_date: date | None = None,
) -> IngestionResult:
    if dataset not in CONTRACTS:
        raise IngestionError(f"Unknown dataset '{dataset}'.")
    if not source_path.exists():
        raise IngestionError(f"Source file does not exist: {source_path}")

    contract = CONTRACTS[dataset]
    required_columns = contract["required_columns"]
    date_column = contract["date_column"]

    validate_schema(source_path, required_columns)
    max_seen = validate_freshness(source_path, date_column, min_allowed_date)

    source_hash = sha256_file(source_path)
    target_path = bronze_dir / source_path.name
    target_path.parent.mkdir(parents=True, exist_ok=True)

    status = "loaded"
    if target_path.exists() and sha256_file(target_path) == source_hash:
        status = "skipped_unchanged"
    else:
        shutil.copy2(source_path, target_path)

    result = IngestionResult(
        dataset=dataset,
        source_path=source_path.resolve(),
        target_path=target_path.resolve(),
        run_id=str(uuid.uuid4()),
        status=status,
        row_count=count_rows(source_path),
        source_sha256=source_hash,
        max_date=max_seen.isoformat() if max_seen else None,
        ingested_at_utc=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )
    append_ingestion_log(metadata_log_path, result)
    return result
