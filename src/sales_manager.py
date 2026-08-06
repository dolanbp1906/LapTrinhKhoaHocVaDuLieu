"""
SalesManager: tạo đơn hàng và trừ kho qua InventoryManager.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from inventory_manager import InventoryError, InventoryManager
from models import Customer, Order, OrderItem


class SalesManager:
    def __init__(self, inventory: InventoryManager) -> None:
        self.inventory = inventory
        self.customers: dict[str, Customer] = {}
        self.orders: dict[str, Order] = {}
        self._order_counter = 0

    def add_customer(self, customer: Customer) -> None:
        self.customers[customer.customer_id] = customer

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"ORD{self._order_counter:06d}"

    def create_order(
        self,
        customer_id: str,
        items: list[dict],
        payment_method: str = "cash",
        sales_channel: str = "offline",
        discount: float = 0.0,
        order_date: Optional[str] = None,
        performed_by: str = "cashier",
        allow_partial: bool = False,
    ) -> Order:
        """
        Tạo đơn và trừ kho theo từng dòng.

        items: list[{"product_id", "quantity", "selling_price"?}]
        Nếu một dòng làm âm kho: dòng đó bị từ chối.
        - allow_partial=False (mặc định): nếu có dòng bị từ chối thì hủy toàn bộ
          các dòng đã trừ thành công trong đơn (rollback) và raise InventoryError.
        - allow_partial=True: giữ các dòng thành công, bỏ dòng lỗi.
        """
        if customer_id not in self.customers:
            # Cho phép đơn với khách chưa đăng ký đầy đủ ở Buổi 2
            self.customers[customer_id] = Customer(
                customer_id=customer_id,
                city="Unknown",
                customer_type="retail",
                join_date=datetime.now().date().isoformat(),
            )

        order = Order(
            order_id=self._next_order_id(),
            customer_id=customer_id,
            order_date=order_date or datetime.now().isoformat(timespec="seconds"),
            payment_method=payment_method,
            sales_channel=sales_channel,
            discount=discount,
        )

        applied: list[tuple[str, int]] = []  # product_id, qty để rollback
        rejected_notes: list[str] = []

        for raw in items:
            pid = str(raw["product_id"])
            qty = int(raw["quantity"])
            product = self.inventory.get_product(pid)
            price = float(raw.get("selling_price", product.unit_price))

            tx = self.inventory.apply_transaction(
                product_id=pid,
                transaction_type="sale",
                quantity=qty,
                performed_by=performed_by,
                note=f"order={order.order_id}",
            )
            if tx.status == "rejected":
                rejected_notes.append(tx.note)
                if not allow_partial:
                    # rollback các dòng đã trừ
                    for r_pid, r_qty in applied:
                        self.inventory.apply_transaction(
                            product_id=r_pid,
                            transaction_type="import",
                            quantity=r_qty,
                            performed_by=performed_by,
                            note=f"rollback order={order.order_id}",
                        )
                    raise InventoryError(
                        "Đơn bị hủy do không đủ tồn kho: " + " | ".join(rejected_notes)
                    )
                continue

            order.add_item(
                OrderItem(product_id=pid, quantity=qty, selling_price=price)
            )
            applied.append((pid, qty))

        if not order.items:
            raise InventoryError("Đơn hàng trống: mọi dòng đều bị từ chối")

        self.orders[order.order_id] = order
        return order

    def order_summary(self, order_id: str) -> dict:
        if order_id not in self.orders:
            raise InventoryError(f"Không tìm thấy đơn: {order_id}")
        return self.orders[order_id].to_dict()
