from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required_files = [
    ROOT / "data" / "gold" / "kpi_summary.csv",
    ROOT / "data" / "gold" / "mart_inventory_health.csv",
    ROOT / "data" / "gold" / "forecast_sku_store_daily.csv",
    ROOT / "data" / "gold" / "streaming_alerts.csv",
    ROOT / "apps" / "dashboard" / "streamlit_app.py",
    ROOT / "apps" / "api" / "main.py",
]

missing = [str(p) for p in required_files if not p.exists()]
if missing:
    print("Missing required files:")
    for m in missing:
        print(f"- {m}")
    sys.exit(1)

print("Artifact smoke check passed")
