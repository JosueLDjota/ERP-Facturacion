from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from database import DBManager
from erp.domain.services.invoice_calculator import calculate_invoice_totals
from erp.domain.use_cases.receipt_use_case import ReceiptStorageService
from receipt_builder import build_receipt_html, load_receipt_labels


logger = logging.getLogger(__name__)


class SaleProcessingError(RuntimeError):
    pass


@dataclass(slots=True)
class SaleService:
    db: DBManager
    receipt_storage: ReceiptStorageService

    def process_sale(
        self,
        *,
        sale_id: str,
        fecha: str,
        items: list[dict[str, Any]],
        usuario_id: int,
        cliente_id: int | None,
        metodo_pago: str,
        amount_received: float | str | None,
        tipo_recibo: str,
        receipt_mode: str,
        tax_included: bool,
        number_to_words: Callable[[int], str] | None = None,
    ) -> dict[str, Any]:
        if not items:
            raise SaleProcessingError("No se puede procesar una venta sin productos.")

        invoice = calculate_invoice_totals(
            items,
            tax_included=tax_included,
            payment_method=metodo_pago,
            amount_received=amount_received,
        )
        if invoice.validation_errors:
            raise SaleProcessingError(" ".join(invoice.validation_errors))

        cliente = self._fetch_client(cliente_id)
        template_html = self.db.get_config("recibo_template", self.db.default_receipt_template())
        empresa = {
            "nombre": self.db.get_config("empresa_nombre", None),
            "rtn": self.db.get_config("empresa_rtn", None),
            "tel": self.db.get_config("empresa_tel", None),
            "direccion": self.db.get_config("empresa_direccion", None),
            "email": self.db.get_config("empresa_email", None),
            "logo_url": self.db.get_config("empresa_logo_url", None),
        }
        empresa = {key: value for key, value in empresa.items() if value}
        html_content = build_receipt_html(
            venta_id=sale_id,
            fecha=fecha,
            total=invoice.total,
            monto_pagado=invoice.monto_recibido,
            vuelto=invoice.vuelto,
            items=items,
            cliente=cliente,
            metodo_pago=metodo_pago,
            mode=receipt_mode,
            number_to_words=number_to_words,
            tax_included=tax_included,
            template_html=template_html,
            empresa=empresa,
            observaciones=self.db.get_config("recibo_observaciones", ""),
            labels=load_receipt_labels(self.db.get_config),
        )

        receipt_path: str | None = None
        try:
            with self.db.transaction():
                self.db.execute_checked(
                    """
                    INSERT INTO Ventas (
                        id, fecha, total, monto_pagado, vuelto, metodo_pago, usuario_id, id_cliente, tipo_recibo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        fecha,
                        invoice.total,
                        invoice.monto_recibido,
                        invoice.vuelto,
                        metodo_pago,
                        usuario_id,
                        cliente_id,
                        tipo_recibo,
                    ),
                )

                for item in items:
                    self._persist_sale_item(sale_id, item)

                self.db.create_venta_diaria(
                    monto_total=invoice.total,
                    metodo_pago=metodo_pago,
                    referencia=f"POS-{sale_id}",
                )
                receipt_path = self.receipt_storage.save_receipt(html_content, sale_id)
        except Exception as exc:
            if receipt_path:
                try:
                    Path(receipt_path).unlink(missing_ok=True)
                except OSError:
                    logger.warning("No se pudo limpiar el recibo temporal '%s' tras rollback.", receipt_path)
            logger.exception("Fallo procesando la venta '%s'.", sale_id)
            raise SaleProcessingError(str(exc)) from exc

        return {
            "sale_id": sale_id,
            "fecha": fecha,
            "total": float(invoice.total),
            "monto_pagado": float(invoice.monto_recibido),
            "vuelto": float(invoice.vuelto),
            "receipt_path": receipt_path,
            "html_content": html_content,
            "cliente": cliente,
        }

    def _persist_sale_item(self, sale_id: str, item: dict[str, Any]) -> None:
        producto_id = int(item["producto_id"])
        cantidad = int(item["cantidad"])
        precio = float(item["precio_unitario"])
        descuento_pct = float(item.get("descuento_porcentaje", 0) or 0)
        descuento_monto = (precio * cantidad) * descuento_pct
        subtotal = (precio * cantidad) - descuento_monto

        stock_row = self.db.fetch_one("SELECT stock FROM Productos WHERE id = ?", (producto_id,))
        if not stock_row:
            raise SaleProcessingError(f"Producto {producto_id} no existe.")
        if int(stock_row[0]) < cantidad:
            raise SaleProcessingError(f"Stock insuficiente para {item['nombre']}.")

        self.db.execute_checked(
            """
            INSERT INTO DetalleVenta (
                venta_id, producto_id, nombre_producto, cantidad, precio_unitario, descuento, subtotal
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sale_id,
                producto_id,
                str(item["nombre"]),
                cantidad,
                precio,
                descuento_monto,
                subtotal,
            ),
        )
        self.db.execute_checked(
            "UPDATE Productos SET stock = stock - ? WHERE id = ?",
            (cantidad, producto_id),
        )

    def _fetch_client(self, cliente_id: int | None) -> dict[str, Any] | None:
        if not cliente_id:
            return None

        row = self.db.fetch_one(
            "SELECT nombre, apellido, dni, telefono, direccion FROM Clientes WHERE id = ?",
            (cliente_id,),
        )
        if not row:
            return None
        return {
            "nombre": row[0],
            "apellido": row[1],
            "dni": row[2],
            "telefono": row[3],
            "direccion": row[4],
        }
