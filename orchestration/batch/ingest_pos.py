from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dischem_orchestrator.ingestion import ingest_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest POS raw data into Bronze layer.")
    parser.add_argument("--source", type=Path, default=Path("data/raw/pos_transactions_raw.csv"))
    parser.add_argument("--bronze-dir", type=Path, default=Path("data/bronze"))
    parser.add_argument("--metadata-log", type=Path, default=Path("data/bronze/_ingestion_log.jsonl"))
    parser.add_argument("--min-allowed-date", type=str, default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    min_date = date.fromisoformat(args.min_allowed_date) if args.min_allowed_date else None
    result = ingest_dataset(
        dataset="pos_transactions_raw",
        source_path=args.source,
        bronze_dir=args.bronze_dir,
        metadata_log_path=args.metadata_log,
        min_allowed_date=min_date,
    )
    print(f"[{result.status}] {result.dataset}: {result.row_count} rows -> {result.target_path}")


if __name__ == "__main__":
    main()
