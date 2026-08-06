"""
Sinh dữ liệu giao dịch mô phỏng với seed cố định.
- customers >= 200
- orders >= 1000
- order_details >= 3000
- inventory_transactions (nhập đầu kỳ + xuất theo đơn + một số điều chỉnh)
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from clean_products import read_csv, write_csv

CITIES = [
    "Hà Nội",
    "TP. Hồ Chí Minh",
    "Đà Nẵng",
    "Hải Phòng",
    "Cần Thơ",
    "Huế",
    "Nha Trang",
    "Biên Hòa",
]
CUSTOMER_TYPES = ["retail", "wholesale", "student", "office"]
PAYMENTS = ["cash", "transfer", "card", "e-wallet"]
CHANNELS = ["offline", "online", "shopee", "website"]


def _weighted_choice(rng: random.Random, items: list[dict], weight_key: str) -> dict:
    weights = [max(0.1, float(i.get(weight_key, 1))) for i in items]
    return rng.choices(items, weights=weights, k=1)[0]


def generate_customers(n: int, rng: random.Random, start_date: datetime) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        join = start_date + timedelta(days=rng.randint(0, 400))
        rows.append(
            {
                "customer_id": f"C{i:04d}",
                "city": rng.choice(CITIES),
                "customer_type": rng.choices(
                    CUSTOMER_TYPES, weights=[0.55, 0.15, 0.2, 0.1], k=1
                )[0],
                "join_date": join.date().isoformat(),
            }
        )
    return rows


def generate_orders_and_details(
    products: list[dict],
    customers: list[dict],
    n_orders: int,
    rng: random.Random,
    start_date: datetime,
    end_date: datetime,
) -> tuple[list[dict], list[dict], dict[str, int]]:
    """
    Trả về orders, order_details, sold_qty_by_product.
    """
    products_by_id = {p["product_id"]: p for p in products}
    span_days = max(1, (end_date - start_date).days)
    orders: list[dict] = []
    details: list[dict] = []
    sold: dict[str, int] = {p["product_id"]: 0 for p in products}

    for i in range(1, n_orders + 1):
        order_id = f"ORD{i:06d}"
        cust = rng.choice(customers)
        order_dt = start_date + timedelta(
            days=rng.randint(0, span_days),
            hours=rng.randint(8, 20),
            minutes=rng.randint(0, 59),
        )
        n_lines = rng.choices([1, 2, 3, 4, 5], weights=[0.25, 0.35, 0.25, 0.1, 0.05], k=1)[0]
        chosen_ids: list[str] = []

        for _ in range(n_lines):
            p = _weighted_choice(rng, products, "popularity_weight")
            if p["product_id"] in chosen_ids:
                continue
            chosen_ids.append(p["product_id"])
            # đôi khi thêm sản phẩm cặp
            paired = (p.get("paired_product_id") or "").strip()
            if paired and paired in products_by_id and paired not in chosen_ids:
                if rng.random() < 0.55:
                    chosen_ids.append(paired)

        if not chosen_ids:
            chosen_ids = [rng.choice(products)["product_id"]]

        discount = 0.0
        if rng.random() < 0.18:
            discount = float(rng.choice([5000, 10000, 20000, 50000]))

        orders.append(
            {
                "order_id": order_id,
                "customer_id": cust["customer_id"],
                "order_date": order_dt.isoformat(timespec="seconds"),
                "payment_method": rng.choice(PAYMENTS),
                "sales_channel": rng.choices(
                    CHANNELS, weights=[0.45, 0.2, 0.2, 0.15], k=1
                )[0],
                "discount": discount,
            }
        )

        for pid in chosen_ids:
            p = products_by_id[pid]
            # wholesale mua nhiều hơn
            if cust["customer_type"] == "wholesale":
                qty = rng.randint(5, 30)
            elif cust["customer_type"] == "office":
                qty = rng.randint(2, 12)
            else:
                qty = rng.randint(1, 5)

            # giá bán có thể giảm nhẹ so với niêm yết
            base = float(p["unit_price"])
            sell = base if rng.random() < 0.7 else round(base * rng.uniform(0.9, 0.99), 0)

            details.append(
                {
                    "order_id": order_id,
                    "product_id": pid,
                    "quantity": qty,
                    "selling_price": sell,
                }
            )
            sold[pid] = sold.get(pid, 0) + qty

    return orders, details, sold


def generate_inventory_transactions(
    products: list[dict],
    orders: list[dict],
    details: list[dict],
    rng: random.Random,
    start_date: datetime,
) -> list[dict]:
    """
    Sinh giao dịch:
    1) import đầu kỳ = initial_quantity
    2) sale theo từng dòng order_details (timestamp ~ order_date)
    3) một số adjust / import bổ sung
    """
    order_date = {o["order_id"]: o["order_date"] for o in orders}
    txs: list[dict] = []
    tx_i = 0

    def add_tx(**kwargs: Any) -> None:
        nonlocal tx_i
        tx_i += 1
        txs.append({"transaction_id": f"TX{tx_i:06d}", **kwargs})

    # 1) nhập đầu kỳ
    for p in products:
        qty = int(float(p["initial_quantity"]))
        add_tx(
            timestamp=(start_date - timedelta(days=1)).isoformat(timespec="seconds"),
            transaction_type="import",
            product_id=p["product_id"],
            quantity=qty,
            performed_by="warehouse",
            status="success",
            note="opening_stock",
        )

    # 2) xuất theo đơn
    for d in details:
        add_tx(
            timestamp=order_date[d["order_id"]],
            transaction_type="sale",
            product_id=d["product_id"],
            quantity=int(d["quantity"]),
            performed_by="cashier",
            status="success",
            note=f"order={d['order_id']}",
        )

    # 3) nhập bổ sung / điều chỉnh ngẫu nhiên
    for p in products:
        if rng.random() < 0.25:
            ts = start_date + timedelta(days=rng.randint(10, 150), hours=9)
            add_tx(
                timestamp=ts.isoformat(timespec="seconds"),
                transaction_type="import",
                product_id=p["product_id"],
                quantity=rng.randint(10, 80),
                performed_by="warehouse",
                status="success",
                note="restock",
            )
        if rng.random() < 0.08:
            ts = start_date + timedelta(days=rng.randint(20, 160), hours=15)
            add_tx(
                timestamp=ts.isoformat(timespec="seconds"),
                transaction_type="adjust",
                product_id=p["product_id"],
                quantity=rng.randint(1, 5),
                performed_by="auditor",
                status="success",
                note="stocktake_shrinkage",
            )

    txs.sort(key=lambda x: (x["timestamp"], x["transaction_id"]))
    # đánh lại ID theo thứ tự thời gian
    for i, tx in enumerate(txs, start=1):
        tx["transaction_id"] = f"TX{i:06d}"
    return txs


def generate_all(
    products_path: Path,
    out_dir: Path,
    seed: int = 42,
    n_customers: int = 220,
    n_orders: int = 1200,
) -> dict[str, Any]:
    rng = random.Random(seed)
    products = read_csv(products_path)
    start_date = datetime(2025, 1, 1, 8, 0, 0)
    end_date = datetime(2025, 12, 31, 20, 0, 0)

    customers = generate_customers(n_customers, rng, start_date - timedelta(days=400))
    orders, details, sold = generate_orders_and_details(
        products, customers, n_orders, rng, start_date, end_date
    )
    inventory = generate_inventory_transactions(
        products, orders, details, rng, start_date
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        customers,
        out_dir / "customers.csv",
        ["customer_id", "city", "customer_type", "join_date"],
    )
    write_csv(
        orders,
        out_dir / "orders.csv",
        [
            "order_id",
            "customer_id",
            "order_date",
            "payment_method",
            "sales_channel",
            "discount",
        ],
    )
    write_csv(
        details,
        out_dir / "order_details.csv",
        ["order_id", "product_id", "quantity", "selling_price"],
    )
    write_csv(
        inventory,
        out_dir / "inventory_transactions.csv",
        [
            "transaction_id",
            "timestamp",
            "transaction_type",
            "product_id",
            "quantity",
            "performed_by",
            "status",
            "note",
        ],
    )

    # quy tắc công bố
    rules = {
        "seed": seed,
        "n_customers": len(customers),
        "n_orders": len(orders),
        "n_order_details": len(details),
        "n_inventory_tx": len(inventory),
        "order_period": f"{start_date.date()} .. {end_date.date()}",
        "selection": "weighted by popularity_weight; paired_product_id boost ~55%",
        "pricing": "70% list price, 30% 90-99% of list",
        "note": "Synthetic transactional data generated for coursework; not real sales.",
    }
    return rules
