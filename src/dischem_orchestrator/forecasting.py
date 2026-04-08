"""Baseline forecasting pipeline for SKU-store demand."""

from __future__ import annotations

import csv
import json
import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


class ForecastingError(Exception):
    """Raised when forecast training or generation fails."""


@dataclass
class ForecastArtifacts:
    run_id: str
    model_version: str
    horizon_days: int
    holdout_days: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    backtest_rows: int
    forecast_rows: int
    metrics_path: Path
    forecast_path: Path
    run_dir: Path


def _read_csv(path: Path) -> csv.DictReader:
    f = path.open("r", encoding="utf-8", newline="")
    return csv.DictReader(f)


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    return len(rows)


def _iso(d: date) -> str:
    return d.isoformat()


def _safe_mean(values: list[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def _global_dow_multipliers(series: dict[tuple[str, str], dict[date, float]], train_end: date) -> dict[int, float]:
    dow_values = defaultdict(list)
    for _, daily in series.items():
        for d, y in daily.items():
            if d <= train_end:
                dow_values[d.weekday()].append(y)

    global_avg = _safe_mean([v for values in dow_values.values() for v in values], 1.0)
    multipliers = {}
    for dow in range(7):
        dow_avg = _safe_mean(dow_values[dow], global_avg)
        multipliers[dow] = dow_avg / global_avg if global_avg > 0 else 1.0
    return multipliers


def _load_series(sales_daily_path: Path) -> tuple[dict[tuple[str, str], dict[date, float]], date, date]:
    if not sales_daily_path.exists():
        raise ForecastingError(f"Missing sales source: {sales_daily_path}")

    series: dict[tuple[str, str], dict[date, float]] = defaultdict(lambda: defaultdict(float))
    min_d: date | None = None
    max_d: date | None = None

    with sales_daily_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            d = date.fromisoformat(r["date"])
            key = (r["store_id"], r["sku_id"])
            series[key][d] += float(r["units_sold"])

            if min_d is None or d < min_d:
                min_d = d
            if max_d is None or d > max_d:
                max_d = d

    if min_d is None or max_d is None:
        raise ForecastingError("No rows found in sales daily source.")

    return series, min_d, max_d


def _predict_from_history(
    history: dict[date, float],
    target_day: date,
    window_days: int,
    dow_multiplier: float,
    fallback_mean: float,
) -> float:
    prior_days = [target_day - timedelta(days=i) for i in range(1, window_days + 1)]
    vals = [history[d] for d in prior_days if d in history]
    base = _safe_mean(vals, fallback_mean)
    pred = max(0.0, base * dow_multiplier)
    return pred


def run_baseline_forecast(
    sales_daily_path: Path,
    forecast_output_path: Path,
    models_dir: Path,
    horizon_days: int = 30,
    holdout_days: int = 28,
    window_days: int = 7,
    model_version: str = "baseline_v1_rolling_mean_dow",
) -> ForecastArtifacts:
    if horizon_days < 1 or holdout_days < 1 or window_days < 1:
        raise ForecastingError("horizon_days, holdout_days, and window_days must be >= 1")

    series, min_d, max_d = _load_series(sales_daily_path)
    if (max_d - min_d).days + 1 <= holdout_days:
        raise ForecastingError("Not enough history for the selected holdout period.")

    test_start = max_d - timedelta(days=holdout_days - 1)
    train_end = test_start - timedelta(days=1)

    run_id = f"fr_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    run_dir = models_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    dow_multipliers = _global_dow_multipliers(series, train_end)

    backtest_rows: list[list[object]] = []
    ae_sum = 0.0
    se_sum = 0.0
    ape_sum = 0.0
    ape_count = 0
    actual_sum = 0.0

    # Backtest with walk-forward updates using actuals as they become available.
    for key, daily in series.items():
        store_id, sku_id = key
        history = {d: y for d, y in daily.items() if d <= train_end}
        fallback = _safe_mean(list(history.values()), 0.0)

        current = test_start
        while current <= max_d:
            actual = daily.get(current, 0.0)
            pred = _predict_from_history(
                history=history,
                target_day=current,
                window_days=window_days,
                dow_multiplier=dow_multipliers[current.weekday()],
                fallback_mean=fallback,
            )

            err = actual - pred
            ae = abs(err)
            se = err * err
            ae_sum += ae
            se_sum += se
            actual_sum += actual
            if actual > 0:
                ape_sum += ae / actual
                ape_count += 1

            backtest_rows.append([
                _iso(current),
                store_id,
                sku_id,
                round(actual, 4),
                round(pred, 4),
                round(ae, 4),
            ])

            history[current] = actual
            current += timedelta(days=1)

    backtest_path = run_dir / "backtest_predictions.csv"
    backtest_count = _write_csv(
        backtest_path,
        ["date", "store_id", "sku_id", "actual_units", "predicted_units", "absolute_error"],
        backtest_rows,
    )

    rmse = math.sqrt(se_sum / max(backtest_count, 1))
    wape = ae_sum / max(actual_sum, 1.0)
    mape = ape_sum / max(ape_count, 1)

    # Generate forward forecast.
    forecast_rows: list[list[object]] = []
    forecast_start = max_d + timedelta(days=1)
    forecast_end = max_d + timedelta(days=horizon_days)

    for key, daily in series.items():
        store_id, sku_id = key
        history = dict(daily)
        fallback = _safe_mean(list(history.values()), 0.0)

        current = forecast_start
        while current <= forecast_end:
            pred = _predict_from_history(
                history=history,
                target_day=current,
                window_days=window_days,
                dow_multiplier=dow_multipliers[current.weekday()],
                fallback_mean=fallback,
            )
            pred = max(0.0, round(pred, 4))

            forecast_rows.append([
                _iso(current),
                store_id,
                sku_id,
                pred,
                model_version,
                run_id,
            ])

            # Recursive path for multi-step horizon.
            history[current] = pred
            current += timedelta(days=1)

    forecast_count = _write_csv(
        forecast_output_path,
        ["forecast_date", "store_id", "sku_id", "predicted_units", "model_version", "run_id"],
        forecast_rows,
    )

    metrics = {
        "run_id": run_id,
        "model_version": model_version,
        "created_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "config": {
            "horizon_days": horizon_days,
            "holdout_days": holdout_days,
            "window_days": window_days,
        },
        "date_ranges": {
            "train_start": _iso(min_d),
            "train_end": _iso(train_end),
            "test_start": _iso(test_start),
            "test_end": _iso(max_d),
            "forecast_start": _iso(forecast_start),
            "forecast_end": _iso(forecast_end),
        },
        "metrics": {
            "backtest_rows": backtest_count,
            "wape": round(wape, 6),
            "mape": round(mape, 6),
            "rmse": round(rmse, 6),
        },
        "artifacts": {
            "backtest_predictions": str(backtest_path),
            "forecast_output": str(forecast_output_path),
        },
    }

    metrics_path = run_dir / "metrics.json"
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Update latest + simple registry (MLflow-like placeholder).
    latest_path = models_dir / "metrics_latest.json"
    with latest_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    registry_path = models_dir / "registry.json"
    registry = {"models": []}
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        if "models" not in registry:
            registry["models"] = []

    registry["models"].append(
        {
            "run_id": run_id,
            "model_version": model_version,
            "created_at_utc": metrics["created_at_utc"],
            "wape": metrics["metrics"]["wape"],
            "mape": metrics["metrics"]["mape"],
            "rmse": metrics["metrics"]["rmse"],
            "run_dir": str(run_dir),
            "forecast_output": str(forecast_output_path),
            "is_latest": True,
        }
    )

    for m in registry["models"][:-1]:
        m["is_latest"] = False

    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    return ForecastArtifacts(
        run_id=run_id,
        model_version=model_version,
        horizon_days=horizon_days,
        holdout_days=holdout_days,
        train_start=_iso(min_d),
        train_end=_iso(train_end),
        test_start=_iso(test_start),
        test_end=_iso(max_d),
        backtest_rows=backtest_count,
        forecast_rows=forecast_count,
        metrics_path=metrics_path,
        forecast_path=forecast_output_path,
        run_dir=run_dir,
    )
