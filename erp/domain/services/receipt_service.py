from __future__ import annotations

# Contexto del archivo:
# Servicio de dominio que transforma el carrito POS en lineas de recibo y
# delega el render HTML al adaptador de impresion. Su objetivo es que la UI no
# construya directamente estructuras de recibo ni dependa del renderer final.

from dataclasses import dataclass

from erp.infrastructure.printing.receipt_builder import build_receipt_html


@dataclass(slots=True)
class ReceiptService:
    def build_receipt_items(self, cart_data: dict) -> list[dict]:
        items = []
        for raw_product_id, item in (cart_data or {}).items():
            product_id = int(raw_product_id)
            quantity = int(item["cantidad"])
            unit_price = float(item["precio_unitario"])
            discount_pct = float(item.get("descuento_porcentaje", 0) or 0)
            subtotal = (unit_price * quantity) * (1 - discount_pct)

            items.append(
                {
                    "producto_id": product_id,
                    "nombre": item["nombre"],
                    "cantidad": quantity,
                    "precio_unitario": unit_price,
                    "descuento_porcentaje": discount_pct,
                    "descuento_monto": (unit_price * quantity) * discount_pct,
                    "subtotal": subtotal,
                    "tax_rate": float(item.get("tax_rate", 0.15)),
                    "tax_exempt": bool(item.get("tax_exempt", False)),
                }
            )
        return items

    def build_html(
        self,
        *,
        venta_id: str,
        fecha: str,
        total: float,
        monto_pagado: float,
        vuelto: float,
        cart_data: dict,
        cliente: dict | None = None,
        metodo_pago: str = "NO_DEFINIDO",
        mode: str = "ticket",
        number_to_words=None,
        tax_included: bool = True,
    ) -> str:
        return build_receipt_html(
            venta_id=venta_id,
            fecha=fecha,
            total=total,
            monto_pagado=monto_pagado,
            vuelto=vuelto,
            items=self.build_receipt_items(cart_data),
            cliente=cliente,
            metodo_pago=metodo_pago,
            mode=mode,
            number_to_words=number_to_words,
            tax_included=tax_included,
        )
