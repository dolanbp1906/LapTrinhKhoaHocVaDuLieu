"""
Buổi 3 — Thực hành crawl HTML mẫu (2 trang) và so sánh với products_lecturer.
Không tính là sản phẩm bổ sung.
Chạy: python src/crawl_practice_html.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
HTML_DIR = ROOT / "practice" / "html_sample"
RAW = ROOT / "data" / "raw"
LOGS = ROOT / "logs"
OUT_CSV = RAW / "products_from_html_practice.csv"
COMPARE_LOG = LOGS / "buoi3_so_sanh_html_excel.txt"


def parse_price_text(text: str, data_price: str | None) -> int:
    """Ưu tiên data-price; fallback parse '82.000 ₫' -> 82000."""
    if data_price is not None and str(data_price).strip() != "":
        return int(data_price)
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        raise ValueError(f"Không parse được giá: {text!r}")
    return int(digits)


def crawl_html_pages() -> list[dict]:
    rows: list[dict] = []
    files = sorted(HTML_DIR.glob("products_page_*.html"))
    if len(files) < 2:
        raise FileNotFoundError(f"Cần đủ 2 trang HTML trong {HTML_DIR}")

    for file in files:
        soup = BeautifulSoup(file.read_text(encoding="utf-8"), "html.parser")
        cards = soup.select(".product-card")
        for card in cards:
            price_el = card.select_one(".price")
            stock_el = card.select_one(".stock span")
            reorder_el = card.select_one(".reorder span")
            brand_el = card.select_one(".brand span")
            rows.append(
                {
                    "product_id": card.get("data-product-id", "").strip(),
                    "product_name": card.select_one(".product-name").get_text(strip=True),
                    "category": card.select_one(".category").get_text(strip=True),
                    "brand": brand_el.get_text(strip=True) if brand_el else "Unknown",
                    "unit_price": parse_price_text(
                        price_el.get_text(strip=True), price_el.get("data-price")
                    ),
                    "initial_quantity": int(stock_el.get_text(strip=True)),
                    "reorder_level": int(reorder_el.get_text(strip=True)),
                    "source_page": file.name,
                }
            )
    return rows


def load_lecturer() -> dict[str, dict]:
    path = RAW / "products_lecturer.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {r["product_id"]: r for r in csv.DictReader(f)}


def compare(html_rows: list[dict], lecturer: dict[str, dict]) -> str:
    html_ids = {r["product_id"] for r in html_rows}
    lec_ids = set(lecturer.keys())
    missing_in_html = sorted(lec_ids - html_ids)
    extra_in_html = sorted(html_ids - lec_ids)
    dup = [pid for pid in html_ids if sum(1 for r in html_rows if r["product_id"] == pid) > 1]

    field_diffs = []
    for r in html_rows:
        pid = r["product_id"]
        if pid not in lecturer:
            continue
        lec = lecturer[pid]
        for field in ["product_name", "category", "brand"]:
            if r[field] != lec.get(field, ""):
                field_diffs.append(f"{pid}.{field}: html={r[field]!r} excel={lec.get(field)!r}")
        if int(r["unit_price"]) != int(float(lec["unit_price"])):
            field_diffs.append(
                f"{pid}.unit_price: html={r['unit_price']} excel={lec['unit_price']}"
            )

    lines = [
        "SO SÁNH HTML MẪU vs products_lecturer",
        f"Số trang HTML: 2",
        f"Số SP từ HTML: {len(html_rows)}",
        f"Số SP Excel: {len(lecturer)}",
        f"Thiếu trong HTML: {missing_in_html or '(không)'}",
        f"Thừa trong HTML: {extra_in_html or '(không)'}",
        f"Trùng ID trong HTML: {dup or '(không)'}",
        f"Số lệch trường: {len(field_diffs)}",
    ]
    if field_diffs[:20]:
        lines.append("Một số lệch (tối đa 20):")
        lines.extend(f"  - {x}" for x in field_diffs[:20])
    lines.append(
        "Kết luận: HTML mẫu dùng để luyện kỹ thuật; KHÔNG tính là sản phẩm crawl bổ sung."
    )
    return "\n".join(lines) + "\n"


def save_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    rows = crawl_html_pages()
    save_csv(rows, OUT_CSV)
    report = compare(rows, load_lecturer())
    COMPARE_LOG.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved: {OUT_CSV}")
    print(f"Log: {COMPARE_LOG}")


if __name__ == "__main__":
    main()
