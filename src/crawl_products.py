"""
Buổi 3 — Orchestrator crawl sản phẩm bổ sung.
Gộp DummyJSON + Books to Scrape -> data/raw/products_crawled.csv
Chạy: python src/crawl_products.py
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crawl_books_toscrape import crawl_books
from crawl_dummyjson import crawl_dummyjson

RAW = ROOT / "data" / "raw"
LOGS = ROOT / "logs"
OUT = RAW / "products_crawled.csv"
CRAWL_LOG = LOGS / "crawl_log.txt"
ERROR_LOG = LOGS / "error_log.txt"


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


def save_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # union keys để không mất cột nguồn
    fieldnames: list[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    stamp = datetime.now().isoformat(timespec="seconds")
    append_log(CRAWL_LOG, f"===== CRAWL START {stamp} =====")

    def log_fn(msg: str) -> None:
        print(msg)
        append_log(CRAWL_LOG, msg)
        if "[ERROR]" in msg:
            append_log(ERROR_LOG, f"[{stamp}] {msg}")

    # DummyJSON: P0061.. (15 SP)
    dummy_rows = crawl_dummyjson(start_id=61, max_items=15, log_fn=log_fn)
    # Books: tiếp nối ID
    next_id = 61 + len(dummy_rows)
    book_rows = crawl_books(start_id=next_id, max_items=15, log_fn=log_fn)

    all_rows = dummy_rows + book_rows
    save_csv(all_rows, OUT)

    # tóm tắt
    by_source = {}
    for r in all_rows:
        by_source[r["source_type"]] = by_source.get(r["source_type"], 0) + 1

    summary = [
        f"===== CRAWL SUMMARY {datetime.now().isoformat(timespec='seconds')} =====",
        f"Total crawled products: {len(all_rows)}",
        f"DummyJSON rows: {len(dummy_rows)}",
        f"Books rows: {len(book_rows)}",
        f"By source_type: {by_source}",
        f"Output: {OUT}",
        f"ID range: {all_rows[0]['product_id'] if all_rows else '-'} .. {all_rows[-1]['product_id'] if all_rows else '-'}",
        "NOTE: HTML practice products are NOT included here.",
        "NOTE: simulated_fields are documented per row.",
    ]
    for line in summary:
        log_fn(line)

    print(f"\nSaved {len(all_rows)} products -> {OUT}")
    if len(all_rows) < 20:
        print("WARNING: chưa đủ 20 sản phẩm bổ sung!")
    else:
        print("OK: đã đủ >= 20 sản phẩm crawl bổ sung.")


if __name__ == "__main__":
    main()
