"""
Buổi 7 — Học máy có giám sát.
A) Dự đoán giá trị đơn hàng: Dummy / Linear / DecisionTree
B) Cảnh báo tồn kho thấp: Dummy / Logistic / DecisionTree
Yêu cầu: train/test split trước fit, Pipeline, không đánh giá trên train,
         phân tích >= 10 trường hợp sai.
Chạy: python src/run_buoi7_ml.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"


def build_order_dataset(fact: pd.DataFrame) -> pd.DataFrame:
    """Mỗi dòng = 1 đơn hàng."""
    g = fact.groupby("order_id").agg(
        order_value=("net_revenue", "sum"),
        n_items=("product_id", "nunique"),
        total_qty=("quantity", "sum"),
        avg_selling_price=("selling_price", "mean"),
        discount=("discount", "first"),
        payment_method=("payment_method", "first"),
        sales_channel=("sales_channel", "first"),
        city=("city", "first"),
        customer_type=("customer_type", "first"),
        order_date=("order_date", "first"),
    ).reset_index()
    g["order_date"] = pd.to_datetime(g["order_date"])
    g["month"] = g["order_date"].dt.month
    g["dow"] = g["order_date"].dt.dayofweek
    return g


def build_stock_dataset() -> pd.DataFrame:
    """
    Dự báo nguy cơ dưới reorder vào cuối kỳ từ đặc trưng đầu kỳ + bán nửa đầu năm.
    Tránh dùng sold_qty cả kỳ (rò rỉ nhãn).
    """
    stock = pd.read_csv(PROC / "summaries" / "stock_vs_reorder.csv")
    products = pd.read_csv(PROC / "products_final.csv")
    inv = pd.read_csv(PROC / "inventory_transactions.csv", parse_dates=["timestamp"])
    mid = pd.Timestamp("2025-06-30")

    early_sales = (
        inv[(inv["transaction_type"] == "sale") & (inv["timestamp"] <= mid)]
        .groupby("product_id")["quantity"]
        .sum()
    )
    early_import = (
        inv[(inv["transaction_type"] == "import") & (inv["timestamp"] <= mid)]
        .groupby("product_id")["quantity"]
        .sum()
    )

    df = stock.merge(
        products[
            [
                "product_id",
                "category",
                "unit_price",
                "popularity_weight",
                "source_type",
                "initial_quantity",
                "brand",
            ]
        ],
        on="product_id",
        how="left",
        suffixes=("", "_prod"),
    )
    # nếu merge tạo initial_quantity trùng, ưu tiên từ products
    if "initial_quantity_prod" in df.columns:
        df["initial_quantity"] = df["initial_quantity_prod"]
        df = df.drop(columns=["initial_quantity_prod"])

    df["early_sold_qty"] = df["product_id"].map(early_sales).fillna(0)
    df["early_import_qty"] = df["product_id"].map(early_import).fillna(0)
    df["early_sell_through"] = (
        df["early_sold_qty"] / df["initial_quantity"].replace(0, np.nan)
    ).fillna(0).clip(0, 10)
    df["reorder_ratio"] = (
        df["reorder_level"] / df["initial_quantity"].replace(0, np.nan)
    ).fillna(0)
    df["low_stock"] = df["below_reorder"].astype(int)
    return df


def regression_metrics(y_true, y_pred) -> dict:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def classification_metrics(y_true, y_pred) -> dict:
    return {
        "Accuracy": float(accuracy_score(y_true, y_pred)),
        "Precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "Recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "F1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def run_order_value_models(orders: pd.DataFrame) -> dict:
    target = "order_value"
    num_cols = ["n_items", "total_qty", "avg_selling_price", "discount", "month", "dow"]
    cat_cols = ["payment_method", "sales_channel", "city", "customer_type"]

    X = orders[num_cols + cat_cols]
    y = orders[target]

    X_train, X_test, y_train, y_test, id_train, id_test = train_test_split(
        X,
        y,
        orders["order_id"],
        test_size=0.25,
        random_state=42,
    )

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat_cols,
            ),
        ]
    )

    models = {
        "DummyRegressor": DummyRegressor(strategy="mean"),
        "LinearRegression": LinearRegression(),
        "DecisionTreeRegressor": DecisionTreeRegressor(
            max_depth=8, min_samples_leaf=10, random_state=42
        ),
    }

    results = {}
    preds = {}
    for name, model in models.items():
        pipe = Pipeline([("pre", pre), ("model", model)])
        pipe.fit(X_train, y_train)
        y_hat = pipe.predict(X_test)
        results[name] = regression_metrics(y_test, y_hat)
        preds[name] = y_hat

    # phân tích sai số trên model tốt nhất theo MAE (không lấy Dummy)
    ranked = sorted(
        ((k, v) for k, v in results.items() if k != "DummyRegressor"),
        key=lambda kv: kv[1]["MAE"],
    )
    best_name = ranked[0][0]
    err = pd.DataFrame(
        {
            "order_id": id_test.values,
            "y_true": y_test.values,
            "y_pred": preds[best_name],
        }
    )
    err["abs_error"] = (err["y_true"] - err["y_pred"]).abs()
    err["pct_error"] = err["abs_error"] / err["y_true"].replace(0, np.nan)
    # gắn thêm thông tin
    meta = orders.set_index("order_id")[
        ["sales_channel", "city", "customer_type", "n_items", "total_qty", "avg_selling_price"]
    ]
    err = err.join(meta, on="order_id")
    top_err = err.sort_values("abs_error", ascending=False).head(10)

    return {
        "task": "order_value_regression",
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "features_num": num_cols,
        "features_cat": cat_cols,
        "metrics": results,
        "best_model": best_name,
        "error_cases": top_err.to_dict(orient="records"),
        "error_table": top_err,
    }


def run_stock_alert_models(stock_df: pd.DataFrame) -> dict:
    target = "low_stock"
    num_cols = [
        "unit_price",
        "popularity_weight",
        "initial_quantity",
        "reorder_level",
        "reorder_ratio",
        "early_sold_qty",
        "early_import_qty",
        "early_sell_through",
    ]
    cat_cols = ["category", "source_type"]

    X = stock_df[num_cols + cat_cols]
    y = stock_df[target]

    # stratify nếu đủ lớp
    strat = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test, id_train, id_test = train_test_split(
        X,
        y,
        stock_df["product_id"],
        test_size=0.3,
        random_state=42,
        stratify=strat,
    )

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat_cols,
            ),
        ]
    )

    models = {
        "DummyClassifier": DummyClassifier(strategy="most_frequent"),
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "DecisionTreeClassifier": DecisionTreeClassifier(
            max_depth=5, min_samples_leaf=3, random_state=42
        ),
    }

    results = {}
    preds = {}
    for name, model in models.items():
        pipe = Pipeline([("pre", pre), ("model", model)])
        pipe.fit(X_train, y_train)
        y_hat = pipe.predict(X_test)
        results[name] = classification_metrics(y_test, y_hat)
        preds[name] = y_hat

    ranked = sorted(
        ((k, v) for k, v in results.items() if k != "DummyClassifier"),
        key=lambda kv: kv[1]["F1"],
        reverse=True,
    )
    best_name = ranked[0][0]

    err = pd.DataFrame(
        {
            "product_id": id_test.values,
            "y_true": y_test.values,
            "y_pred": preds[best_name],
        }
    )
    err["wrong"] = err["y_true"] != err["y_pred"]
    meta = stock_df.set_index("product_id")[
        [
            "product_name",
            "category",
            "current_quantity",
            "reorder_level",
            "early_sold_qty",
            "early_sell_through",
        ]
    ]
    err = err.join(meta, on="product_id")
    wrong = err[err["wrong"]].copy()
    # nếu ít hơn 10 case sai, lấy thêm biên gần ngưỡng
    if len(wrong) < 10:
        near = err.copy()
        near["margin"] = (near["current_quantity"] - near["reorder_level"]).abs()
        extra = near.sort_values("margin").head(10)
        cases = pd.concat([wrong, extra]).drop_duplicates("product_id").head(10)
    else:
        cases = wrong.head(10)

    return {
        "task": "low_stock_classification",
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "class_balance": y.value_counts().to_dict(),
        "features_num": num_cols,
        "features_cat": cat_cols,
        "metrics": results,
        "best_model": best_name,
        "error_cases": cases.to_dict(orient="records"),
        "error_table": cases,
        "n_wrong_on_test": int(err["wrong"].sum()),
    }


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    fact = pd.read_csv(PROC / "fact_sales.csv", parse_dates=["order_date"])
    orders = build_order_dataset(fact)
    stock_df = build_stock_dataset()

    reg = run_order_value_models(orders)
    clf = run_stock_alert_models(stock_df)

    # lưu bảng lỗi
    reg["error_table"].to_csv(
        REPORTS / "07_order_value_top10_errors.csv", index=False, encoding="utf-8-sig"
    )
    clf["error_table"].to_csv(
        REPORTS / "07_stock_alert_error_cases.csv", index=False, encoding="utf-8-sig"
    )

    # metrics json (không gồm dataframe)
    payload = {
        "order_value": {
            k: v
            for k, v in reg.items()
            if k not in {"error_table"}
        },
        "stock_alert": {
            k: v
            for k, v in clf.items()
            if k not in {"error_table"}
        },
        "notes": [
            "Train/test split trước khi học tham số (random_state=42).",
            "Dùng Pipeline + ColumnTransformer (scale + one-hot).",
            "Không báo cáo metric trên tập train.",
            "Dữ liệu giao dịch là synthetic; giới hạn triển khai thực tế.",
        ],
    }
    # convert numpy types in class_balance keys
    payload["stock_alert"]["class_balance"] = {
        str(k): int(v) for k, v in payload["stock_alert"]["class_balance"].items()
    }
    (REPORTS / "07_ml_metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # markdown report
    def fmt_reg(m: dict) -> str:
        rows = [
            "| Model | MAE | RMSE | R² |",
            "|---|---:|---:|---:|",
        ]
        for name, met in m.items():
            rows.append(
                f"| {name} | {met['MAE']:,.0f} | {met['RMSE']:,.0f} | {met['R2']:.4f} |"
            )
        return "\n".join(rows)

    def fmt_clf(m: dict) -> str:
        rows = [
            "| Model | Accuracy | Precision | Recall | F1 |",
            "|---|---:|---:|---:|---:|",
        ]
        for name, met in m.items():
            rows.append(
                f"| {name} | {met['Accuracy']:.3f} | {met['Precision']:.3f} | "
                f"{met['Recall']:.3f} | {met['F1']:.3f} |"
            )
        return "\n".join(rows)

    md = f"""# Hồ sơ Buổi 7 — Baseline & mô hình học máy

## A. Dự đoán giá trị đơn hàng (hồi quy)

- Train/test: **{reg['n_train']} / {reg['n_test']}**
- Features số: `{reg['features_num']}`
- Features categorical: `{reg['features_cat']}`
- Model tốt nhất (MAE): **{reg['best_model']}**

{fmt_reg(reg['metrics'])}

### 10 trường hợp sai số lớn nhất

File: `reports/07_order_value_top10_errors.csv`

Nhận xét: các đơn sai lớn thường có `avg_selling_price` rất cao (thiết bị) hoặc số lượng/item bất thường so với pattern phổ biến.

## B. Cảnh báo tồn kho thấp (phân lớp)

- Nhãn: `low_stock = current_quantity <= reorder_level`
- Train/test: **{clf['n_train']} / {clf['n_test']}**
- Cân bằng lớp (toàn bộ): `{clf['class_balance']}`
- Model tốt nhất (F1): **{clf['best_model']}**
- Số dự đoán sai trên test: **{clf['n_wrong_on_test']}**

{fmt_clf(clf['metrics'])}

### Trường hợp sai / biên quyết định

File: `reports/07_stock_alert_error_cases.csv`

## Giới hạn & rủi ro

- Dữ liệu đơn hàng/tồn kho là **mô phỏng** (seed=42), không phải giao dịch thật.
- Doanh thu bị chi phối bởi sản phẩm giá cao (DummyJSON) → metric hồi quy dễ bị outlier.
- Không nên triển khai tự động đặt hàng nếu chưa kiểm chứng trên dữ liệu thật.
- Có thể có rò rỉ nếu dùng sold_qty cả kỳ; bài tồn kho chỉ dùng đặc trưng đầu kỳ + bán nửa đầu năm 2025.
- Lớp `low_stock` mất cân bằng (~85% dương) nên ưu tiên Precision/Recall/F1 hơn Accuracy.

## Chạy lại

```bash
python src/run_buoi7_ml.py
```

## Tiếp theo — Buổi 8

RFM + K-Means, hoàn thiện báo cáo/slide, chạy lại pipeline end-to-end.
"""
    (REPORTS / "07_hoso_buoi_7.md").write_text(md, encoding="utf-8")

    print("=== BUOI 7 DONE ===")
    print("ORDER VALUE METRICS")
    for k, v in reg["metrics"].items():
        print(f"  {k}: {v}")
    print("Best:", reg["best_model"])
    print("STOCK ALERT METRICS")
    for k, v in clf["metrics"].items():
        print(f"  {k}: {v}")
    print("Best:", clf["best_model"], "wrong=", clf["n_wrong_on_test"])
    print(f"Report: {REPORTS / '07_hoso_buoi_7.md'}")


if __name__ == "__main__":
    main()
