"""
Gộp products lecturer + crawled -> products_final.csv
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from clean_products import PRODUCT_COLUMNS, clean_products, read_csv, write_csv


def fix_paired_ids(rows: list[dict[str, Any]]) -> list[str]:
    ids = {r["product_id"] for r in rows}
    notes = []
    for r in rows:
        pid = r["paired_product_id"]
        if pid and pid not in ids:
            notes.append(f"{r['product_id']}: paired_product_id {pid} invalid -> cleared")
            r["paired_product_id"] = ""
    return notes


def assign_missing_pairs(rows: list[dict[str, Any]], rng) -> int:
    """Gán paired_product_id mô phỏng cho một phần SP crawl chưa có cặp."""
    by_cat: dict[str, list[str]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r["product_id"])

    assigned = 0
    for r in rows:
        if r["paired_product_id"]:
            continue
        if r["source_type"] == "lecturer_sample":
            continue
        candidates = [x for x in by_cat.get(r["category"], []) if x != r["product_id"]]
        if not candidates:
            continue
        if rng.random() < 0.45:
            r["paired_product_id"] = rng.choice(candidates)
            # đánh dấu mô phỏng
            sim = r.get("simulated_fields") or ""
            if "paired_product_id" not in sim:
                r["simulated_fields"] = (
                    (sim + "," if sim else "") + "paired_product_id(assigned_on_merge)"
                )
            assigned += 1
    return assigned


def merge_products(
    lecturer_path: Path,
    crawled_path: Path,
    out_path: Path,
    seed: int = 42,
) -> dict[str, Any]:
    import random

    rng = random.Random(seed)
    lec_raw = read_csv(lecturer_path)
    crawl_raw = read_csv(crawled_path)

    lec_clean, lec_issues = clean_products(lec_raw)
    crawl_clean, crawl_issues = clean_products(crawl_raw)

    # lecturer ưu tiên nếu trùng ID
    merged: dict[str, dict[str, Any]] = {}
    overlap = []
    for r in lec_clean:
        merged[r["product_id"]] = r
    for r in crawl_clean:
        if r["product_id"] in merged:
            overlap.append(r["product_id"])
            continue
        merged[r["product_id"]] = r

    rows = list(merged.values())
    pair_notes = fix_paired_ids(rows)
    n_assigned = assign_missing_pairs(rows, rng)
    pair_notes += fix_paired_ids(rows)

    rows.sort(key=lambda x: x["product_id"])
    write_csv(rows, out_path, PRODUCT_COLUMNS)

    report = {
        "lecturer_raw": len(lec_raw),
        "crawled_raw": len(crawl_raw),
        "lecturer_clean": len(lec_clean),
        "crawled_clean": len(crawl_clean),
        "overlap_dropped_crawl": overlap,
        "final_count": len(rows),
        "assigned_pairs": n_assigned,
        "issues": lec_issues + crawl_issues + pair_notes,
        "by_source": {},
        "by_category": {},
    }
    for r in rows:
        report["by_source"][r["source_type"]] = report["by_source"].get(r["source_type"], 0) + 1
        report["by_category"][r["category"]] = report["by_category"].get(r["category"], 0) + 1
    return report
