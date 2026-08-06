"""
Validate products_final.csv
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from clean_products import read_csv


def validate_products(path: Path) -> dict[str, Any]:
    rows = read_csv(path)
    ids = [r["product_id"] for r in rows]
    idset = set(ids)
    issues = []

    if len(ids) != len(idset):
        issues.append(f"duplicate ids: {len(ids) - len(idset)}")

    bad_price = [r["product_id"] for r in rows if float(r["unit_price"]) <= 0]
    bad_stock = [
        r["product_id"]
        for r in rows
        if int(float(r["initial_quantity"])) < int(float(r["reorder_level"]))
    ]
    bad_pair = [
        r["product_id"]
        for r in rows
        if r.get("paired_product_id") and r["paired_product_id"] not in idset
    ]
    missing_name = [r["product_id"] for r in rows if not r.get("product_name")]

    if bad_price:
        issues.append(f"bad_price: {bad_price}")
    if bad_stock:
        issues.append(f"stock<=reorder: {bad_stock}")
    if bad_pair:
        issues.append(f"bad_paired: {bad_pair}")
    if missing_name:
        issues.append(f"missing_name: {missing_name}")

    return {
        "n_rows": len(rows),
        "n_cols": len(rows[0]) if rows else 0,
        "ok": len(issues) == 0 and len(rows) >= 80,
        "issues": issues,
        "min_price": min(float(r["unit_price"]) for r in rows) if rows else None,
        "max_price": max(float(r["unit_price"]) for r in rows) if rows else None,
    }
