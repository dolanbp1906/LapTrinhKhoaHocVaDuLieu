"""Minh chứng yêu cầu NumPy và dictionary lồng nhau của Chuyên đề 6."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def build_nested_transactions(fact: pd.DataFrame) -> dict[str, dict]:
    """Chuyển một mẫu giao dịch sang dictionary lồng nhau để phân tích."""
    sample = fact.sort_values(["order_date", "order_id"]).head(120)
    transactions: dict[str, dict] = {}
    for order_id, rows in sample.groupby("order_id", sort=False):
        first = rows.iloc[0]
        transactions[str(order_id)] = {
            "customer": {
                "customer_id": str(first["customer_id"]),
                "city": str(first["city"]),
                "customer_type": str(first["customer_type"]),
            },
            "order": {
                "order_date": str(first["order_date"]),
                "sales_channel": str(first["sales_channel"]),
                "discount": float(first["discount"]),
            },
            "items": [
                {
                    "product_id": str(row.product_id),
                    "quantity": int(row.quantity),
                    "selling_price": float(row.selling_price),
                    "line_revenue": float(row.net_revenue),
                }
                for row in rows.itertuples()
            ],
        }
    return transactions


def analyze_nested_transactions(transactions: dict[str, dict]) -> dict:
    customer_spend: dict[str, float] = {}
    product_pairs: dict[str, int] = {}
    total_revenue = 0.0

    for order in transactions.values():
        customer_id = order["customer"]["customer_id"]
        order_revenue = sum(item["line_revenue"] for item in order["items"])
        total_revenue += order_revenue
        customer_spend[customer_id] = customer_spend.get(customer_id, 0.0) + order_revenue

        product_ids = sorted({item["product_id"] for item in order["items"]})
        for i, left in enumerate(product_ids):
            for right in product_ids[i + 1 :]:
                key = f"{left}|{right}"
                product_pairs[key] = product_pairs.get(key, 0) + 1

    return {
        "sample_orders": len(transactions),
        "sample_revenue": total_revenue,
        "top_customer_spend": sorted(
            customer_spend.items(), key=lambda item: item[1], reverse=True
        )[:5],
        "top_product_pairs": sorted(
            product_pairs.items(), key=lambda item: item[1], reverse=True
        )[:10],
    }


def analyze_numpy(fact: pd.DataFrame, products: pd.DataFrame) -> dict:
    revenue_pivot = pd.pivot_table(
        fact,
        index="year_month",
        columns="category",
        values="net_revenue",
        aggfunc="sum",
        fill_value=0,
    )
    revenue_matrix = revenue_pivot.to_numpy(dtype=float)

    monthly_total = revenue_matrix.sum(axis=1)
    category_total = revenue_matrix.sum(axis=0)
    category_mean = revenue_matrix.mean(axis=0)
    category_std = revenue_matrix.std(axis=0)
    standardized = np.divide(
        revenue_matrix - category_mean,
        np.where(category_std == 0, 1, category_std),
    )

    stock_value = (
        products["initial_quantity"].to_numpy(dtype=float)
        * products["unit_price"].to_numpy(dtype=float)
    )

    matrix_path = PROCESSED / "summaries" / "numpy_revenue_matrix.csv"
    standardized_path = PROCESSED / "summaries" / "numpy_revenue_standardized.csv"
    revenue_pivot.to_csv(matrix_path, encoding="utf-8-sig")
    pd.DataFrame(
        standardized,
        index=revenue_pivot.index,
        columns=revenue_pivot.columns,
    ).to_csv(standardized_path, encoding="utf-8-sig")

    return {
        "matrix_shape": list(revenue_matrix.shape),
        "months": revenue_pivot.index.tolist(),
        "categories": revenue_pivot.columns.tolist(),
        "monthly_total_axis_1": monthly_total.tolist(),
        "category_total_axis_0": category_total.tolist(),
        "standardized_column_means": standardized.mean(axis=0).round(8).tolist(),
        "inventory_value_total": float(stock_value.sum()),
        "inventory_value_mean": float(stock_value.mean()),
        "matrix_file": str(matrix_path.relative_to(ROOT)),
        "standardized_file": str(standardized_path.relative_to(ROOT)),
    }


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "summaries").mkdir(parents=True, exist_ok=True)

    fact = pd.read_csv(PROCESSED / "fact_sales.csv")
    products = pd.read_csv(PROCESSED / "products_final.csv")
    nested = build_nested_transactions(fact)
    nested_result = analyze_nested_transactions(nested)
    numpy_result = analyze_numpy(fact, products)

    result = {
        "nested_dictionary_analysis": nested_result,
        "numpy_analysis": numpy_result,
    }
    json_path = REPORTS / "03_numpy_dictionary_evidence.json"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = f"""# Minh chứng NumPy và dictionary lồng nhau

## Dictionary lồng nhau

- Số đơn trong mẫu: **{nested_result['sample_orders']}**
- Doanh thu mẫu: **{nested_result['sample_revenue']:,.0f} VND**
- Đã tính chi tiêu khách hàng và tần suất cặp sản phẩm bằng vòng lặp trên cấu trúc
  `order → customer/order/items`.

## NumPy

- Ma trận doanh thu tháng × danh mục: **{tuple(numpy_result['matrix_shape'])}**
- `sum(axis=1)`: tổng doanh thu từng tháng.
- `sum(axis=0)`: tổng doanh thu từng danh mục.
- Chuẩn hóa z-score theo cột; trung bình sau chuẩn hóa xấp xỉ 0.
- Giá trị tồn kho đầu kỳ: **{numpy_result['inventory_value_total']:,.0f} VND**.

Đầu ra chi tiết: `reports/03_numpy_dictionary_evidence.json`.
"""
    (REPORTS / "03_numpy_dictionary_evidence.md").write_text(md, encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Revenue matrix shape: {tuple(numpy_result['matrix_shape'])}")


if __name__ == "__main__":
    main()
