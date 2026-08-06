"""
Demo Buổi 2: đọc products, chạy nhập/xuất/điều chỉnh/bán, kiểm tra từ chối âm kho.
Chạy từ thư mục gốc dự án:
    python src/demo_buoi2.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inventory_manager import InventoryError, InventoryManager
from models import Customer
from sales_manager import SalesManager


def main() -> None:
    log_dir = ROOT / "logs"
    raw_csv = ROOT / "data" / "raw" / "products_lecturer.csv"
    out_csv = ROOT / "data" / "processed" / "products_after_buoi2.csv"
    report_path = ROOT / "reports" / "02_ket_qua_buoi_2.md"

    # Xóa log cũ của demo để dễ đọc (giữ error_log sẽ append)
    inv_log = log_dir / "inventory_log.csv"
    if inv_log.exists():
        inv_log.unlink()
    err_log = log_dir / "error_log.txt"
    if err_log.exists():
        err_log.unlink()

    inv = InventoryManager(log_dir=log_dir, performed_by="demo_buoi2")
    n = inv.load_products_from_csv(raw_csv)
    before = inv.snapshot()

    print(f"Loaded {n} products from {raw_csv.name}")
    print(f"Checkpoint BEFORE sample P0001={before.get('P0001')}, P0011={before.get('P0011')}")

    results = []

    # 1) Nhập kho
    tx1 = inv.import_stock("P0001", 20, note="Nhập bổ sung vở")
    results.append(("import P0001 +20", tx1.status, tx1.quantity_before, tx1.quantity_after))

    # 2) Xuất kho hợp lệ
    tx2 = inv.export_stock("P0001", 10, note="Xuất nội bộ")
    results.append(("export P0001 -10", tx2.status, tx2.quantity_before, tx2.quantity_after))

    # 3) Điều chỉnh
    tx3 = inv.adjust_stock("P0011", delta=-5, note="Kiểm kê hao hụt")
    results.append(("adjust P0011 delta=-5", tx3.status, tx3.quantity_before, tx3.quantity_after))

    # 4) Xuất vượt tồn -> rejected
    p = inv.get_product("P0005")
    tx4 = inv.export_stock("P0005", p.quantity + 100, note="Cố tình vượt tồn")
    results.append(
        ("export P0005 vượt tồn", tx4.status, tx4.quantity_before, tx4.quantity_after)
    )

    # 5) Bán hàng qua SalesManager
    sales = SalesManager(inv)
    sales.add_customer(
        Customer("C0001", city="Hà Nội", customer_type="retail", join_date="2026-01-15")
    )
    order = sales.create_order(
        customer_id="C0001",
        items=[
            {"product_id": "P0001", "quantity": 2},
            {"product_id": "P0011", "quantity": 5},
        ],
        payment_method="transfer",
        sales_channel="offline",
        discount=0,
    )
    results.append(
        (
            f"sale order {order.order_id}",
            "success",
            None,
            f"total={order.total:,.0f} | items={len(order.items)}",
        )
    )

    # 6) Đơn vượt tồn -> raise / rollback
    try:
        sales.create_order(
            customer_id="C0001",
            items=[{"product_id": "P0005", "quantity": 10_000}],
            payment_method="cash",
        )
        results.append(("sale vượt tồn", "UNEXPECTED_SUCCESS", None, None))
    except InventoryError as exc:
        results.append(("sale vượt tồn", "rejected_ok", None, str(exc)))

    after = inv.snapshot()
    inv.save_products_to_csv(out_csv)

    print("\n=== KẾT QUẢ GIAO DỊCH ===")
    for row in results:
        print(row)

    low = inv.low_stock_products()
    print(f"\nSố SP dưới reorder_level: {len(low)}")
    print(f"inventory_log: {inv.inventory_log_path}")
    print(f"error_log: {inv.error_log_path}")
    print(f"products snapshot: {out_csv}")

    # Báo cáo ngắn
    lines = [
        "# Kết quả demo Buổi 2 — OOP quản lý kho",
        "",
        f"- Đã nạp **{n}** sản phẩm từ `{raw_csv.name}`",
        f"- Checkpoint P0001: {before.get('P0001')} → {after.get('P0001')}",
        f"- Checkpoint P0011: {before.get('P0011')} → {after.get('P0011')}",
        f"- Đơn bán mẫu: `{order.order_id}` tổng **{order.total:,.0f}** VND",
        f"- Số giao dịch ghi log: **{len(inv.transactions)}**",
        f"- SP dưới reorder_level: **{len(low)}**",
        "",
        "## Các tình huống đã kiểm tra",
        "",
        "| Tình huống | Status | Before | After/Note |",
        "|---|---|---|---|",
    ]
    for name, status, b, a in results:
        lines.append(f"| {name} | {status} | {b} | {a} |")
    lines += [
        "",
        "## File phát sinh",
        "",
        f"- `{inv.inventory_log_path.relative_to(ROOT)}`",
        f"- `{inv.error_log_path.relative_to(ROOT)}`",
        f"- `{out_csv.relative_to(ROOT)}`",
        "",
        "## Lớp đã xây",
        "",
        "- `models.py`: Product, Customer, Order, OrderItem, InventoryTransaction",
        "- `inventory_manager.py`: InventoryManager",
        "- `sales_manager.py`: SalesManager",
        "",
        "Chạy lại: `python src/demo_buoi2.py`",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {report_path}")

    # Xuất thêm JSON tóm tắt đơn
    summary = {
        "n_products": n,
        "n_transactions": len(inv.transactions),
        "sample_order": order.to_dict(),
        "rejected": [t.to_dict() for t in inv.transactions if t.status == "rejected"],
    }
    (ROOT / "reports" / "02_demo_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
