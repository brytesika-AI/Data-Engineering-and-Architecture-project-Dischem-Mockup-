from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dischem_orchestrator.forecasting import run_baseline_forecast


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train baseline forecast model and generate outputs.")
    parser.add_argument("--sales-daily", type=Path, default=Path("data/silver/fct_sales_daily.csv"))
    parser.add_argument("--forecast-output", type=Path, default=Path("data/gold/forecast_sku_store_daily.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models/forecasting"))
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--holdout-days", type=int, default=28)
    parser.add_argument("--window-days", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifacts = run_baseline_forecast(
        sales_daily_path=args.sales_daily,
        forecast_output_path=args.forecast_output,
        models_dir=args.models_dir,
        horizon_days=args.horizon_days,
        holdout_days=args.holdout_days,
        window_days=args.window_days,
    )
    print(
        "Forecast pipeline complete: "
        f"run_id={artifacts.run_id}, "
        f"backtest_rows={artifacts.backtest_rows}, "
        f"forecast_rows={artifacts.forecast_rows}, "
        f"metrics={artifacts.metrics_path}, "
        f"forecast_output={artifacts.forecast_path}"
    )


if __name__ == "__main__":
    main()
