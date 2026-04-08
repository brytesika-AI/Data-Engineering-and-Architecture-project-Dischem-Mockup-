from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dischem_orchestrator.agent import explain_inventory_exception


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run governed inventory agent explanation.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--store-id", required=True)
    parser.add_argument("--sku-id", default="")
    parser.add_argument("--kpi", type=Path, default=Path("data/gold/kpi_summary.csv"))
    parser.add_argument("--alerts", type=Path, default=Path("data/gold/streaming_alerts.csv"))
    parser.add_argument("--forecast", type=Path, default=Path("data/gold/forecast_sku_store_daily.csv"))
    parser.add_argument("--policy", type=Path, default=Path("config/policies/agent_policy.json"))
    parser.add_argument("--prompt", type=Path, default=Path("config/prompts/inventory_agent_prompt.txt"))
    parser.add_argument("--audit-log", type=Path, default=Path("models/llmops/agent_explanations_log.jsonl"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = explain_inventory_exception(
        day=args.date,
        store_id=args.store_id,
        sku_id=args.sku_id or None,
        kpi_path=args.kpi,
        alerts_path=args.alerts,
        forecast_path=args.forecast,
        policy_path=args.policy,
        prompt_path=args.prompt,
        audit_log_path=args.audit_log,
    )
    print(json.dumps(result.as_dict(), indent=2))


if __name__ == "__main__":
    main()
