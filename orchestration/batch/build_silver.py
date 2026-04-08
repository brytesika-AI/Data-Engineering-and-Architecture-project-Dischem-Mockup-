from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dischem_orchestrator.silver import build_silver_layer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Silver layer datasets from Bronze inputs.")
    parser.add_argument("--raw-products", type=Path, default=Path("data/raw/dim_products.csv"))
    parser.add_argument("--bronze-pos", type=Path, default=Path("data/bronze/pos_transactions_raw.csv"))
    parser.add_argument("--bronze-sap", type=Path, default=Path("data/bronze/sap_inventory_levels_raw.csv"))
    parser.add_argument("--bronze-clinic", type=Path, default=Path("data/bronze/clinic_scripts_raw.csv"))
    parser.add_argument("--silver-dir", type=Path, default=Path("data/silver"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifacts = build_silver_layer(
        raw_products_path=args.raw_products,
        bronze_pos_path=args.bronze_pos,
        bronze_sap_path=args.bronze_sap,
        bronze_clinic_path=args.bronze_clinic,
        silver_dir=args.silver_dir,
    )
    print(
        "Silver build complete: "
        f"dim_products_hc={artifacts.dim_products_rows}, "
        f"fct_inventory_snapshots={artifacts.inventory_rows}, "
        f"fct_dispensing_log={artifacts.dispensing_rows}, "
        f"fct_sales_daily={artifacts.sales_daily_rows}, "
        f"quality_report={artifacts.quality_report_path}"
    )


if __name__ == "__main__":
    main()
