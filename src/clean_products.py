"""
Làm sạch bảng sản phẩm (lecturer + crawled).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


PRODUCT_COLUMNS = [
    "product_id",
    "product_name",
    "category",
    "brand",
    "unit",
    "unit_price",
    "initial_quantity",
    "reorder_level",
    "popularity_weight",
    "paired_product_id",
    "source_type",
    "source_reference",
    "source_url",
    "collected_at",
    "simulated_fields",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _norm_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return default
    return float(str(value).replace(",", "").strip())


def _to_int(value: Any, default: int = 0) -> int:
    return int(round(_to_float(value, float(default))))


def clean_product_row(row: dict[str, str]) -> dict[str, Any]:
    cleaned = {
        "product_id": _norm_text(row.get("product_id")),
        "product_name": _norm_text(row.get("product_name")),
        "category": _norm_text(row.get("category")),
        "brand": _norm_text(row.get("brand")) or "Unknown",
        "unit": _norm_text(row.get("unit")) or "cái",
        "unit_price": _to_float(row.get("unit_price")),
        "initial_quantity": _to_int(row.get("initial_quantity")),
        "reorder_level": _to_int(row.get("reorder_level")),
        "popularity_weight": max(1.0, _to_float(row.get("popularity_weight"), 1.0)),
        "paired_product_id": _norm_text(row.get("paired_product_id")),
        "source_type": _norm_text(row.get("source_type")) or "unknown",
        "source_reference": _norm_text(row.get("source_reference")),
        "source_url": _norm_text(row.get("source_url")),
        "collected_at": _norm_text(row.get("collected_at")),
        "simulated_fields": _norm_text(row.get("simulated_fields")),
    }
    return cleaned


def clean_products(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    issues: list[str] = []
    cleaned_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for i, row in enumerate(rows, start=2):
        try:
            c = clean_product_row(row)
        except Exception as exc:  # noqa: BLE001
            issues.append(f"line {i}: parse error: {exc}")
            continue

        if not c["product_id"] or not c["product_name"]:
            issues.append(f"line {i}: missing product_id/name")
            continue
        if c["product_id"] in seen_ids:
            issues.append(f"line {i}: duplicate product_id {c['product_id']} (dropped)")
            continue
        if c["unit_price"] <= 0:
            issues.append(f"{c['product_id']}: unit_price <= 0 (dropped)")
            continue
        if c["initial_quantity"] < 0:
            issues.append(f"{c['product_id']}: negative stock -> set 0")
            c["initial_quantity"] = 0
        if c["reorder_level"] < 0:
            issues.append(f"{c['product_id']}: negative reorder -> set 0")
            c["reorder_level"] = 0
        if c["initial_quantity"] <= c["reorder_level"]:
            # sửa nhẹ để hợp lệ nghiệp vụ
            new_reorder = max(1, c["initial_quantity"] // 5) if c["initial_quantity"] > 0 else 0
            issues.append(
                f"{c['product_id']}: initial_quantity<=reorder_level "
                f"({c['initial_quantity']}<={c['reorder_level']}) -> reorder={new_reorder}"
            )
            c["reorder_level"] = new_reorder

        seen_ids.add(c["product_id"])
        cleaned_rows.append(c)

    return cleaned_rows, issues
