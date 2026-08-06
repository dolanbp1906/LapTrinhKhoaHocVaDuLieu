"""
Buổi 3 — Crawl bổ sung từ Books to Scrape (sandbox).
URL: https://books.toscrape.com/
"""
from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
GBP_TO_VND = 33_000  # tỷ giá công bố để chuẩn hóa tiền tệ


def parse_price_gbp(text: str) -> float:
    # £51.77
    m = re.search(r"([\d.]+)", text.replace(",", ""))
    if not m:
        raise ValueError(f"Không parse được giá: {text!r}")
    return float(m.group(1))


def simulate_inventory(seed: int) -> tuple[int, int]:
    initial = 30 + (seed * 11) % 100
    reorder = max(5, initial // 4)
    return initial, reorder


def fetch_page(url: str, timeout: int = 20) -> BeautifulSoup:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_books_on_page(soup: BeautifulSoup, page_url: str) -> list[dict]:
    books = []
    for art in soup.select("article.product_pod"):
        a = art.select_one("h3 a")
        price_el = art.select_one("p.price_color")
        avail_el = art.select_one("p.instock.availability")
        rel = a.get("href", "")
        abs_url = urljoin(page_url, rel)
        name = a.get("title") or a.get_text(strip=True)
        price_gbp = parse_price_gbp(price_el.get_text(strip=True))
        in_stock = "In stock" in (avail_el.get_text(" ", strip=True) if avail_el else "")
        books.append(
            {
                "product_name": name.strip(),
                "price_gbp": price_gbp,
                "in_stock": in_stock,
                "source_url": abs_url,
            }
        )
    return books


def next_page_url(soup: BeautifulSoup, current_url: str) -> str | None:
    nxt = soup.select_one("li.next a")
    if not nxt:
        return None
    return urljoin(current_url, nxt.get("href"))


def to_product_row(raw: dict, product_id: str, idx: int, collected_at: str) -> dict:
    initial_qty, reorder = simulate_inventory(idx)
    price_vnd = int(round(raw["price_gbp"] * GBP_TO_VND))
    return {
        "product_id": product_id,
        "product_name": raw["product_name"],
        "category": "Sách",
        "brand": "Unknown",
        "unit": "quyển",
        "unit_price": price_vnd,
        "initial_quantity": initial_qty,
        "reorder_level": reorder,
        "popularity_weight": 1 + (idx % 10),
        "paired_product_id": "",
        "source_type": "public_website",
        "source_reference": BASE_URL,
        "source_url": raw["source_url"],
        "collected_at": collected_at,
        "raw_category": "Books",
        "raw_price_gbp": raw["price_gbp"],
        "fx_gbp_vnd": GBP_TO_VND,
        "simulated_fields": "initial_quantity,reorder_level,popularity_weight,paired_product_id,product_id,brand,unit_price(fx)",
    }


def crawl_books(
    start_id: int = 76,
    max_items: int = 15,
    sleep_s: float = 1.5,
    log_fn: Callable[[str], None] | None = None,
) -> list[dict]:
    log = log_fn or (lambda m: None)
    collected_at = datetime.now().isoformat(timespec="seconds")
    rows: list[dict] = []
    url = BASE_URL
    page_no = 0
    next_id = start_id
    ok, fail = 0, 0

    while url and len(rows) < max_items:
        page_no += 1
        try:
            log(f"[Books] GET page={page_no} url={url}")
            soup = fetch_page(url)
            books = parse_books_on_page(soup, url)
            log(f"[Books] page={page_no} parsed={len(books)}")
            time.sleep(sleep_s)
        except Exception as exc:  # noqa: BLE001
            fail += 1
            log(f"[Books][ERROR] page={page_no}: {exc}")
            break

        for raw in books:
            if len(rows) >= max_items:
                break
            try:
                pid = f"P{next_id:04d}"
                rows.append(to_product_row(raw, pid, next_id, collected_at))
                next_id += 1
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                log(f"[Books][ERROR] book={raw.get('product_name')}: {exc}")

        url = next_page_url(soup, url) if len(rows) < max_items else None

    log(f"[Books] done success={ok} fail={fail} rows={len(rows)}")
    return rows
