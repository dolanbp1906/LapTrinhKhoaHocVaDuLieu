"""
Buổi 6 — EDA: tạo >= 8 biểu đồ có tiêu đề, nhãn trục và lưu figures.
Chạy: python src/run_buoi6_eda.py
"""
from __future__ import annotations

from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import plot_style

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
SUM = PROC / "summaries"
FIG = ROOT / "reports" / "figures"
REPORTS = ROOT / "reports"

plot_style.apply_style()


def load_data() -> dict[str, pd.DataFrame]:
    fact = pd.read_csv(PROC / "fact_sales.csv", parse_dates=["order_date"])
    stock = pd.read_csv(SUM / "stock_vs_reorder.csv")
    products = pd.read_csv(PROC / "products_final.csv")
    customers = pd.read_csv(PROC / "customers.csv")
    return {"fact": fact, "stock": stock, "products": products, "customers": customers}


def pair_matrix(fact: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    """Đếm đồng xuất hiện sản phẩm trong cùng đơn (top SP theo doanh thu)."""
    top_ids = (
        fact.groupby("product_id")["line_revenue"].sum().nlargest(top_n).index.tolist()
    )
    sub = fact[fact["product_id"].isin(top_ids)][["order_id", "product_id"]]
    # self-join cùng order
    merged = sub.merge(sub, on="order_id")
    merged = merged[merged["product_id_x"] < merged["product_id_y"]]
    mat = (
        merged.groupby(["product_id_x", "product_id_y"]).size().unstack(fill_value=0)
    )
    # làm vuông đủ top_ids
    mat = mat.reindex(index=top_ids, columns=top_ids, fill_value=0)
    # đối xứng
    mat = mat.add(mat.T, fill_value=0)
    arr = mat.to_numpy(copy=True)
    np.fill_diagonal(arr, 0)
    mat = pd.DataFrame(arr, index=mat.index, columns=mat.columns)
    return mat


def savefig(name: str) -> Path:
    FIG.mkdir(parents=True, exist_ok=True)
    path = FIG / name
    plt.tight_layout()
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    return path


def main() -> list[dict]:
    data = load_data()
    fact = data["fact"]
    stock = data["stock"]
    products = data["products"]
    findings: list[dict] = []

    # 1) Doanh thu theo tháng
    by_month = (
        fact.groupby(fact["order_date"].dt.to_period("M").astype(str))["net_revenue"]
        .sum()
        .reset_index()
        .rename(columns={"order_date": "year_month"})
    )
    plt.figure(figsize=(10, 4.5))
    sns.lineplot(
        data=by_month,
        x="year_month",
        y="net_revenue",
        marker="o",
        color=plot_style.PRIMARY,
        linewidth=2.2,
    )
    plt.xticks(rotation=45)
    plt.title("Biểu đồ 1 — Doanh thu ròng theo tháng")
    plt.xlabel("Tháng")
    plt.ylabel("Doanh thu ròng (VND)")
    p1 = savefig("01_revenue_by_month.png")
    peak = by_month.loc[by_month["net_revenue"].idxmax()]
    findings.append(
        {
            "chart": "01",
            "file": p1.name,
            "note": (
                f"Doanh thu biến động theo tháng; đỉnh {peak['year_month']} "
                f"({peak['net_revenue']:,.0f} VND)."
            ),
        }
    )

    # 2) Top danh mục
    by_cat = (
        fact.groupby("category")["net_revenue"].sum().sort_values(ascending=False).head(8)
    )
    plt.figure(figsize=(9, 4.5))
    sns.barplot(x=by_cat.values, y=by_cat.index, orient="h", color=plot_style.PRIMARY)
    plt.title("Biểu đồ 2 — Top danh mục theo doanh thu ròng")
    plt.xlabel("Doanh thu ròng (VND)")
    plt.ylabel("Danh mục")
    p2 = savefig("02_revenue_by_category.png")
    findings.append(
        {
            "chart": "02",
            "file": p2.name,
            "note": (
                f"Danh mục dẫn đầu: {by_cat.index[0]} "
                f"({by_cat.iloc[0]:,.0f} VND) — chịu ảnh hưởng giá thiết bị cao."
            ),
        }
    )

    # 3) Top SP bán chạy / bán chậm (theo số lượng)
    qty = (
        fact.groupby(["product_id", "product_name"])["quantity"].sum().sort_values(ascending=False)
    )
    top5 = qty.head(5)
    bottom5 = qty.tail(5)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].barh(top5.index.get_level_values(1), top5.values, color=plot_style.POSITIVE)
    axes[0].invert_yaxis()
    axes[0].set_title("Top 5 bán chạy (số lượng)")
    axes[0].set_xlabel("Số lượng")
    axes[1].barh(bottom5.index.get_level_values(1), bottom5.values, color=plot_style.DANGER)
    axes[1].invert_yaxis()
    axes[1].set_title("Top 5 bán chậm (số lượng)")
    axes[1].set_xlabel("Số lượng")
    fig.suptitle("Biểu đồ 3 — Sản phẩm bán chạy / bán chậm")
    p3 = savefig("03_top_slow_products.png")
    findings.append(
        {
            "chart": "03",
            "file": p3.name,
            "note": (
                f"Bán chạy nhất: {top5.index[0][1]} ({int(top5.iloc[0])} sp); "
                f"bán chậm nhất: {bottom5.index[0][1]} ({int(bottom5.iloc[0])} sp)."
            ),
        }
    )

    # 4) Doanh thu theo kênh
    by_ch = fact.groupby("sales_channel")["net_revenue"].sum().sort_values(ascending=False)
    plt.figure(figsize=(7, 4.5))
    sns.barplot(x=by_ch.index, y=by_ch.values, color=plot_style.PRIMARY)
    plt.title("Biểu đồ 4 — Doanh thu theo kênh bán")
    plt.xlabel("Kênh bán")
    plt.ylabel("Doanh thu ròng (VND)")
    p4 = savefig("04_revenue_by_channel.png")
    findings.append(
        {
            "chart": "04",
            "file": p4.name,
            "note": f"Kênh chiếm ưu thế: {by_ch.index[0]} ({by_ch.iloc[0]/by_ch.sum():.1%} tổng doanh thu).",
        }
    )

    # 5) Phân bố giá trị đơn
    order_value = fact.groupby("order_id")["net_revenue"].sum()
    plt.figure(figsize=(8, 4.5))
    sns.histplot(order_value, bins=40, kde=True, color=plot_style.PRIMARY)
    plt.title("Biểu đồ 5 — Phân bố giá trị đơn hàng")
    plt.xlabel("Giá trị đơn (VND)")
    plt.ylabel("Số đơn")
    p5 = savefig("05_order_value_dist.png")
    findings.append(
        {
            "chart": "05",
            "file": p5.name,
            "note": (
                f"Giá trị đơn lệch phải: median={order_value.median():,.0f}, "
                f"mean={order_value.mean():,.0f}, p95={order_value.quantile(0.95):,.0f}."
            ),
        }
    )

    # 6) Heatmap cặp SP mua cùng
    mat = pair_matrix(fact, top_n=10)
    plt.figure(figsize=(9, 7))
    sns.heatmap(mat, cmap=plot_style.SEQUENTIAL_CMAP, annot=False)
    plt.title("Biểu đồ 6 — Heatmap đồng mua (top 10 SP theo doanh thu)")
    plt.xlabel("product_id")
    plt.ylabel("product_id")
    p6 = savefig("06_pair_heatmap.png")
    # tìm cặp mạnh nhất
    mat_vals = mat.to_numpy(copy=True)
    np.fill_diagonal(mat_vals, -1)
    if mat_vals.max() > 0:
        i, j = np.unravel_index(mat_vals.argmax(), mat_vals.shape)
        pair_note = f"Cặp đồng mua mạnh nhất trong top: {mat.index[i]}–{mat.columns[j]} ({int(mat_vals[i, j])} lần)."
    else:
        pair_note = "Chưa thấy cặp đồng mua nổi bật trong top doanh thu."
    findings.append({"chart": "06", "file": p6.name, "note": pair_note})

    # 7) Tồn kho vs reorder
    plt.figure(figsize=(8, 5))
    colors = np.where(stock["below_reorder"], plot_style.DANGER, plot_style.POSITIVE)
    plt.scatter(stock["reorder_level"], stock["current_quantity"], c=colors, alpha=0.75)
    max_v = max(stock["reorder_level"].max(), stock["current_quantity"].max())
    plt.plot([0, max_v], [0, max_v], "--", color=plot_style.NEUTRAL, label="quantity = reorder")
    plt.title("Biểu đồ 7 — Tồn kho hiện tại vs mức cảnh báo")
    plt.xlabel("reorder_level")
    plt.ylabel("current_quantity")
    plt.legend()
    p7 = savefig("07_stock_vs_reorder.png")
    n_low = int(stock["below_reorder"].sum())
    findings.append(
        {
            "chart": "07",
            "file": p7.name,
            "note": f"{n_low}/{len(stock)} sản phẩm đang dưới hoặc bằng reorder_level (điểm đỏ).",
        }
    )

    # 8) RFM thô trước cluster — phân bố Monetary
    snapshot = fact["order_date"].max() + pd.Timedelta(days=1)
    rfm = fact.groupby("customer_id").agg(
        recency_days=("order_date", lambda s: (snapshot - s.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("net_revenue", "sum"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    sns.histplot(rfm["recency_days"], bins=25, ax=axes[0], color=plot_style.PRIMARY)
    axes[0].set_title("Recency (ngày)")
    sns.histplot(rfm["frequency"], bins=20, ax=axes[1], color=plot_style.ACCENT)
    axes[1].set_title("Frequency (số đơn)")
    sns.histplot(np.log1p(rfm["monetary"]), bins=25, ax=axes[2], color=plot_style.POSITIVE)
    axes[2].set_title("log1p(Monetary)")
    fig.suptitle("Biểu đồ 8 — Phân bố RFM thô (trước phân cụm)")
    p8 = savefig("08_rfm_raw_dist.png")
    findings.append(
        {
            "chart": "08",
            "file": p8.name,
            "note": (
                f"RFM: median R={rfm['recency_days'].median():.0f} ngày, "
                f"F={rfm['frequency'].median():.0f} đơn, "
                f"M={rfm['monetary'].median():,.0f} VND."
            ),
        }
    )

    # 9) (bonus) Doanh thu theo thành phố
    by_city = (
        fact.groupby("city")["net_revenue"].sum().sort_values(ascending=False).head(8)
    )
    plt.figure(figsize=(9, 4.5))
    sns.barplot(x=by_city.values, y=by_city.index, orient="h", color=plot_style.WARNING)
    plt.title("Biểu đồ 9 — Top thành phố theo doanh thu")
    plt.xlabel("Doanh thu ròng (VND)")
    plt.ylabel("Thành phố")
    p9 = savefig("09_revenue_by_city.png")
    findings.append(
        {
            "chart": "09",
            "file": p9.name,
            "note": f"Thành phố dẫn đầu: {by_city.index[0]} ({by_city.iloc[0]:,.0f} VND).",
        }
    )

    # 10) (bonus) Boxplot giá trị đơn theo kênh
    order_ch = (
        fact.groupby(["order_id", "sales_channel"])["net_revenue"].sum().reset_index()
    )
    plt.figure(figsize=(8, 4.5))
    sns.boxplot(
        data=order_ch,
        x="sales_channel",
        y="net_revenue",
        color=plot_style.PRIMARY,
    )
    plt.yscale("log")
    plt.title("Biểu đồ 10 — Phân bố giá trị đơn theo kênh (log scale)")
    plt.xlabel("Kênh bán")
    plt.ylabel("Giá trị đơn (VND, log)")
    p10 = savefig("10_order_value_by_channel.png")
    findings.append(
        {
            "chart": "10",
            "file": p10.name,
            "note": "Giá trị đơn khác biệt giữa kênh; có outlier lớn (thiết bị giá cao).",
        }
    )

    # lưu RFM thô cho buổi 8
    rfm_out = PROC / "rfm_raw.csv"
    rfm.reset_index().to_csv(rfm_out, index=False, encoding="utf-8-sig")

    # hồ sơ
    md_lines = [
        "# Hồ sơ Buổi 6 — EDA & trực quan hóa",
        "",
        f"- Số biểu đồ: **{len(findings)}** (≥ 8)",
        f"- Thư mục ảnh: `reports/figures/`",
        f"- RFM thô: `data/processed/rfm_raw.csv`",
        "",
        "## Nhận xét từng biểu đồ",
        "",
    ]
    for fnd in findings:
        md_lines.append(f"### Biểu đồ {fnd['chart']} — `{fnd['file']}`")
        md_lines.append(fnd["note"])
        md_lines.append("")

    md_lines += [
        "## ≥ 5 phát hiện tổng hợp",
        "",
        "1. Doanh thu theo tháng có biến động rõ; cần xem xét mùa vụ khi dự trữ kho.",
        "2. Thiết bị văn phòng (laptop/tablet) chiếm tỷ trọng doanh thu lớn do đơn giá cao.",
        "3. Kênh offline vẫn là nguồn doanh thu chính trong bộ dữ liệu mô phỏng.",
        "4. Phân bố giá trị đơn lệch phải — phù hợp bài toán dự đoán giá trị đơn.",
        "5. Nhiều sản phẩm dưới reorder_level — cần mô hình cảnh báo tồn kho.",
        "6. RFM thô cho thấy khách đa dạng về R/F/M, sẵn sàng cho K-Means Buổi 8.",
        "",
        "## Chạy lại",
        "",
        "```bash",
        "python src/run_buoi6_eda.py",
        "```",
        "",
        "## Tiếp theo — Buổi 7",
        "",
        "Baseline + ≥ 2 mô hình dự đoán giá trị đơn hàng / cảnh báo tồn kho + 10 case sai.",
    ]
    (REPORTS / "06_hoso_buoi_6.md").write_text("\n".join(md_lines), encoding="utf-8")

    print("=== BUOI 6 DONE ===")
    for fnd in findings:
        print(f"[{fnd['chart']}] {fnd['file']}: {fnd['note']}")
    print(f"Figures: {FIG}")
    print(f"Report: {REPORTS / '06_hoso_buoi_6.md'}")
    return findings


if __name__ == "__main__":
    main()
