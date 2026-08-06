"""
Buổi 1: đọc và kiểm tra products_lecturer (CSV/Excel).
Chạy: python src/read_excel.py
"""
from __future__ import annotations

from pathlib import Path
import csv
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
LOG = ROOT / "logs" / "buoi1_kiem_tra_products.txt"


def load_products_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate(rows: list[dict]) -> dict:
    cols = list(rows[0].keys()) if rows else []
    missing = {
        c: sum(1 for r in rows if not str(r.get(c, "")).strip()) for c in cols
    }
    ids = [r["product_id"] for r in rows]
    idset = set(ids)
    return {
        "n_rows": len(rows),
        "n_cols": len(cols),
        "columns": cols,
        "categories": dict(Counter(r["category"] for r in rows)),
        "missing": {k: v for k, v in missing.items() if v},
        "duplicate_ids": len(ids) - len(idset),
        "bad_price": [
            r["product_id"] for r in rows if float(r["unit_price"]) <= 0
        ],
        "bad_stock": [
            r["product_id"]
            for r in rows
            if int(r["initial_quantity"]) <= int(r["reorder_level"])
        ],
        "bad_paired": [
            r["product_id"]
            for r in rows
            if r.get("paired_product_id")
            and r["paired_product_id"] not in idset
        ],
        "price_min": min(float(r["unit_price"]) for r in rows) if rows else None,
        "price_max": max(float(r["unit_price"]) for r in rows) if rows else None,
    }


def main() -> None:
    csv_path = RAW / "products_lecturer.csv"
    rows = load_products_csv(csv_path)
    report = validate(rows)

    print("=== PRODUCTS LECTURER ===")
    print(f"File: {csv_path}")
    print(f"Rows x Cols: {report['n_rows']} x {report['n_cols']}")
    print("Columns:", report["columns"])
    print("First 5 rows:")
    for r in rows[:5]:
        print(
            f"  {r['product_id']} | {r['product_name']} | "
            f"{r['category']} | {r['unit_price']}"
        )
    print("Categories:", report["categories"])
    print("Missing:", report["missing"] or "(none)")
    print("Duplicate IDs:", report["duplicate_ids"])
    print("Bad price:", report["bad_price"] or "(none)")
    print("Bad stock<=reorder:", report["bad_stock"] or "(none)")
    print("Bad paired FK:", report["bad_paired"] or "(none)")
    print(f"Price range: {report['price_min']} .. {report['price_max']}")
    print(f"Log file (manual summary): {LOG}")


if __name__ == "__main__":
    main()
