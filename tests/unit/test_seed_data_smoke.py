from pathlib import Path
import subprocess
import sys


def test_seed_data_smoke(tmp_path: Path) -> None:
    output_dir = tmp_path / "raw"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/seed_data.py",
            "--output-dir",
            str(output_dir),
            "--days",
            "10",
            "--stores",
            "5",
            "--skus",
            "80",
            "--seed",
            "7",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    expected = {
        "dim_products.csv",
        "dim_stores.csv",
        "pos_transactions_raw.csv",
        "sap_inventory_levels_raw.csv",
        "clinic_scripts_raw.csv",
        "streaming_inventory_events_raw.csv",
    }
    found = {p.name for p in output_dir.glob("*.csv")}
    assert expected.issubset(found)
