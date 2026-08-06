"""
Pipeline Buổi 4:
1) merge + clean products -> products_final.csv
2) validate
3) sinh customers/orders/order_details/inventory_transactions
Chạy: python src/run_buoi4.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from generate_transactions import generate_all
from merge_products import merge_products
from validate_products import validate_products

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    lecturer = RAW / "products_lecturer.csv"
    crawled = RAW / "products_crawled.csv"
    final_path = PROCESSED / "products_final.csv"

    merge_report = merge_products(lecturer, crawled, final_path, seed=42)
    validation = validate_products(final_path)

    # lưu issues làm sạch
    clean_log = LOGS / "buoi4_cleaning_report.txt"
    lines = [
        "BAO CAO LAM SACH / GOP SAN PHAM - BUOI 4",
        f"lecturer_raw={merge_report['lecturer_raw']} clean={merge_report['lecturer_clean']}",
        f"crawled_raw={merge_report['crawled_raw']} clean={merge_report['crawled_clean']}",
        f"overlap_dropped={merge_report['overlap_dropped_crawl']}",
        f"final_count={merge_report['final_count']}",
        f"assigned_pairs={merge_report['assigned_pairs']}",
        f"by_source={merge_report['by_source']}",
        f"by_category={merge_report['by_category']}",
        "",
        "ISSUES / QUY TAC DA AP DUNG:",
    ]
    if merge_report["issues"]:
        lines.extend(f"- {x}" for x in merge_report["issues"])
    else:
        lines.append("- (none)")
    lines += [
        "",
        f"VALIDATION ok={validation['ok']}",
        f"validation_issues={validation['issues']}",
        f"price_range={validation['min_price']} .. {validation['max_price']}",
    ]
    clean_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    gen_rules = generate_all(
        products_path=final_path,
        out_dir=PROCESSED,
        seed=42,
        n_customers=220,
        n_orders=1200,
    )
    (REPORTS / "04_generation_rules.json").write_text(
        json.dumps(gen_rules, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # hồ sơ markdown
    md = f"""# Hồ sơ Buổi 4 — Làm sạch, gộp sản phẩm & sinh giao dịch

## 1. Products final

| Chỉ số | Giá trị |
|---|---|
| Lecturer raw / clean | {merge_report['lecturer_raw']} / {merge_report['lecturer_clean']} |
| Crawled raw / clean | {merge_report['crawled_raw']} / {merge_report['crawled_clean']} |
| **Final** | **{merge_report['final_count']}** (≥ 80) |
| Validate OK | {validation['ok']} |
| Nguồn | `{merge_report['by_source']}` |

File: `data/processed/products_final.csv`  
Log clean: `logs/buoi4_cleaning_report.txt`

## 2. Dữ liệu giao dịch (seed=42)

| Bảng | Số bản ghi | File |
|---|---|---|
| customers | {gen_rules['n_customers']} | `data/processed/customers.csv` |
| orders | {gen_rules['n_orders']} | `data/processed/orders.csv` |
| order_details | {gen_rules['n_order_details']} | `data/processed/order_details.csv` |
| inventory_transactions | {gen_rules['n_inventory_tx']} | `data/processed/inventory_transactions.csv` |

Kỳ đơn hàng: {gen_rules['order_period']}

### Quy tắc sinh (tóm tắt)

- Chọn SP theo `popularity_weight`
- ~55% khả năng thêm `paired_product_id`
- 70% bán đúng giá niêm yết; 30% giảm 1–10%
- Inventory: opening import + sale theo đơn + restock/adjust ngẫu nhiên
- **Dữ liệu tổng hợp phục vụ học tập, không phải doanh số thật**

Chi tiết: `reports/04_generation_rules.json`

## 3. Chạy lại

```bash
python src/run_buoi4.py
```

## 4. Tiếp theo — Buổi 5

Merge 5 bảng, Groupby/Pivot doanh thu theo tháng/danh mục/thành phố/kênh bán.
"""
    (REPORTS / "04_hoso_buoi_4.md").write_text(md, encoding="utf-8")

    print("=== BUOI 4 DONE ===")
    print(f"products_final: {merge_report['final_count']}")
    print(f"validate ok: {validation['ok']} issues={validation['issues']}")
    print(
        f"customers={gen_rules['n_customers']} orders={gen_rules['n_orders']} "
        f"details={gen_rules['n_order_details']} inventory={gen_rules['n_inventory_tx']}"
    )
    print(f"Report: {REPORTS / '04_hoso_buoi_4.md'}")


if __name__ == "__main__":
    main()
