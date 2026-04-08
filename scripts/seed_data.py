"""Synthetic data generator for the Dis-Chem Omni-Channel Inventory Orchestrator.

Generates at least one year of data for:
- POS transactions
- ERP inventory snapshots
- Clinic scripts and dispensing
- Streaming inventory events
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Store:
    store_id: str
    tier: str
    region: str
    clinic_id: str


@dataclass(frozen=True)
class Product:
    sku_id: str
    category: str
    subcategory: str
    unit_cost: float
    unit_price: float
    shelf_life_days: int
    is_controlled_substance: int


def seasonality_multiplier(day: date, category: str) -> float:
    month = day.month
    weekend = 1.08 if day.weekday() >= 5 else 1.0

    flu_season = 1.28 if month in (5, 6, 7, 8) and category in {"acute_otc", "respiratory"} else 1.0
    year_end = 1.22 if month in (11, 12) and category in {"front_shop", "wellness"} else 1.0
    payday_bump = 1.10 if day.day in (24, 25, 26, 27, 28, 29, 30, 31) else 1.0

    return weekend * flu_season * year_end * payday_bump


def promo_multiplier(rng: random.Random) -> float:
    return 1.22 if rng.random() < 0.07 else 1.0


def poisson_like(rng: random.Random, lam: float) -> int:
    # Lightweight approximation without external dependencies.
    if lam <= 0:
        return 0
    g = math.exp(-lam)
    t = 1.0
    k = 0
    while t > g and k < 1000:
        t *= rng.random()
        k += 1
    return max(0, k - 1)


def build_stores(num_stores: int) -> list[Store]:
    regions = ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape", "Free State"]
    stores: list[Store] = []
    for i in range(1, num_stores + 1):
        tier = "high" if i <= int(num_stores * 0.25) else "medium" if i <= int(num_stores * 0.75) else "low"
        region = regions[(i - 1) % len(regions)]
        stores.append(Store(store_id=f"ST{i:03d}", tier=tier, region=region, clinic_id=f"CL{i:03d}"))
    return stores


def build_products(num_skus: int, rng: random.Random) -> list[Product]:
    category_mix = [
        ("chronic_rx", "chronic", 0.35),
        ("acute_otc", "acute", 0.20),
        ("respiratory", "acute", 0.10),
        ("front_shop", "retail", 0.25),
        ("wellness", "retail", 0.10),
    ]
    products: list[Product] = []
    for i in range(1, num_skus + 1):
        p = rng.random()
        csum = 0.0
        chosen = category_mix[-1]
        for item in category_mix:
            csum += item[2]
            if p <= csum:
                chosen = item
                break

        category, subcategory, _ = chosen
        is_sched6 = 1 if category == "chronic_rx" and rng.random() < 0.12 else 0

        cost = round(rng.uniform(20, 400), 2)
        margin = rng.uniform(1.15, 1.65) if category != "front_shop" else rng.uniform(1.25, 1.9)
        price = round(cost * margin, 2)
        shelf_life = 180 if category in {"chronic_rx", "acute_otc", "respiratory"} else 365

        products.append(
            Product(
                sku_id=f"SKU{i:05d}",
                category=category,
                subcategory=subcategory,
                unit_cost=cost,
                unit_price=price,
                shelf_life_days=shelf_life,
                is_controlled_substance=is_sched6,
            )
        )
    return products


def write_csv(path: Path, headers: list[str], rows: Iterable[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def generate_data(output_dir: Path, start: date, days: int, num_stores: int, num_skus: int, seed: int) -> None:
    rng = random.Random(seed)
    stores = build_stores(num_stores)
    products = build_products(num_skus, rng)

    store_weights = {"high": 1.8, "medium": 1.0, "low": 0.55}

    # Base demand per SKU kept small; multiplied by tier/season/promo.
    sku_base = {p.sku_id: rng.uniform(0.05, 1.8) for p in products}

    products_by_id = {p.sku_id: p for p in products}

    inventory = {}
    for s in stores:
        for p in products:
            open_units = int(max(0, rng.gauss(42, 20)))
            inventory[(s.store_id, p.sku_id)] = open_units

    product_rows = [
        [
            p.sku_id,
            p.category,
            p.subcategory,
            p.unit_cost,
            p.unit_price,
            p.shelf_life_days,
            p.is_controlled_substance,
        ]
        for p in products
    ]
    store_rows = [[s.store_id, s.tier, s.region, s.clinic_id] for s in stores]

    pos_rows: list[list[object]] = []
    erp_rows: list[list[object]] = []
    clinic_rows: list[list[object]] = []
    event_rows: list[list[object]] = []

    tx_id = 0
    script_id = 0
    snap_id = 0
    event_id = 0

    for d in range(days):
        current_day = start + timedelta(days=d)

        for s in stores:
            tier_weight = store_weights[s.tier]
            daily_vol_target = int(rng.uniform(120, 450) * tier_weight)
            sampled = rng.sample(products, k=min(len(products), max(60, daily_vol_target // 2)))

            for p in sampled:
                key = (s.store_id, p.sku_id)
                opening = inventory[key]

                seasonal = seasonality_multiplier(current_day, p.category)
                promo = promo_multiplier(rng)
                expected = sku_base[p.sku_id] * tier_weight * seasonal * promo
                demand_units = poisson_like(rng, expected)

                sold = min(opening, demand_units)
                stockout = 1 if demand_units > opening else 0

                if sold > 0:
                    tx_id += 1
                    discount = round(p.unit_price * rng.uniform(0.0, 0.12), 2)
                    unit_price = p.unit_price
                    net_sales = round((unit_price - discount) * sold, 2)
                    txn_ts = datetime.combine(current_day, datetime.min.time()) + timedelta(
                        minutes=rng.randint(8 * 60, 20 * 60)
                    )
                    channel_roll = rng.random()
                    channel = "store" if channel_roll < 0.88 else "online" if channel_roll < 0.96 else "clinic_pickup"
                    pay_type = "card" if rng.random() < 0.72 else "cash"
                    pos_rows.append(
                        [
                            f"TX{tx_id:012d}",
                            txn_ts.isoformat(),
                            current_day.isoformat(),
                            s.store_id,
                            p.sku_id,
                            sold,
                            f"{unit_price:.2f}",
                            f"{discount:.2f}",
                            f"{net_sales:.2f}",
                            channel,
                            pay_type,
                        ]
                    )

                clinic_units = 0
                if p.category == "chronic_rx" and rng.random() < 0.16 * tier_weight:
                    clinic_units = max(1, poisson_like(rng, 1.2))
                    script_id += 1
                    script_ts = datetime.combine(current_day, datetime.min.time()) + timedelta(
                        minutes=rng.randint(8 * 60, 17 * 60)
                    )
                    clinic_rows.append(
                        [
                            f"SC{script_id:012d}",
                            script_ts.isoformat(),
                            current_day.isoformat(),
                            s.clinic_id,
                            s.store_id,
                            "chronic",
                            p.sku_id,
                            clinic_units,
                            "chronic_care",
                            p.is_controlled_substance,
                        ]
                    )

                consumed = sold + clinic_units
                remaining = max(0, opening - consumed)

                receipts = 0
                reorder_point = 18 if s.tier == "high" else 12 if s.tier == "medium" else 8
                lead_time = int(max(1, round(rng.gauss(4.0, 1.2))))

                if remaining <= reorder_point:
                    receipts = int(max(reorder_point * 2.1, consumed * rng.uniform(1.3, 2.2)))
                    remaining += receipts

                    event_id += 1
                    event_rows.append(
                        [
                            f"EV{event_id:012d}",
                            datetime.combine(current_day, datetime.min.time())
                            .replace(hour=14, minute=rng.randint(0, 50))
                            .isoformat(),
                            current_day.isoformat(),
                            s.store_id,
                            p.sku_id,
                            "reorder_trigger",
                            receipts,
                            remaining,
                            "0.78",
                        ]
                    )

                if stockout:
                    event_id += 1
                    event_rows.append(
                        [
                            f"EV{event_id:012d}",
                            datetime.combine(current_day, datetime.min.time())
                            .replace(hour=18, minute=rng.randint(0, 50))
                            .isoformat(),
                            current_day.isoformat(),
                            s.store_id,
                            p.sku_id,
                            "stockout_risk",
                            -max(1, demand_units - opening),
                            remaining,
                            "0.91",
                        ]
                    )

                if remaining > reorder_point * 4:
                    event_id += 1
                    event_rows.append(
                        [
                            f"EV{event_id:012d}",
                            datetime.combine(current_day, datetime.min.time())
                            .replace(hour=19, minute=rng.randint(0, 50))
                            .isoformat(),
                            current_day.isoformat(),
                            s.store_id,
                            p.sku_id,
                            "overstock_risk",
                            0,
                            remaining,
                            "0.64",
                        ]
                    )

                if p.shelf_life_days <= 180 and rng.random() < 0.015:
                    event_id += 1
                    event_rows.append(
                        [
                            f"EV{event_id:012d}",
                            datetime.combine(current_day, datetime.min.time())
                            .replace(hour=16, minute=rng.randint(0, 50))
                            .isoformat(),
                            current_day.isoformat(),
                            s.store_id,
                            p.sku_id,
                            "expiry_risk",
                            0,
                            remaining,
                            "0.73",
                        ]
                    )

                snap_id += 1
                expiry_dt = current_day + timedelta(days=p.shelf_life_days)
                erp_rows.append(
                    [
                        f"SN{snap_id:012d}",
                        current_day.isoformat(),
                        s.store_id,
                        p.sku_id,
                        opening,
                        receipts,
                        remaining,
                        reorder_point,
                        lead_time,
                        f"{p.unit_cost:.2f}",
                        expiry_dt.isoformat(),
                        p.is_controlled_substance,
                    ]
                )

                inventory[key] = remaining

    write_csv(
        output_dir / "dim_products.csv",
        [
            "sku_id",
            "category",
            "subcategory",
            "unit_cost",
            "unit_price",
            "shelf_life_days",
            "is_controlled_substance",
        ],
        product_rows,
    )
    write_csv(output_dir / "dim_stores.csv", ["store_id", "tier", "region", "clinic_id"], store_rows)

    write_csv(
        output_dir / "pos_transactions_raw.csv",
        [
            "transaction_line_id",
            "transaction_ts",
            "date",
            "store_id",
            "sku_id",
            "quantity",
            "unit_price",
            "discount_amount",
            "net_sales_amount",
            "channel",
            "payment_type",
        ],
        pos_rows,
    )

    write_csv(
        output_dir / "sap_inventory_levels_raw.csv",
        [
            "snapshot_id",
            "date",
            "store_id",
            "sku_id",
            "opening_stock_units",
            "receipts_units",
            "closing_stock_units",
            "reorder_point_units",
            "lead_time_days",
            "unit_cost",
            "expiry_date",
            "is_controlled_substance",
        ],
        erp_rows,
    )

    write_csv(
        output_dir / "clinic_scripts_raw.csv",
        [
            "script_line_id",
            "script_ts",
            "date",
            "clinic_id",
            "store_id",
            "patient_segment",
            "sku_id",
            "quantity_dispensed",
            "diagnosis_group",
            "is_schedule_6",
        ],
        clinic_rows,
    )

    write_csv(
        output_dir / "streaming_inventory_events_raw.csv",
        [
            "event_id",
            "event_ts",
            "date",
            "store_id",
            "sku_id",
            "event_type",
            "delta_units",
            "resulting_stock_units",
            "risk_score",
        ],
        event_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Dis-Chem synthetic one-year operational data.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--start-date", type=str, default="2025-01-01")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--stores", type=int, default=100)
    parser.add_argument("--skus", type=int, default=2500)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    generate_data(args.output_dir, start, args.days, args.stores, args.skus, args.seed)
    print(f"Synthetic data generated in: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
