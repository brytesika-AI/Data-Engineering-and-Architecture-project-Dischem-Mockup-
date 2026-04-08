from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dischem_orchestrator.streaming import build_streaming_alerts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate streaming inventory alerts from event and KPI/forecast context.")
    parser.add_argument("--events", type=Path, default=Path("data/raw/streaming_inventory_events_raw.csv"))
    parser.add_argument("--kpi-summary", type=Path, default=Path("data/gold/kpi_summary.csv"))
    parser.add_argument("--forecast", type=Path, default=Path("data/gold/forecast_sku_store_daily.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/gold/streaming_alerts.csv"))
    parser.add_argument("--quality-report", type=Path, default=Path("data/gold/streaming_alerts_quality.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifacts = build_streaming_alerts(
        events_path=args.events,
        kpi_summary_path=args.kpi_summary,
        forecast_path=args.forecast,
        output_path=args.output,
        quality_report_path=args.quality_report,
    )
    print(
        "Streaming simulation complete: "
        f"alerts={artifacts.alert_rows}, "
        f"output={artifacts.output_path}, "
        f"quality_report={artifacts.quality_report_path}"
    )


if __name__ == "__main__":
    main()
