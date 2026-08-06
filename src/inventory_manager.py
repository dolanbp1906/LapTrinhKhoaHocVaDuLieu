"""
InventoryManager: nhập / xuất / điều chỉnh tồn kho.
- Từ chối giao dịch làm tồn kho âm
- Ghi inventory_log.csv và error_log.txt
- Lưu trạng thái trước/sau (checkpoint)
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from models import InventoryTransaction, Product


class InventoryError(Exception):
    """Lỗi nghiệp vụ kho."""


class InventoryManager:
    VALID_TYPES = {"import", "export", "adjust", "sale"}

    def __init__(
        self,
        products: Optional[dict[str, Product]] = None,
        log_dir: Optional[Path] = None,
        performed_by: str = "system",
    ) -> None:
        self.products: dict[str, Product] = products or {}
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.inventory_log_path = self.log_dir / "inventory_log.csv"
        self.error_log_path = self.log_dir / "error_log.txt"
        self.performed_by = performed_by
        self._tx_counter = 0
        self.transactions: list[InventoryTransaction] = []
        self._ensure_inventory_log_header()

    def load_products_from_csv(self, path: Path) -> int:
        path = Path(path)
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            product = Product.from_row(row)
            self.products[product.product_id] = product
        return len(rows)

    def save_products_to_csv(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self.products:
            return
        fieldnames = list(next(iter(self.products.values())).to_dict().keys())
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in self.products.values():
                writer.writerow(p.to_dict())

    def _next_tx_id(self) -> str:
        self._tx_counter += 1
        return f"TX{self._tx_counter:06d}"

    def _ensure_inventory_log_header(self) -> None:
        if self.inventory_log_path.exists():
            return
        fieldnames = [
            "transaction_id",
            "timestamp",
            "transaction_type",
            "product_id",
            "quantity",
            "performed_by",
            "status",
            "quantity_before",
            "quantity_after",
            "note",
        ]
        with self.inventory_log_path.open("w", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    def _append_inventory_log(self, tx: InventoryTransaction) -> None:
        fieldnames = list(tx.to_dict().keys())
        with self.inventory_log_path.open("a", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writerow(tx.to_dict())

    def _append_error(self, message: str) -> None:
        with self.error_log_path.open("a", encoding="utf-8") as f:
            f.write(message.rstrip() + "\n")

    def get_product(self, product_id: str) -> Product:
        if product_id not in self.products:
            raise InventoryError(f"Không tìm thấy sản phẩm: {product_id}")
        return self.products[product_id]

    def snapshot(self) -> dict[str, int]:
        """Checkpoint tồn kho hiện tại."""
        return {pid: p.quantity for pid, p in self.products.items()}

    def low_stock_products(self) -> list[Product]:
        return [p for p in self.products.values() if p.is_below_reorder()]

    def apply_transaction(
        self,
        product_id: str,
        transaction_type: str,
        quantity: int,
        performed_by: Optional[str] = None,
        note: str = "",
        signed_adjust: Optional[int] = None,
    ) -> InventoryTransaction:
        """
        Áp dụng một giao dịch kho.

        - import / export / sale: `quantity` > 0
        - adjust: dùng `signed_adjust` (âm/dương) làm delta;
          nếu không truyền, `quantity` là tồn kho mới (set)
        """
        tx_type = transaction_type.lower().strip()
        actor = performed_by or self.performed_by

        if tx_type not in self.VALID_TYPES:
            msg = f"Loại giao dịch không hợp lệ: {transaction_type}"
            self._append_error(msg)
            raise InventoryError(msg)

        try:
            product = self.get_product(product_id)
        except InventoryError as exc:
            self._append_error(str(exc))
            raise

        before = product.quantity

        if tx_type == "import":
            if quantity <= 0:
                return self._reject(
                    tx_type, product_id, quantity, actor, before, "Số lượng nhập phải > 0"
                )
            after = before + quantity
            delta_logged = quantity

        elif tx_type in {"export", "sale"}:
            if quantity <= 0:
                return self._reject(
                    tx_type, product_id, quantity, actor, before, "Số lượng xuất phải > 0"
                )
            after = before - quantity
            if after < 0:
                return self._reject(
                    tx_type,
                    product_id,
                    quantity,
                    actor,
                    before,
                    f"Từ chối: tồn kho âm (hiện có {before}, yêu cầu {quantity})",
                )
            delta_logged = quantity

        else:  # adjust
            if signed_adjust is not None:
                after = before + int(signed_adjust)
                delta_logged = abs(int(signed_adjust))
                note = note or f"adjust delta={signed_adjust}"
            else:
                if quantity < 0:
                    return self._reject(
                        tx_type,
                        product_id,
                        quantity,
                        actor,
                        before,
                        "Tồn kho mới không được âm",
                    )
                after = quantity
                delta_logged = abs(after - before)
                note = note or f"adjust set={quantity}"

            if after < 0:
                return self._reject(
                    tx_type,
                    product_id,
                    delta_logged,
                    actor,
                    before,
                    f"Từ chối adjust: tồn kho sẽ âm ({after})",
                )

        product.quantity = after
        tx = InventoryTransaction.create(
            transaction_id=self._next_tx_id(),
            transaction_type=tx_type,
            product_id=product_id,
            quantity=delta_logged,
            performed_by=actor,
            status="success",
            quantity_before=before,
            quantity_after=after,
            note=note,
        )
        self.transactions.append(tx)
        self._append_inventory_log(tx)
        return tx

    def _reject(
        self,
        tx_type: str,
        product_id: str,
        quantity: int,
        actor: str,
        before: int,
        reason: str,
    ) -> InventoryTransaction:
        tx = InventoryTransaction.create(
            transaction_id=self._next_tx_id(),
            transaction_type=tx_type,
            product_id=product_id,
            quantity=quantity,
            performed_by=actor,
            status="rejected",
            quantity_before=before,
            quantity_after=before,
            note=reason,
        )
        self.transactions.append(tx)
        self._append_inventory_log(tx)
        self._append_error(
            f"[{tx.timestamp}] {tx.transaction_id} {tx_type} {product_id}: {reason}"
        )
        return tx

    def import_stock(self, product_id: str, quantity: int, **kwargs) -> InventoryTransaction:
        return self.apply_transaction(product_id, "import", quantity, **kwargs)

    def export_stock(self, product_id: str, quantity: int, **kwargs) -> InventoryTransaction:
        return self.apply_transaction(product_id, "export", quantity, **kwargs)

    def adjust_stock(
        self,
        product_id: str,
        new_quantity: Optional[int] = None,
        delta: Optional[int] = None,
        **kwargs,
    ) -> InventoryTransaction:
        if delta is not None:
            return self.apply_transaction(
                product_id, "adjust", abs(delta), signed_adjust=delta, **kwargs
            )
        if new_quantity is None:
            raise InventoryError("adjust_stock cần new_quantity hoặc delta")
        return self.apply_transaction(product_id, "adjust", new_quantity, **kwargs)
