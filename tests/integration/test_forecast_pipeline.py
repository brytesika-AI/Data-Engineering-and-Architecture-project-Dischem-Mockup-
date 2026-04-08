from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from dischem_orchestrator.forecasting import run_baseline_forecast


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def test_baseline_forecast_pipeline(tmp_path: Path) -> None:
    sales = tmp_path / "fct_sales_daily.csv"
    models_dir = tmp_path / "models"
    forecast_output = tmp_path / "forecast.csv"

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

    rows = []
    start = date(2025, 1, 1)
    for i in range(60):
        day = (start + timedelta(days=i)).isoformat()
        rows.append([day, "ST001", "SKU1", "store", 1, 10 + (i % 3), 100.0, 0.0, 100.0])
    _write_csv(sales, headers, rows)

    artifacts = run_baseline_forecast(
        sales_daily_path=sales,
        forecast_output_path=forecast_output,
        models_dir=models_dir,
        horizon_days=7,
        holdout_days=14,
        window_days=7,
    )

    assert artifacts.backtest_rows > 0
    assert artifacts.forecast_rows == 7

    metrics = json.loads((models_dir / "metrics_latest.json").read_text(encoding="utf-8"))
    assert "wape" in metrics["metrics"]
    assert (models_dir / "registry.json").exists()
