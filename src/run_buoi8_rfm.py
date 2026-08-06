"""
Buổi 8 — RFM + K-Means phân nhóm khách hàng.
Chạy: python src/run_buoi8_rfm.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import plot_style
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"

REFERENCE_DATE = pd.Timestamp("2026-01-01")  # cố định, công bố rõ


SEGMENT_STRATEGY = {
    "Champions": {
        "desc": "Mua gần đây, thường xuyên, chi tiêu cao",
        "strategy": "Giữ chân VIP: ưu đãi độc quyền, early access, chăm sóc cá nhân hóa.",
    },
    "Loyal": {
        "desc": "Tần suất tốt, chi tiêu khá, recency ổn",
        "strategy": "Upsell/cross-sell, chương trình tích điểm, gợi ý sản phẩm cặp.",
    },
    "Potential": {
        "desc": "Chi tiêu hoặc tần suất tiềm năng, chưa ổn định",
        "strategy": "Nurture: coupon kích hoạt đơn tiếp theo, email gợi ý theo danh mục đã mua.",
    },
    "At Risk": {
        "desc": "Từng mua tốt nhưng lâu không quay lại",
        "strategy": "Win-back: mã giảm giá có hạn, khảo sát lý do rời bỏ, remarketing.",
    },
    "Hibernating": {
        "desc": "Recency kém, tần suất/chi tiêu thấp",
        "strategy": "Chi phí thấp: campaign định kỳ nhẹ; không đầu tư chăm sóc đắt.",
    },
}


def compute_rfm(fact: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame:
    rfm = (
        fact.groupby("customer_id")
        .agg(
            last_order=("order_date", "max"),
            frequency=("order_id", "nunique"),
            monetary=("net_revenue", "sum"),
        )
        .reset_index()
    )
    rfm["recency_days"] = (reference_date - rfm["last_order"]).dt.days
    # RFM score 1-5 (5 tốt hơn). Recency: thấp hơn = tốt hơn.
    rfm["R_score"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(
        int
    )
    rfm["M_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(
        int
    )
    rfm["RFM_score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]
    return rfm


def choose_k(X: np.ndarray, k_min: int = 3, k_max: int = 6) -> tuple[int, dict]:
    scores = {}
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        scores[k] = float(silhouette_score(X, labels))
    best_k = max(scores, key=scores.get)
    return best_k, scores


def label_segments(summary: pd.DataFrame) -> dict[int, str]:
    """Gán tên đoạn dựa trên trung bình R/F/M đã chuẩn hóa ngược ý nghĩa."""
    # summary index = cluster, columns include recency_days, frequency, monetary means
    # thấp recency + cao F/M => Champions
    s = summary.copy()
    s["r_rank"] = s["recency_days"].rank(ascending=True)  # thấp recency = rank tốt
    s["f_rank"] = s["frequency"].rank(ascending=False)
    s["m_rank"] = s["monetary"].rank(ascending=False)
    s["goodness"] = s["r_rank"] + s["f_rank"] + s["m_rank"]  # thấp hơn = tốt hơn
    order = s.sort_values("goodness").index.tolist()
    names = ["Champions", "Loyal", "Potential", "At Risk", "Hibernating"]
    mapping = {}
    for i, cid in enumerate(order):
        mapping[int(cid)] = names[i] if i < len(names) else f"Segment_{cid}"
    return mapping


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    fact = pd.read_csv(PROC / "fact_sales.csv", parse_dates=["order_date"])
    customers = pd.read_csv(PROC / "customers.csv")

    rfm = compute_rfm(fact, REFERENCE_DATE)
    rfm = rfm.merge(customers, on="customer_id", how="left")

    feats = rfm[["recency_days", "frequency", "monetary"]].copy()
    # log monetary để giảm ảnh hưởng outlier
    feats["monetary_log"] = np.log1p(feats["monetary"])
    X_raw = feats[["recency_days", "frequency", "monetary_log"]].to_numpy()
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    best_k, sil_scores = choose_k(X, 3, 6)
    # cố định k=4 hoặc 5 cho dễ diễn giải; ưu tiên best silhouette nhưng k trong {4,5}
    cand = {k: v for k, v in sil_scores.items() if k in (4, 5)}
    k = max(cand, key=cand.get) if cand else best_k

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    rfm["cluster"] = km.fit_predict(X)

    summary = (
        rfm.groupby("cluster")
        .agg(
            n_customers=("customer_id", "count"),
            recency_days=("recency_days", "mean"),
            frequency=("frequency", "mean"),
            monetary=("monetary", "mean"),
            RFM_score=("RFM_score", "mean"),
        )
        .round(2)
    )
    mapping = label_segments(summary)
    rfm["segment"] = rfm["cluster"].map(mapping)
    summary["segment"] = summary.index.map(mapping)
    summary = summary.reset_index().sort_values("monetary", ascending=False)

    # lưu
    rfm_out = PROC / "rfm_segments.csv"
    rfm.to_csv(rfm_out, index=False, encoding="utf-8-sig")
    summary.to_csv(REPORTS / "08_rfm_segment_summary.csv", index=False, encoding="utf-8-sig")

    # biểu đồ
    plot_style.apply_style()
    plt.figure(figsize=(8, 5))
    sns.scatterplot(
        data=rfm,
        x="recency_days",
        y="monetary",
        hue="segment",
        size="frequency",
        sizes=(30, 180),
        alpha=0.75,
    )
    plt.yscale("log")
    plt.title("RFM clusters — Recency vs Monetary (log)")
    plt.xlabel(f"Recency (days) | reference_date={REFERENCE_DATE.date()}")
    plt.ylabel("Monetary (VND, log)")
    plt.tight_layout()
    plt.savefig(FIG / "11_rfm_clusters.png", dpi=140, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(7, 4))
    order = summary.sort_values("n_customers", ascending=False)["segment"]
    sns.barplot(data=summary, x="segment", y="n_customers", order=order, color=plot_style.PRIMARY)
    plt.title("Số khách theo nhóm RFM/K-Means")
    plt.ylabel("Số khách hàng")
    plt.xlabel("Nhóm")
    plt.tight_layout()
    plt.savefig(FIG / "12_rfm_segment_counts.png", dpi=140, bbox_inches="tight")
    plt.close()

    # chiến lược
    strategies = []
    for _, row in summary.iterrows():
        name = row["segment"]
        info = SEGMENT_STRATEGY.get(
            name, {"desc": "Nhóm trung gian", "strategy": "Theo dõi thêm."}
        )
        strategies.append(
            {
                "segment": name,
                "cluster": int(row["cluster"]),
                "n_customers": int(row["n_customers"]),
                "avg_recency": float(row["recency_days"]),
                "avg_frequency": float(row["frequency"]),
                "avg_monetary": float(row["monetary"]),
                "description": info["desc"],
                "strategy": info["strategy"],
            }
        )

    meta = {
        "reference_date": str(REFERENCE_DATE.date()),
        "k": k,
        "silhouette_scores": sil_scores,
        "features": ["recency_days", "frequency", "log1p(monetary)"],
        "scaler": "StandardScaler",
        "random_state": 42,
        "segments": strategies,
    }
    (REPORTS / "08_rfm_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md_lines = [
        "# Hồ sơ Buổi 8 — RFM & K-Means",
        "",
        f"- Ngày tham chiếu cố định: **{REFERENCE_DATE.date()}**",
        f"- Số cụm K-Means: **k={k}** (silhouette: {sil_scores})",
        f"- File phân nhóm: `data/processed/rfm_segments.csv`",
        f"- Biểu đồ: `reports/figures/11_rfm_clusters.png`, `12_rfm_segment_counts.png`",
        "",
        "## Tóm tắt nhóm",
        "",
        "| Segment | n | Recency TB | Frequency TB | Monetary TB | Chiến lược |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for s in strategies:
        md_lines.append(
            f"| {s['segment']} | {s['n_customers']} | {s['avg_recency']:.1f} | "
            f"{s['avg_frequency']:.1f} | {s['avg_monetary']:,.0f} | {s['strategy']} |"
        )
    md_lines += [
        "",
        "## Chạy lại",
        "",
        "```bash",
        "python src/run_buoi8_rfm.py",
        "```",
    ]
    (REPORTS / "08_hoso_buoi_8.md").write_text("\n".join(md_lines), encoding="utf-8")

    print("=== BUOI 8 RFM DONE ===")
    print("reference_date=", REFERENCE_DATE.date(), "k=", k, "silhouette=", sil_scores)
    print(summary.to_string(index=False))
    print(f"Saved: {rfm_out}")


if __name__ == "__main__":
    main()
