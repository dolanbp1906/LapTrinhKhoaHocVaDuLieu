"""
Hệ thống Chuyên đề 6 — nghiệp vụ kho + bán hàng + phân tích + RFM + dự đoán.
Khớp bối cảnh đề bài:
  • Nhập / xuất / điều chỉnh tồn kho có nhật ký, chặn âm kho
  • Phân tích doanh thu, SP bán chạy, cặp mua cùng nhau
  • Phân nhóm khách hàng RFM
  • Dự đoán giá trị đơn / cảnh báo tồn kho

Chạy:
    python -m streamlit run src/app_dashboard.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from inventory_manager import InventoryError, InventoryManager
from models import Customer
from sales_manager import SalesManager

PROC = ROOT / "data" / "processed"
SUM = PROC / "summaries"
FIG = ROOT / "reports" / "figures"
REP = ROOT / "reports"
UI_LOG = ROOT / "logs" / "ui_runtime"
UI_STOCK = PROC / "products_ui_live.csv"

st.set_page_config(
    page_title="Hệ thống bán hàng & kho — Chuyên đề 6",
    layout="wide",
    initial_sidebar_state="expanded",
)


def fmt_vnd(x: float) -> str:
    return f"{float(x):,.0f} ₫"


@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def products_table(inv: InventoryManager) -> pd.DataFrame:
    rows = []
    for p in inv.products.values():
        d = p.to_dict()
        d["below_reorder"] = p.is_below_reorder()
        rows.append(d)
    return pd.DataFrame(rows).sort_values("product_id")


def init_business_layer() -> None:
    """Khởi tạo InventoryManager + SalesManager trong session (nghiệp vụ sống)."""
    if "inv" in st.session_state and "sales" in st.session_state:
        return

    UI_LOG.mkdir(parents=True, exist_ok=True)
    inv = InventoryManager(log_dir=UI_LOG, performed_by="ui_user")
    # ưu tiên trạng thái live nếu đã thao tác trước đó
    src = UI_STOCK if UI_STOCK.exists() else (PROC / "products_final.csv")
    inv.load_products_from_csv(src)
    # đồng bộ counter log nếu file đã có giao dịch
    log_path = UI_LOG / "inventory_log.csv"
    if log_path.exists():
        try:
            n = max(0, len(pd.read_csv(log_path)) - 0)
            # đếm dòng dữ liệu
            n = sum(1 for _ in open(log_path, encoding="utf-8-sig")) - 1
            inv._tx_counter = max(0, n)
        except Exception:
            pass

    sales = SalesManager(inv)
    # nạp vài khách mẫu từ customers.csv
    cust_path = PROC / "customers.csv"
    if cust_path.exists():
        cdf = pd.read_csv(cust_path).head(30)
        for _, r in cdf.iterrows():
            sales.add_customer(
                Customer(
                    customer_id=str(r["customer_id"]),
                    city=str(r["city"]),
                    customer_type=str(r["customer_type"]),
                    join_date=str(r["join_date"]),
                )
            )
    st.session_state.inv = inv
    st.session_state.sales = sales
    st.session_state.last_message = None


def persist_stock() -> None:
    st.session_state.inv.save_products_to_csv(UI_STOCK)


def product_options(inv: InventoryManager) -> list[str]:
    return [
        f"{p.product_id} | {p.product_name} (tồn {p.quantity})"
        for p in sorted(inv.products.values(), key=lambda x: x.product_id)
    ]


def parse_pid(label: str) -> str:
    return label.split("|", 1)[0].strip()


def pair_top(fact: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    top_ids = (
        fact.groupby("product_id")["line_revenue"].sum().nlargest(top_n).index.tolist()
    )
    sub = fact[fact["product_id"].isin(top_ids)][["order_id", "product_id", "product_name"]]
    names = sub.drop_duplicates("product_id").set_index("product_id")["product_name"]
    m = sub.merge(sub, on="order_id")
    m = m[m["product_id_x"] < m["product_id_y"]]
    pair = (
        m.groupby(["product_id_x", "product_id_y"])
        .size()
        .reset_index(name="co_purchase_count")
        .sort_values("co_purchase_count", ascending=False)
    )
    pair["product_x"] = pair["product_id_x"].map(names)
    pair["product_y"] = pair["product_id_y"].map(names)
    return pair.head(20)


@st.cache_resource
def fit_ml_models():
    """Huấn luyện model nhẹ để dự đoán tương tác trên UI."""
    fact = pd.read_csv(PROC / "fact_sales.csv", parse_dates=["order_date"])
    orders = (
        fact.groupby("order_id")
        .agg(
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
        )
        .reset_index()
    )
    orders["month"] = pd.to_datetime(orders["order_date"]).dt.month
    orders["dow"] = pd.to_datetime(orders["order_date"]).dt.dayofweek

    num_r = ["n_items", "total_qty", "avg_selling_price", "discount", "month", "dow"]
    cat_r = ["payment_method", "sales_channel", "city", "customer_type"]
    pre_r = ColumnTransformer(
        [
            ("num", StandardScaler(), num_r),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_r),
        ]
    )
    reg = Pipeline(
        [
            ("pre", pre_r),
            ("model", DecisionTreeRegressor(max_depth=8, min_samples_leaf=10, random_state=42)),
        ]
    )
    reg.fit(orders[num_r + cat_r], orders["order_value"])

    stock = pd.read_csv(SUM / "stock_vs_reorder.csv")
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
    sdf = stock.merge(
        products[
            [
                "product_id",
                "category",
                "unit_price",
                "popularity_weight",
                "source_type",
                "initial_quantity",
            ]
        ],
        on="product_id",
        how="left",
        suffixes=("", "_p"),
    )
    if "initial_quantity_p" in sdf.columns:
        sdf["initial_quantity"] = sdf["initial_quantity_p"]
    sdf["early_sold_qty"] = sdf["product_id"].map(early_sales).fillna(0)
    sdf["early_import_qty"] = sdf["product_id"].map(early_import).fillna(0)
    sdf["early_sell_through"] = (
        sdf["early_sold_qty"] / sdf["initial_quantity"].replace(0, np.nan)
    ).fillna(0).clip(0, 10)
    sdf["reorder_ratio"] = (
        sdf["reorder_level"] / sdf["initial_quantity"].replace(0, np.nan)
    ).fillna(0)
    sdf["low_stock"] = sdf["below_reorder"].astype(int)

    num_c = [
        "unit_price",
        "popularity_weight",
        "initial_quantity",
        "reorder_level",
        "reorder_ratio",
        "early_sold_qty",
        "early_import_qty",
        "early_sell_through",
    ]
    cat_c = ["category", "source_type"]
    pre_c = ColumnTransformer(
        [
            ("num", StandardScaler(), num_c),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_c),
        ]
    )
    clf = Pipeline(
        [
            ("pre", pre_c),
            (
                "model",
                DecisionTreeClassifier(max_depth=5, min_samples_leaf=3, random_state=42),
            ),
        ]
    )
    clf.fit(sdf[num_c + cat_c], sdf["low_stock"])

    return {
        "reg": reg,
        "reg_cols": num_r + cat_r,
        "clf": clf,
        "clf_cols": num_c + cat_c,
        "stock_features": sdf,
        "orders_ref": orders,
    }


# -------------------- UI shell --------------------
NAV_ITEMS = [
    ("overview", "01", "Tổng quan", "Vận hành cửa hàng"),
    ("warehouse", "02", "Nghiệp vụ kho", "Nhập · xuất · điều chỉnh"),
    ("sales", "03", "Bán hàng", "Tạo đơn & trừ kho"),
    ("analytics", "04", "Phân tích", "Doanh thu & cặp SP"),
    ("rfm", "05", "Khách hàng RFM", "Phân nhóm & chiến lược"),
    ("ml", "06", "Dự đoán ML", "Giá trị đơn · cảnh báo"),
    ("logs", "07", "Nhật ký", "Inventory & error log"),
]

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "overview"

st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: "Source Sans 3", "Segoe UI", sans-serif;
  }

  /* Giữ menu Settings góc phải của Streamlit */
  #MainMenu, header, [data-testid="stToolbar"], [data-testid="stHeader"] {
    visibility: visible !important;
  }
  [data-testid="stToolbar"] { z-index: 999999 !important; }

  .stApp {
    background:
      radial-gradient(1100px 420px at 8% -8%, color-mix(in srgb, #14b8a6 16%, transparent), transparent 55%),
      radial-gradient(900px 380px at 100% 0%, color-mix(in srgb, #3b82f6 10%, transparent), transparent 50%),
      var(--background-color);
  }
  .block-container {
    padding-top: 1.4rem;
    max-width: 1200px;
    color: var(--text-color);
  }

  [data-testid="stSidebar"] {
    background: linear-gradient(185deg, #0b1f33 0%, #14344d 48%, #0f766e 160%) !important;
    border-right: 1px solid rgba(255,255,255,0.08);
  }
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] .stMarkdown span,
  [data-testid="stSidebar"] label { color: #cbd5e1 !important; }
  [data-testid="stSidebar"] .stButton > button {
    width: 100%; text-align: left !important; justify-content: flex-start !important;
    display: inline-flex !important; align-items: center !important;
    border: 1px solid transparent; background: transparent; color: #e2e8f0 !important;
    padding: 0.7rem 0.85rem; border-radius: 12px; margin-bottom: 0.35rem;
    box-shadow: none; transition: all .18s ease; font-weight: 600;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.12); transform: translateX(2px);
  }
  [data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, rgba(15,118,110,0.95), rgba(20,184,166,0.75));
    border: 1px solid rgba(255,255,255,0.18); box-shadow: 0 8px 20px rgba(0,0,0,0.22); color: #fff !important;
  }
  [data-testid="stSidebar"] .stButton > button p,
  [data-testid="stSidebar"] .stButton > button div,
  [data-testid="stSidebar"] .stButton > button span {
    text-align: left !important; justify-content: flex-start !important; margin: 0 !important; width: 100%; color: inherit !important;
  }
  [data-testid="stSidebar"] .stButton { text-align: left !important; }

  .brand-card {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px; padding: 1rem; margin-bottom: 1rem; text-align: left !important;
  }
  .brand-mark {
    display: inline-flex; align-items: center; justify-content: center;
    width: 38px; height: 38px; border-radius: 11px; background: #14b8a6; color: #042f2e !important;
    font-family: Fraunces, Georgia, serif; font-weight: 700; margin-bottom: 0.65rem;
  }
  .brand-title {
    font-family: Fraunces, Georgia, serif; font-size: 1.15rem; font-weight: 700;
    color: #fff !important; margin: 0; text-align: left !important;
  }
  .brand-sub { margin: 0.25rem 0 0; font-size: 0.82rem; color: #94a3b8 !important; text-align: left !important; }
  .nav-label {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em;
    color: #94a3b8 !important; margin: 0.4rem 0 0.55rem 0; padding-left: 0.15rem;
    font-weight: 600; text-align: left !important;
  }
  .side-kpi { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin: 0.85rem 0 0.6rem; }
  .side-kpi .cell {
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px; padding: 0.55rem 0.65rem;
  }
  .side-kpi .k { font-size: 0.7rem; color: #94a3b8 !important; }
  .side-kpi .v { font-size: 1.05rem; font-weight: 700; color: #fff !important; }

  .hero {
    background: linear-gradient(120deg, #102a43 0%, #1f4e5f 55%, #0f766e 120%);
    border-radius: 22px; padding: 1.35rem 1.5rem; margin-bottom: 1.1rem;
    box-shadow: 0 18px 40px rgba(16,42,67,0.18); position: relative; overflow: hidden;
  }
  .hero::after {
    content: ""; position: absolute; right: -40px; top: -50px;
    width: 220px; height: 220px; border-radius: 50%; background: rgba(255,255,255,0.07);
  }
  .hero h1 {
    font-family: Fraunces, Georgia, serif; font-size: 1.85rem; margin: 0 0 0.35rem;
    font-weight: 700; color: #ffffff !important;
  }
  .hero p { margin: 0; color: #d9e8ef !important; font-size: 0.98rem; }
  .hero .chip {
    display: inline-block; margin-top: 0.75rem; background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.18); border-radius: 999px; padding: 0.25rem 0.7rem;
    font-size: 0.78rem; color: #ecfeff !important;
  }

  div[data-testid="stMetric"] {
    background: var(--secondary-background-color) !important;
    border: 1px solid color-mix(in srgb, var(--text-color) 12%, transparent);
    border-radius: 16px; padding: 0.85rem 1rem;
  }
  div[data-testid="stMetricValue"] { font-size: 1.35rem; color: var(--text-color) !important; }
  div[data-testid="stMetricLabel"],
  div[data-testid="stMetricDelta"] { color: var(--text-color) !important; opacity: 0.72; }
  .section-title {
    font-family: Fraunces, Georgia, serif; font-size: 1.35rem;
    color: var(--text-color) !important; margin: 0.2rem 0 0.35rem;
  }
  .section-sub { color: var(--text-color) !important; opacity: 0.75; margin-bottom: 1rem; }

  .ok-box, .err-box, .info-box {
    border-radius: 14px; padding: 0.9rem 1.05rem; margin: 0.6rem 0 1rem; border: 1px solid transparent;
  }
  .ok-box { background: #ecfdf3 !important; border-color: #abefc6; }
  .ok-box, .ok-box * { color: #027a48 !important; }
  .err-box { background: #fef3f2 !important; border-color: #fecdca; }
  .err-box, .err-box * { color: #b42318 !important; }
  .info-box { background: #eff8ff !important; border-color: #b2ddff; }
  .info-box, .info-box * { color: #175cd3 !important; }

  [data-theme="dark"] .ok-box { background: rgba(2,122,72,0.18) !important; border-color: #027a48; }
  [data-theme="dark"] .err-box { background: rgba(180,35,24,0.18) !important; border-color: #f97066; }
  [data-theme="dark"] .info-box { background: rgba(23,92,211,0.18) !important; border-color: #84caff; }
  [data-theme="dark"] .ok-box, [data-theme="dark"] .ok-box * { color: #6ce9a6 !important; }
  [data-theme="dark"] .err-box, [data-theme="dark"] .err-box * { color: #fda29b !important; }
  [data-theme="dark"] .info-box, [data-theme="dark"] .info-box * { color: #b2ddff !important; }
</style>
""",
    unsafe_allow_html=True,
)

init_business_layer()
inv: InventoryManager = st.session_state.inv
sales: SalesManager = st.session_state.sales
pdf = products_table(inv)
n_low_live = int(pdf["below_reorder"].sum()) if len(pdf) else 0

with st.sidebar:
    st.markdown(
        """
        <div class="brand-card">
          <div class="brand-mark">S6</div>
          <p class="brand-title">StoreOps</p>
          <p class="brand-sub">Nhà sách & văn phòng phẩm<br/>Chuyên đề 6 · KHDL</p>
        </div>
        <div class="nav-label">Chức năng hệ thống</div>
        """,
        unsafe_allow_html=True,
    )

    for key, num, title, caption in NAV_ITEMS:
        label = f"{num}  {title}"
        clicked = st.button(
            label,
            key=f"nav_{key}",
            type="primary" if st.session_state.nav_page == key else "secondary",
            use_container_width=True,
        )
        if clicked:
            st.session_state.nav_page = key
            st.rerun()

    st.markdown(
        f"""
        <div class="side-kpi">
          <div class="cell"><div class="k">Sản phẩm</div><div class="v">{len(pdf)}</div></div>
          <div class="cell"><div class="k">Dưới reorder</div><div class="v">{n_low_live}</div></div>
          <div class="cell"><div class="k">Đơn phiên này</div><div class="v">{len(sales.orders)}</div></div>
          <div class="cell"><div class="k">Trạng thái</div><div class="v">Live</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Reset tồn kho", use_container_width=True):
        if UI_STOCK.exists():
            UI_STOCK.unlink()
        for p in [UI_LOG / "inventory_log.csv", UI_LOG / "error_log.txt"]:
            if p.exists():
                p.unlink()
        for k in ["inv", "sales", "last_message", "nav_page"]:
            st.session_state.pop(k, None)
        st.rerun()

page = st.session_state.nav_page
page_meta = {k: (num, title, cap) for k, num, title, cap in NAV_ITEMS}
num, title, cap = page_meta[page]

st.markdown(
    f"""
    <div class="hero">
      <h1>{title}</h1>
      <p>{cap} · Hệ thống nghiệp vụ kho + phân tích + học máy</p>
      <span class="chip">Mục {num} / 07</span>
      <span class="chip" style="margin-left:0.35rem;">Seed dữ liệu 42</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
if page == "overview":
    fact = load_csv(str(PROC / "fact_sales.csv"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Doanh thu lịch sử (fact)", fmt_vnd(fact["net_revenue"].sum()))
    c2.metric("Đơn lịch sử", f"{fact['order_id'].nunique():,}")
    c3.metric("Khách có mua", f"{fact['customer_id'].nunique():,}")
    c4.metric("SP dưới reorder (live)", n_low_live)

    st.markdown(
        '<div class="info-box">Hệ thống gồm <b>nghiệp vụ kho/đơn hàng</b> (OOP, có nhật ký) '
        "và <b>lớp phân tích/học máy</b> trên dữ liệu đã xử lý.</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.markdown('<p class="section-title">Tồn kho hiện tại (live)</p>', unsafe_allow_html=True)
        show = pdf[
            [
                "product_id",
                "product_name",
                "category",
                "quantity",
                "reorder_level",
                "below_reorder",
            ]
        ]
        st.dataframe(show, width="stretch", height=380)
    with right:
        st.markdown('<p class="section-title">Cảnh báo ưu tiên</p>', unsafe_allow_html=True)
        alert = show[show["below_reorder"]].sort_values("quantity")
        if alert.empty:
            st.success("Không có sản phẩm dưới mức cảnh báo.")
        else:
            st.warning(f"{len(alert)} sản phẩm cần nhập thêm")
            st.dataframe(alert, width="stretch", height=380)

# =========================================================
elif page == "warehouse":
    st.caption("Dùng InventoryManager: từ chối giao dịch làm tồn kho âm · ghi nhật ký trước/sau")

    opts = product_options(inv)
    with st.form("warehouse_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            action = st.selectbox(
                "Loại giao dịch",
                ["import (nhập kho)", "export (xuất kho)", "adjust (điều chỉnh delta)"],
            )
            product_label = st.selectbox("Sản phẩm", opts)
            qty = st.number_input("Số lượng", min_value=1, value=10, step=1)
        with col_b:
            actor = st.text_input("Người thực hiện", value="thu_kho_01")
            note = st.text_input("Ghi chú", value="")
            if action.startswith("adjust"):
                delta = st.number_input(
                    "Delta điều chỉnh (+ nhập / − giảm)", value=-1, step=1
                )
            else:
                delta = 0
        submitted = st.form_submit_button("Thực hiện giao dịch", type="primary")

    if submitted:
        pid = parse_pid(product_label)
        before = inv.get_product(pid).quantity
        try:
            if action.startswith("import"):
                tx = inv.import_stock(pid, int(qty), performed_by=actor, note=note)
            elif action.startswith("export"):
                tx = inv.export_stock(pid, int(qty), performed_by=actor, note=note)
            else:
                tx = inv.adjust_stock(
                    pid, delta=int(delta), performed_by=actor, note=note or f"delta={delta}"
                )
            persist_stock()
            if tx.status == "success":
                st.markdown(
                    f'<div class="ok-box"><b>{tx.transaction_id}</b> · {tx.transaction_type} · '
                    f"{pid}: {tx.quantity_before} → {tx.quantity_after} · status={tx.status}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="err-box"><b>TỪ CHỐI</b> {tx.transaction_id}: {tx.note}</div>',
                    unsafe_allow_html=True,
                )
        except InventoryError as exc:
            st.markdown(f'<div class="err-box">{exc}</div>', unsafe_allow_html=True)

    st.subheader("Tra cứu nhanh 1 sản phẩm")
    pick = st.selectbox("Chọn SP để xem tồn", opts, key="wh_lookup")
    p = inv.get_product(parse_pid(pick))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tồn hiện tại", p.quantity)
    m2.metric("Reorder level", p.reorder_level)
    m3.metric("Giá", fmt_vnd(p.unit_price))
    m4.metric("Cảnh báo", "CÓ" if p.is_below_reorder() else "Không")

# =========================================================
elif page == "sales":
    st.caption("SalesManager trừ kho theo dòng; thiếu hàng → rollback toàn đơn")

    cust_ids = sorted(sales.customers.keys()) or ["C0001"]
    with st.form("order_form"):
        c1, c2 = st.columns(2)
        with c1:
            customer_id = st.selectbox("Khách hàng", cust_ids)
            channel = st.selectbox("Kênh bán", ["offline", "online", "shopee", "website"])
            payment = st.selectbox("Thanh toán", ["cash", "transfer", "card", "e-wallet"])
        with c2:
            discount = st.number_input("Giảm giá (VND)", min_value=0, value=0, step=1000)
            line1 = st.selectbox("SP dòng 1", product_options(inv), key="o1")
            q1 = st.number_input("SL dòng 1", min_value=1, value=1, key="q1")
            add_second = st.checkbox("Thêm dòng 2", value=True)
            if add_second:
                line2 = st.selectbox("SP dòng 2", product_options(inv), key="o2")
                q2 = st.number_input("SL dòng 2", min_value=1, value=1, key="q2")
            else:
                line2, q2 = None, 0
        ok = st.form_submit_button("Tạo đơn & trừ kho", type="primary")

    if ok:
        items = [{"product_id": parse_pid(line1), "quantity": int(q1)}]
        if add_second and line2:
            items.append({"product_id": parse_pid(line2), "quantity": int(q2)})
        try:
            order = sales.create_order(
                customer_id=customer_id,
                items=items,
                payment_method=payment,
                sales_channel=channel,
                discount=float(discount),
                performed_by="cashier_ui",
            )
            persist_stock()
            st.markdown(
                f'<div class="ok-box"><b>Đơn {order.order_id}</b> thành công · '
                f"tổng {fmt_vnd(order.total)} · {len(order.items)} dòng</div>",
                unsafe_allow_html=True,
            )
            st.json(order.to_dict())
            st.write("Chi tiết dòng:", [i.to_dict() for i in order.items])
        except InventoryError as exc:
            st.markdown(
                f'<div class="err-box"><b>Đơn bị hủy / rollback:</b> {exc}</div>',
                unsafe_allow_html=True,
            )

    st.subheader("Đơn đã tạo trong phiên này")
    if sales.orders:
        st.dataframe(
            pd.DataFrame([o.to_dict() for o in sales.orders.values()]),
            width="stretch",
        )
    else:
        st.info("Chưa có đơn nào trong phiên làm việc hiện tại.")

# =========================================================
elif page == "analytics":
    fact = load_csv(str(PROC / "fact_sales.csv"))
    by_month = load_csv(str(SUM / "revenue_by_month.csv"))
    by_cat = load_csv(str(SUM / "revenue_by_category.csv"))
    by_channel = load_csv(str(SUM / "revenue_by_channel.csv"))
    top_products = load_csv(str(SUM / "top_products.csv"))

    a, b, c = st.columns(3)
    a.metric("Doanh thu ròng", fmt_vnd(fact["net_revenue"].sum()))
    top_cat = by_cat.iloc[0]
    b.metric("Danh mục #1", str(top_cat["category"]))
    top_ch = by_channel.iloc[0]
    c.metric("Kênh #1", str(top_ch["sales_channel"]))

    t1, t2 = st.tabs(["Doanh thu", "Sản phẩm & cặp mua"])
    with t1:
        st.subheader("Theo tháng")
        st.line_chart(by_month.set_index("year_month")["net_revenue"])
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Theo danh mục")
            st.bar_chart(by_cat.set_index("category")["net_revenue"])
        with c2:
            st.subheader("Theo kênh")
            st.bar_chart(by_channel.set_index("sales_channel")["net_revenue"])
        city_path = SUM / "revenue_by_city.csv"
        if city_path.exists():
            st.subheader("Theo thành phố")
            st.bar_chart(load_csv(str(city_path)).set_index("city")["net_revenue"])

    with t2:
        st.subheader("Top sản phẩm bán chạy (doanh thu)")
        st.dataframe(top_products.head(15), width="stretch")
        qty = (
            fact.groupby(["product_id", "product_name"])["quantity"]
            .sum()
            .sort_values(ascending=False)
        )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Top 10 theo số lượng**")
            st.dataframe(qty.head(10).reset_index(), width="stretch")
        with c2:
            st.markdown("**10 bán chậm nhất**")
            st.dataframe(qty.tail(10).reset_index(), width="stretch")

        st.subheader("Cặp sản phẩm thường mua cùng nhau")
        pairs = pair_top(fact, top_n=15)
        st.dataframe(
            pairs[["product_id_x", "product_x", "product_id_y", "product_y", "co_purchase_count"]],
            width="stretch",
        )
        heat = FIG / "06_pair_heatmap.png"
        if heat.exists():
            st.image(str(heat), caption="Heatmap đồng mua (top theo doanh thu)", width="stretch")

# =========================================================
elif page == "rfm":
    rfm = load_csv(str(PROC / "rfm_segments.csv"))
    st.caption("Ngày tham chiếu cố định: 2026-01-01")

    seg = (
        rfm.groupby("segment")
        .agg(
            so_khach=("customer_id", "count"),
            recency_tb=("recency_days", "mean"),
            frequency_tb=("frequency", "mean"),
            monetary_tb=("monetary", "mean"),
        )
        .reset_index()
        .sort_values("monetary_tb", ascending=False)
    )
    st.dataframe(seg, width="stretch")
    st.bar_chart(seg.set_index("segment")["so_khach"])

    strategies = {
        "Champions": "Giữ chân VIP, ưu đãi độc quyền",
        "Loyal": "Upsell/cross-sell, tích điểm",
        "Potential": "Coupon kích hoạt đơn tiếp theo",
        "At Risk": "Win-back, remarketing",
        "Hibernating": "Campaign chi phí thấp",
    }
    st.subheader("Chiến lược theo nhóm")
    for _, row in seg.iterrows():
        name = row["segment"]
        st.markdown(
            f"- **{name}** ({int(row['so_khach'])} KH): {strategies.get(name, 'Theo dõi thêm')}"
        )

    f11 = FIG / "11_rfm_clusters.png"
    if f11.exists():
        st.image(str(f11), width="stretch")

    pick = st.multiselect(
        "Lọc khách theo segment",
        sorted(rfm["segment"].dropna().unique()),
        default=list(sorted(rfm["segment"].dropna().unique())[:2]),
    )
    st.dataframe(
        rfm[rfm["segment"].isin(pick)][
            [
                "customer_id",
                "city",
                "customer_type",
                "segment",
                "recency_days",
                "frequency",
                "monetary",
                "RFM_score",
            ]
        ].sort_values("monetary", ascending=False),
        width="stretch",
        height=360,
    )

# =========================================================
elif page == "ml":
    ml = fit_ml_models()
    mode = st.radio(
        "Chọn bài toán",
        ["Dự đoán giá trị đơn hàng", "Cảnh báo nguy cơ dưới reorder"],
        horizontal=True,
    )

    if mode.startswith("Dự đoán"):
        st.subheader("Nhập hồ sơ đơn để ước lượng giá trị")
        ref = ml["orders_ref"]
        c1, c2, c3 = st.columns(3)
        with c1:
            n_items = st.slider("Số dòng SP", 1, 5, 2)
            total_qty = st.slider("Tổng số lượng", 1, 40, 4)
            avg_price = st.number_input(
                "Giá bán TB",
                min_value=1000.0,
                value=float(ref["avg_selling_price"].median()),
                step=1000.0,
            )
        with c2:
            discount = st.number_input("Discount", min_value=0.0, value=0.0, step=1000.0)
            month = st.slider("Tháng", 1, 12, 6)
            dow = st.slider("Thứ trong tuần (0=Mon)", 0, 6, 2)
        with c3:
            payment = st.selectbox("Thanh toán", sorted(ref["payment_method"].unique()))
            channel = st.selectbox("Kênh", sorted(ref["sales_channel"].unique()))
            city = st.selectbox("Thành phố", sorted(ref["city"].unique()))
            ctype = st.selectbox("Loại KH", sorted(ref["customer_type"].unique()))

        row = pd.DataFrame(
            [
                {
                    "n_items": n_items,
                    "total_qty": total_qty,
                    "avg_selling_price": avg_price,
                    "discount": discount,
                    "month": month,
                    "dow": dow,
                    "payment_method": payment,
                    "sales_channel": channel,
                    "city": city,
                    "customer_type": ctype,
                }
            ]
        )
        pred = float(ml["reg"].predict(row[ml["reg_cols"]])[0])
        st.markdown(
            f'<div class="ok-box">Giá trị đơn dự đoán: <b>{fmt_vnd(pred)}</b> '
            f"(DecisionTreeRegressor)</div>",
            unsafe_allow_html=True,
        )
        metrics = REP / "07_ml_metrics.json"
        if metrics.exists():
            m = json.loads(metrics.read_text(encoding="utf-8"))
            st.caption("Metric trên tập test (pipeline Buổi 7)")
            st.dataframe(pd.DataFrame(m["order_value"]["metrics"]).T, width="stretch")

    else:
        st.subheader("Chọn sản phẩm để dự báo nguy cơ dưới reorder (cuối kỳ)")
        sdf = ml["stock_features"]
        labels = (
            sdf["product_id"] + " | " + sdf["product_name"].astype(str) + " | " + sdf["category"].astype(str)
        ).tolist()
        choice = st.selectbox("Sản phẩm", labels)
        pid = choice.split("|", 1)[0].strip()
        row = sdf[sdf["product_id"] == pid][ml["clf_cols"]]
        proba = None
        pred = int(ml["clf"].predict(row)[0])
        if hasattr(ml["clf"].named_steps["model"], "predict_proba"):
            try:
                proba = float(ml["clf"].predict_proba(row)[0][1])
            except Exception:
                proba = None

        # đối chiếu tồn live
        live_qty = inv.get_product(pid).quantity if pid in inv.products else None
        live_reorder = inv.get_product(pid).reorder_level if pid in inv.products else None

        if pred == 1:
            st.markdown(
                '<div class="err-box"><b>Nguy cơ CAO</b> — mô hình dự báo sản phẩm có thể '
                "xuống dưới mức cảnh báo.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="ok-box"><b>Nguy cơ THẤP</b> — mô hình không báo dưới reorder.</div>',
                unsafe_allow_html=True,
            )
        if proba is not None:
            st.write(f"Xác suất low_stock (ước lượng): **{proba:.1%}**")
        if live_qty is not None:
            st.write(
                f"Tồn live hiện tại: **{live_qty}** / reorder **{live_reorder}** "
                f"→ {'ĐANG dưới cảnh báo' if live_qty <= live_reorder else 'Còn trên cảnh báo'}"
            )

        metrics = REP / "07_ml_metrics.json"
        if metrics.exists():
            m = json.loads(metrics.read_text(encoding="utf-8"))
            st.caption("Metric trên tập test (pipeline Buổi 7)")
            st.dataframe(pd.DataFrame(m["stock_alert"]["metrics"]).T, width="stretch")

# =========================================================
else:  # logs
    log_csv = UI_LOG / "inventory_log.csv"
    err_txt = UI_LOG / "error_log.txt"
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("inventory_log.csv (UI runtime)")
        if log_csv.exists():
            st.dataframe(pd.read_csv(log_csv).tail(100), width="stretch", height=420)
        else:
            st.info("Chưa có giao dịch UI nào.")
    with c2:
        st.subheader("error_log.txt")
        if err_txt.exists():
            st.code(err_txt.read_text(encoding="utf-8")[-5000:] or "(trống)")
        else:
            st.info("Chưa có lỗi ghi nhận.")

    st.subheader("Nhật ký phân tích (pipeline)")
    for name in [
        "buoi5_merge_checks.txt",
        "buoi4_cleaning_report.txt",
        "crawl_log.txt",
    ]:
        p = ROOT / "logs" / name
        if p.exists():
            with st.expander(name):
                st.text(p.read_text(encoding="utf-8")[-4000:])

st.divider()
st.caption(
    "Chạy UI: `python -m streamlit run src/app_dashboard.py` · "
    "Pipeline dữ liệu: `python src/run_all.py`"
)
