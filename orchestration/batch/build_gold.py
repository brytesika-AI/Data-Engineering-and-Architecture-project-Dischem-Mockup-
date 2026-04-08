from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dischem_orchestrator.gold import build_gold_layer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gold marts and KPI outputs from Silver inputs.")
    parser.add_argument("--silver-dir", type=Path, default=Path("data/silver"))
    parser.add_argument("--gold-dir", type=Path, default=Path("data/gold"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifacts = build_gold_layer(args.silver_dir, args.gold_dir)
    print(
        "Gold build complete: "
        f"mart_inventory_health={artifacts.inventory_health_rows}, "
        f"mart_financial_performance={artifacts.financial_rows}, "
        f"mart_customer_behavior={artifacts.customer_rows}, "
        f"kpi_summary={artifacts.kpi_rows}, "
        f"quality_report={artifacts.quality_report_path}"
    )


if __name__ == "__main__":
    main()
