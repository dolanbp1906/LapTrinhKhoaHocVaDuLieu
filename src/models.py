"""
Các lớp miền dữ liệu cho Chuyên đề 6.
Buổi 2: Product, Customer, Order, OrderItem, InventoryTransaction.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Product:
    product_id: str
    product_name: str
    category: str
    unit_price: float
    quantity: int
    reorder_level: int
    brand: str = "Unknown"
    unit: str = "cái"
    popularity_weight: float = 1.0
    paired_product_id: Optional[str] = None
    source_type: str = "unknown"
    source_reference: str = ""

    def is_below_reorder(self) -> bool:
        return self.quantity <= self.reorder_level

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict) -> "Product":
        paired = (row.get("paired_product_id") or "").strip() or None
        # lecturer sample dùng initial_quantity; sau này dùng quantity hiện tại
        qty_raw = row.get("quantity", row.get("initial_quantity", 0))
        return cls(
            product_id=str(row["product_id"]).strip(),
            product_name=str(row["product_name"]).strip(),
            category=str(row.get("category", "")).strip(),
            brand=str(row.get("brand", "Unknown")).strip() or "Unknown",
            unit=str(row.get("unit", "cái")).strip() or "cái",
            unit_price=float(row["unit_price"]),
            quantity=int(qty_raw),
            reorder_level=int(row["reorder_level"]),
            popularity_weight=float(row.get("popularity_weight") or 1),
            paired_product_id=paired,
            source_type=str(row.get("source_type", "unknown")),
            source_reference=str(row.get("source_reference", "")),
        )


@dataclass
class Customer:
    customer_id: str
    city: str
    customer_type: str
    join_date: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict) -> "Customer":
        return cls(
            customer_id=str(row["customer_id"]).strip(),
            city=str(row.get("city", "")).strip(),
            customer_type=str(row.get("customer_type", "retail")).strip(),
            join_date=str(row.get("join_date", "")).strip(),
        )


@dataclass
class OrderItem:
    product_id: str
    quantity: int
    selling_price: float

    @property
    def line_total(self) -> float:
        return self.quantity * self.selling_price

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Order:
    order_id: str
    customer_id: str
    order_date: str
    payment_method: str = "cash"
    sales_channel: str = "offline"
    discount: float = 0.0
    items: list[OrderItem] = field(default_factory=list)

    def add_item(self, item: OrderItem) -> None:
        self.items.append(item)

    @property
    def subtotal(self) -> float:
        return sum(i.line_total for i in self.items)

    @property
    def total(self) -> float:
        return max(0.0, self.subtotal - float(self.discount))

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "order_date": self.order_date,
            "payment_method": self.payment_method,
            "sales_channel": self.sales_channel,
            "discount": self.discount,
            "subtotal": self.subtotal,
            "total": self.total,
            "n_items": len(self.items),
        }


@dataclass
class InventoryTransaction:
    transaction_id: str
    timestamp: str
    transaction_type: str  # import | export | adjust | sale
    product_id: str
    quantity: int  # số lượng thay đổi (dương); chiều phụ thuộc type
    performed_by: str
    status: str  # success | rejected
    quantity_before: int
    quantity_after: int
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def create(
        cls,
        transaction_id: str,
        transaction_type: str,
        product_id: str,
        quantity: int,
        performed_by: str,
        status: str,
        quantity_before: int,
        quantity_after: int,
        note: str = "",
        timestamp: Optional[str] = None,
    ) -> "InventoryTransaction":
        return cls(
            transaction_id=transaction_id,
            timestamp=timestamp or _now_iso(),
            transaction_type=transaction_type,
            product_id=product_id,
            quantity=quantity,
            performed_by=performed_by,
            status=status,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            note=note,
        )
