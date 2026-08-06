"""
Buổi 5 — Merge 5 bảng + Groupby/Pivot báo cáo tổng hợp.
Chạy: python src/run_buoi5.py
"""
from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"
OUT_SUM = PROCESSED / "summaries"
OUT_FACT = PROCESSED / "fact_sales.csv"


def load_tables() -> dict[str, pd.DataFrame]:
    return {
        "products": pd.read_csv(PROCESSED / "products_final.csv"),
        "customers": pd.read_csv(PROCESSED / "customers.csv"),
        "orders": pd.read_csv(PROCESSED / "orders.csv"),
        "order_details": pd.read_csv(PROCESSED / "order_details.csv"),
        "inventory": pd.read_csv(PROCESSED / "inventory_transactions.csv"),
    }


def check_keys(tables: dict[str, pd.DataFrame]) -> list[str]:
    notes = []
    p, c, o, d, inv = (
        tables["products"],
        tables["customers"],
        tables["orders"],
        tables["order_details"],
        tables["inventory"],
    )

    notes.append(f"products PK unique: {p['product_id'].is_unique} n={len(p)}")
    notes.append(f"customers PK unique: {c['customer_id'].is_unique} n={len(c)}")
    notes.append(f"orders PK unique: {o['order_id'].is_unique} n={len(o)}")
    notes.append(
        "order_details dup keys (order_id,product_id): "
        f"{d.duplicated(['order_id','product_id']).sum()}"
    )
    notes.append(f"inventory PK unique: {inv['transaction_id'].is_unique} n={len(inv)}")

    # FK checks
    bad_order_cust = ~o["customer_id"].isin(c["customer_id"])
    bad_detail_order = ~d["order_id"].isin(o["order_id"])
    bad_detail_prod = ~d["product_id"].isin(p["product_id"])
    bad_inv_prod = ~inv["product_id"].isin(p["product_id"])
    notes.append(f"orders.customer_id missing FK: {bad_order_cust.sum()}")
    notes.append(f"order_details.order_id missing FK: {bad_detail_order.sum()}")
    notes.append(f"order_details.product_id missing FK: {bad_detail_prod.sum()}")
    notes.append(f"inventory.product_id missing FK: {bad_inv_prod.sum()}")
    return notes


def build_fact(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, list[str]]:
    """
    Merge chain:
    order_details -> orders -> customers
    order_details -> products
    """
    d = tables["order_details"].copy()
    o = tables["orders"].copy()
    c = tables["customers"].copy()
    p = tables["products"].copy()

    cardinality = []
    cardinality.append(f"order_details rows BEFORE: {len(d)}")

    m1 = d.merge(o, on="order_id", how="left", validate="many_to_one")
    cardinality.append(f"after +orders: {len(m1)} (delta={len(m1)-len(d)})")

    m2 = m1.merge(c, on="customer_id", how="left", validate="many_to_one")
    cardinality.append(f"after +customers: {len(m2)} (delta={len(m2)-len(m1)})")

    prod_cols = [
        "product_id",
        "product_name",
        "category",
        "brand",
        "unit",
        "unit_price",
        "reorder_level",
        "source_type",
    ]
    m3 = m2.merge(p[prod_cols], on="product_id", how="left", validate="many_to_one")
    cardinality.append(f"after +products: {len(m3)} (delta={len(m3)-len(m2)})")

    m3["order_date"] = pd.to_datetime(m3["order_date"])
    m3["year_month"] = m3["order_date"].dt.to_period("M").astype(str)
    m3["line_revenue"] = m3["quantity"] * m3["selling_price"]
    # phân bổ discount theo tỷ trọng line (đơn giản)
    order_sub = m3.groupby("order_id")["line_revenue"].transform("sum")
    m3["allocated_discount"] = m3["discount"].fillna(0) * (
        m3["line_revenue"] / order_sub.replace(0, pd.NA)
    ).fillna(0)
    m3["net_revenue"] = m3["line_revenue"] - m3["allocated_discount"]

    return m3, cardinality


def current_stock(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    inv = tables["inventory"].copy()
    inv["timestamp"] = pd.to_datetime(inv["timestamp"])
    inv = inv.sort_values(["product_id", "timestamp", "transaction_id"])

    def signed_qty(row: pd.Series) -> int:
        q = int(row["quantity"])
        t = row["transaction_type"]
        if t in {"import"}:
            return q
        if t in {"sale", "export"}:
            return -q
        if t == "adjust":
            # trong generator, adjust là shrinkage (giảm)
            return -q
        return 0

    inv["delta"] = inv.apply(signed_qty, axis=1)
    stock = (
        inv.groupby("product_id", as_index=False)["delta"]
        .sum()
        .rename(columns={"delta": "current_quantity"})
    )
    p = tables["products"][
        ["product_id", "product_name", "category", "reorder_level", "initial_quantity"]
    ]
    out = stock.merge(p, on="product_id", how="right")
    out["current_quantity"] = out["current_quantity"].fillna(0).astype(int)
    out["below_reorder"] = out["current_quantity"] <= out["reorder_level"]
    return out.sort_values("current_quantity")


def build_summaries(fact: pd.DataFrame, stock: pd.DataFrame) -> dict[str, pd.DataFrame]:
    summaries: dict[str, pd.DataFrame] = {}

    summaries["revenue_by_month"] = (
        fact.groupby("year_month", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            quantity=("quantity", "sum"),
            gross_revenue=("line_revenue", "sum"),
            net_revenue=("net_revenue", "sum"),
        )
        .sort_values("year_month")
    )

    summaries["revenue_by_category"] = (
        fact.groupby("category", as_index=False)
        .agg(
            quantity=("quantity", "sum"),
            net_revenue=("net_revenue", "sum"),
            n_products=("product_id", "nunique"),
        )
        .sort_values("net_revenue", ascending=False)
    )

    summaries["revenue_by_city"] = (
        fact.groupby("city", as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            orders=("order_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
        )
        .sort_values("net_revenue", ascending=False)
    )

    summaries["revenue_by_channel"] = (
        fact.groupby("sales_channel", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
            avg_order_value=("net_revenue", "mean"),
        )
        .sort_values("net_revenue", ascending=False)
    )

    # Pivot: tháng x kênh
    summaries["pivot_month_channel"] = (
        pd.pivot_table(
            fact,
            index="year_month",
            columns="sales_channel",
            values="net_revenue",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    # Pivot: danh mục x phương thức thanh toán
    summaries["pivot_category_payment"] = (
        pd.pivot_table(
            fact,
            index="category",
            columns="payment_method",
            values="net_revenue",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    summaries["top_products"] = (
        fact.groupby(["product_id", "product_name", "category"], as_index=False)
        .agg(quantity=("quantity", "sum"), net_revenue=("net_revenue", "sum"))
        .sort_values("net_revenue", ascending=False)
        .head(20)
    )

    summaries["stock_vs_reorder"] = stock.copy()
    summaries["low_stock_alert"] = stock[stock["below_reorder"]].copy()

    return summaries


def main() -> None:
    OUT_SUM.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    tables = load_tables()
    key_notes = check_keys(tables)
    fact, card_notes = build_fact(tables)
    stock = current_stock(tables)
    summaries = build_summaries(fact, stock)

    fact.to_csv(OUT_FACT, index=False, encoding="utf-8-sig")
    for name, df in summaries.items():
        df.to_csv(OUT_SUM / f"{name}.csv", index=False, encoding="utf-8-sig")

    # log cardinality
    log_lines = ["BUOI 5 - KIEM TRA KHOA & CARDINALITY", ""]
    log_lines += ["[KEYS]"] + [f"- {x}" for x in key_notes]
    log_lines += ["", "[MERGE CARDINALITY]"] + [f"- {x}" for x in card_notes]
    log_lines += [
        "",
        f"fact_sales rows: {len(fact)}",
        f"fact columns: {list(fact.columns)}",
        f"summaries written: {len(summaries)}",
    ]
    (LOGS / "buoi5_merge_checks.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    # insights ngắn
    top_cat = summaries["revenue_by_category"].iloc[0]
    top_channel = summaries["revenue_by_channel"].iloc[0]
    top_city = summaries["revenue_by_city"].iloc[0]
    best_month = summaries["revenue_by_month"].sort_values("net_revenue", ascending=False).iloc[0]
    n_low = int(summaries["low_stock_alert"].shape[0])

    md = f"""# Hồ sơ Buổi 5 — Merge / Groupby / Pivot

## 1. Kiểm tra khóa & cardinality

Xem chi tiết: `logs/buoi5_merge_checks.txt`

- Merge `order_details → orders → customers → products` **không phình dòng** bất thường
- Fact table: `data/processed/fact_sales.csv` (**{len(fact):,}** dòng)

## 2. Các bảng tổng hợp (≥ 5)

Thư mục: `data/processed/summaries/`

1. `revenue_by_month.csv`
2. `revenue_by_category.csv`
3. `revenue_by_city.csv`
4. `revenue_by_channel.csv`
5. `pivot_month_channel.csv`
6. `pivot_category_payment.csv`
7. `top_products.csv`
8. `stock_vs_reorder.csv` / `low_stock_alert.csv`

## 3. Phát hiện nhanh

| Chỉ số | Kết quả |
|---|---|
| Doanh thu ròng tổng | **{fact['net_revenue'].sum():,.0f}** VND |
| Danh mục doanh thu cao nhất | **{top_cat['category']}** ({top_cat['net_revenue']:,.0f}) |
| Kênh bán cao nhất | **{top_channel['sales_channel']}** ({top_channel['net_revenue']:,.0f}) |
| Thành phố cao nhất | **{top_city['city']}** ({top_city['net_revenue']:,.0f}) |
| Tháng cao nhất | **{best_month['year_month']}** ({best_month['net_revenue']:,.0f}) |
| SP dưới reorder | **{n_low}** |

## 4. Chạy lại

```bash
python src/run_buoi5.py
```

## 5. Tiếp theo — Buổi 6

EDA ≥ 8 biểu đồ + nhận xét (doanh thu, SP, KH, tồn kho, mùa vụ).
"""
    (REPORTS / "05_hoso_buoi_5.md").write_text(md, encoding="utf-8")

    print("=== BUOI 5 DONE ===")
    for x in key_notes:
        print("KEY:", x)
    for x in card_notes:
        print("CARD:", x)
    print(f"fact rows={len(fact):,}")
    print(f"summaries={list(summaries)}")
    print(f"low stock={n_low}")
    print(f"Report: {REPORTS / '05_hoso_buoi_5.md'}")


if __name__ == "__main__":
    main()
