from __future__ import annotations

# Contexto del archivo:
# Caso de uso transaccional de venta POS. Valida la venta pendiente, calcula
# totales, persiste la operacion de forma atomica y devuelve un resultado listo
# para recibo y refresco visual del POS.

from dataclasses import dataclass

from erp.data.repositories.sale_repository import SaleRepository
from erp.domain.services.invoice_calculator import calculate_invoice_totals
from erp.domain.services.receipt_service import ReceiptService


@dataclass(slots=True)
class CreatePOSSaleResult:
    sale_id: str
    fecha: str
    total: float
    monto_pagado: float
    vuelto: float
    metodo_pago: str
    cliente_id: int | None
    cart_data: dict
    receipt_html: str


@dataclass(slots=True)
class CreatePOSSale:
    sales: SaleRepository
    receipt_service: ReceiptService

    def execute(
        self,
        sale_data: dict,
        *,
        usuario_id: int,
        preview_mode: str = "ticket",
        number_to_words=None,
    ) -> CreatePOSSaleResult:
        if not sale_data:
            raise ValueError("No hay venta pendiente para procesar.")

        sale_id = str(sale_data.get("venta_id") or "").strip()
        fecha = str(sale_data.get("fecha") or "").strip()
        cart_data = sale_data.get("cart_snapshot") or {}
        metodo_pago = str(sale_data.get("metodo_pago") or "NO_DEFINIDO").strip().upper()
        tipo_recibo = f"POS-{str(sale_data.get('modo') or 'NORMAL').strip().upper()}"
        tax_included = bool(sale_data.get("tax_included", True))
        cliente_id = sale_data.get("cliente_id")

        if not sale_id:
            raise ValueError("La venta no tiene identificador.")
        if not fecha:
            raise ValueError("La venta no tiene fecha valida.")
        if usuario_id in ("", None):
            raise ValueError("La venta requiere un usuario valido.")
        if not cart_data:
            raise ValueError("No hay productos para registrar en la venta.")

        receipt_items = self.receipt_service.build_receipt_items(cart_data)
        invoice = calculate_invoice_totals(
            receipt_items,
            tax_included=tax_included,
            payment_method=metodo_pago,
            amount_received=sale_data.get("pagado", 0),
        )
        if invoice.validation_errors:
            raise ValueError(" ".join(invoice.validation_errors))

        self.sales.create_sale(
            sale_id=sale_id,
            fecha=fecha,
            total=float(invoice.total),
            pagado=float(invoice.monto_recibido),
            vuelto=float(invoice.vuelto),
            metodo_pago=metodo_pago,
            usuario_id=int(usuario_id),
            cliente_id=int(cliente_id) if cliente_id not in (None, "") else None,
            tipo_recibo=tipo_recibo,
            items=cart_data,
        )

        client = self.sales.get_client_detail(int(cliente_id)) if cliente_id not in (None, "") else None
        receipt_html = self.receipt_service.build_html(
            venta_id=sale_id,
            fecha=fecha,
            total=float(invoice.total),
            monto_pagado=float(invoice.monto_recibido),
            vuelto=float(invoice.vuelto),
            cart_data=cart_data,
            cliente=client,
            metodo_pago=metodo_pago,
            mode=preview_mode,
            number_to_words=number_to_words,
            tax_included=tax_included,
        )

        return CreatePOSSaleResult(
            sale_id=sale_id,
            fecha=fecha,
            total=float(invoice.total),
            monto_pagado=float(invoice.monto_recibido),
            vuelto=float(invoice.vuelto),
            metodo_pago=metodo_pago,
            cliente_id=int(cliente_id) if cliente_id not in (None, "") else None,
            cart_data=cart_data,
            receipt_html=receipt_html,
        )
