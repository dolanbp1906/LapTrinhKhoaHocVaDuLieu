"""
Buổi 3 — Crawl bổ sung từ DummyJSON Products API.
Docs: https://dummyjson.com/docs/products
Chỉ lấy category phù hợp cửa hàng nhà sách/văn phòng phẩm/thiết bị.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Callable

import requests

# Tỷ giá quy đổi USD -> VND (công bố rõ, dùng để chuẩn hóa đơn vị tiền)
USD_TO_VND = 25_000

CATEGORY_MAP = {
    "laptops": "Thiết bị văn phòng",
    "tablets": "Thiết bị văn phòng",
    "mobile-accessories": "Phụ kiện máy tính",
}

UNIT_MAP = {
    "laptops": "chiếc",
    "tablets": "chiếc",
    "mobile-accessories": "cái",
}


def fetch_category(category: str, timeout: int = 20, sleep_s: float = 1.0) -> list[dict]:
    url = f"https://dummyjson.com/products/category/{category}"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    time.sleep(sleep_s)
    return resp.json().get("products", [])


def simulate_inventory(seed: int) -> tuple[int, int]:
    """Trường mô phỏng — phải ghi rõ trong báo cáo."""
    initial = 40 + (seed * 7) % 120
    reorder = max(5, initial // 5)
    return initial, reorder


def to_product_row(
    item: dict,
    product_id: str,
    collected_at: str,
) -> dict:
    cat = item.get("category", "")
    price_vnd = int(round(float(item["price"]) * USD_TO_VND))
    initial_qty, reorder = simulate_inventory(int(item.get("id", 1)))
    stock = item.get("stock")
    if isinstance(stock, int) and stock > 0:
        initial_qty = stock
        reorder = max(5, stock // 5)

    return {
        "product_id": product_id,
        "product_name": str(item.get("title", "")).strip(),
        "category": CATEGORY_MAP.get(cat, cat),
        "brand": str(item.get("brand") or "Unknown").strip() or "Unknown",
        "unit": UNIT_MAP.get(cat, "cái"),
        "unit_price": price_vnd,
        "initial_quantity": initial_qty,
        "reorder_level": reorder,
        "popularity_weight": max(1, int(round(float(item.get("rating", 3))))) ,
        "paired_product_id": "",
        "source_type": "public_api",
        "source_reference": "https://dummyjson.com/products",
        "source_url": f"https://dummyjson.com/products/{item.get('id')}",
        "collected_at": collected_at,
        "raw_category": cat,
        "raw_price_usd": item.get("price"),
        "fx_usd_vnd": USD_TO_VND,
        "simulated_fields": "initial_quantity,reorder_level,popularity_weight,paired_product_id,product_id,unit_price(fx)",
    }


def crawl_dummyjson(
    start_id: int = 61,
    max_items: int = 15,
    log_fn: Callable[[str], None] | None = None,
) -> list[dict]:
    log = log_fn or (lambda m: None)
    collected_at = datetime.now().isoformat(timespec="seconds")
    rows: list[dict] = []
    next_id = start_id
    ok, fail = 0, 0

    for category in CATEGORY_MAP:
        try:
            log(f"[DummyJSON] GET category={category}")
            items = fetch_category(category)
            log(f"[DummyJSON] category={category} got={len(items)}")
        except Exception as exc:  # noqa: BLE001
            fail += 1
            log(f"[DummyJSON][ERROR] category={category}: {exc}")
            continue

        for item in items:
            if len(rows) >= max_items:
                break
            try:
                pid = f"P{next_id:04d}"
                rows.append(to_product_row(item, pid, collected_at))
                next_id += 1
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                log(f"[DummyJSON][ERROR] item id={item.get('id')}: {exc}")
        if len(rows) >= max_items:
            break

    log(f"[DummyJSON] done success={ok} fail={fail} rows={len(rows)}")
    return rows
