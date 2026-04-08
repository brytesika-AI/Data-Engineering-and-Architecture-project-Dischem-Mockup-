from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from apps.api.main import app


def main() -> None:
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200, r.text

    r = client.get("/kpis")
    assert r.status_code == 200, r.text
    assert "metrics" in r.json(), r.json()

    r = client.get("/inventory/health?limit=5")
    assert r.status_code == 200, r.text
    assert "items" in r.json(), r.json()

    r = client.get("/forecast?limit=5")
    assert r.status_code == 200, r.text
    assert "items" in r.json(), r.json()

    sample = r.json().get("items", [])
    sku_id = sample[0]["sku_id"] if sample else None

    payload = {"date": "2025-01-01", "store_id": "ST001"}
    if sku_id:
        payload["sku_id"] = sku_id

    r = client.post("/agent/explain", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    for field in ["summary", "risk_level", "recommended_actions", "confidence", "signals"]:
        assert field in body, body

    print("API smoke tests passed")


if __name__ == "__main__":
    main()
