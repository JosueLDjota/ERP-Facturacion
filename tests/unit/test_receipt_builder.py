import unittest

from receipt_builder import (
    build_receipt_html,
    build_receipt_preview_text,
    default_receipt_labels,
    load_receipt_labels,
)


class ReceiptBuilderTests(unittest.TestCase):
    def test_receipt_splits_base_and_tax_when_prices_include_isv(self):
        html = build_receipt_html(
            venta_id="V-001",
            fecha="2026-03-30 14:49:37",
            total=970.0,
            monto_pagado=1000.0,
            vuelto=30.0,
            metodo_pago="TRANSFERENCIA",
            items=[
                {"producto_id": 4, "nombre": "Laptop HP", "cantidad": 1, "precio_unitario": 650.0, "subtotal": 650.0},
                {"producto_id": 1, "nombre": "Monitor 27", "cantidad": 1, "precio_unitario": 320.0, "subtotal": 320.0},
            ],
        )

        self.assertIn("<tr><td>TOTAL</td><td>L 970.00</td></tr>", html)
        self.assertIn("<tr><td>Base Gravada 15%</td><td>L 843.48</td></tr>", html)
        self.assertIn("<tr><td>Impuesto 15%</td><td>L 126.52</td></tr>", html)
        self.assertIn("<strong>Monto recibido:</strong> L 970.00", html)
        self.assertNotIn("<strong>Vuelto:</strong>", html)

    def test_receipt_adds_tax_when_prices_do_not_include_isv(self):
        html = build_receipt_html(
            venta_id="V-002",
            fecha="2026-03-30 14:49:37",
            total=1115.5,
            monto_pagado=1200.0,
            vuelto=84.5,
            metodo_pago="EFECTIVO",
            tax_included=False,
            items=[
                {"producto_id": 4, "nombre": "Laptop HP", "cantidad": 1, "precio_unitario": 650.0, "subtotal": 650.0},
                {"producto_id": 1, "nombre": "Monitor 27", "cantidad": 1, "precio_unitario": 320.0, "subtotal": 320.0},
            ],
        )

        self.assertIn("<tr><td>Impuesto 15%</td><td>L 145.50</td></tr>", html)
        self.assertIn("<tr><td>TOTAL</td><td>L 1115.50</td></tr>", html)
        self.assertIn("<strong>Vuelto:</strong> L 84.50", html)

    def test_receipt_for_45_with_tax_included_shows_base_subtotal(self):
        html = build_receipt_html(
            venta_id="V-003",
            fecha="2026-03-30 15:50:35",
            total=45.0,
            monto_pagado=50.0,
            vuelto=5.0,
            metodo_pago="EFECTIVO",
            items=[
                {"producto_id": 2, "nombre": "Teclado Mecanico", "cantidad": 1, "precio_unitario": 45.0, "subtotal": 45.0},
            ],
            tax_included=True,
        )

        self.assertIn("<tr><td>Base Gravada 15%</td><td>L 39.13</td></tr>", html)
        self.assertIn("<tr><td>Impuesto 15%</td><td>L 5.87</td></tr>", html)
        self.assertIn("<tr><td>TOTAL</td><td>L 45.00</td></tr>", html)
        self.assertNotIn("Sub Total", html)

    def test_receipt_template_and_preview_share_same_labels(self):
        template = """
<html>
<body>
    <h1>{{DOC_TITLE}}</h1>
    <div>{{NOMBRE_NEGOCIO}}</div>
    <div>{{LABEL_MONTO_RECIBIDO}}: {{MONTO_PAGADO}}</div>
    <!-- ITEMS_PLACEHOLDER -->
    <footer>{{THANK_YOU_MESSAGE}}</footer>
</body>
</html>
"""
        labels = default_receipt_labels()
        labels["DOC_TITLE"] = "RECIBO PERSONALIZADO"
        labels["LABEL_MONTO_RECIBIDO"] = "Recibido cliente"
        labels["THANK_YOU_MESSAGE"] = "Gracias por volver"

        html = build_receipt_html(
            venta_id="V-004",
            fecha="2026-04-01 12:00:00",
            total=45.0,
            monto_pagado=50.0,
            vuelto=5.0,
            metodo_pago="EFECTIVO",
            items=[
                {"producto_id": 2, "nombre": "Teclado Mecanico", "cantidad": 1, "precio_unitario": 45.0, "subtotal": 45.0},
            ],
            template_html=template,
            labels=labels,
            empresa={"nombre": "ERP DEMO"},
        )
        preview = build_receipt_preview_text(
            venta_id="V-004",
            fecha="2026-04-01 12:00:00",
            metodo_pago="EFECTIVO",
            items=[
                {"producto_id": 2, "nombre": "Teclado Mecanico", "cantidad": 1, "precio_unitario": 45.0, "subtotal": 45.0},
            ],
            template_text=template,
            labels=labels,
            empresa={"nombre": "ERP DEMO"},
            amount_received=50.0,
        )

        self.assertIn("RECIBO PERSONALIZADO", html)
        self.assertIn("Recibido cliente: 50.00", html)
        self.assertIn("ERP DEMO", html)
        self.assertIn("Gracias por volver", preview)
        self.assertIn("Recibido cliente: 50.00", preview)

    def test_receipt_template_supports_legacy_items_rows_placeholder(self):
        template = """
<html>
<body>
    <table>
        <tbody>
            {{ITEMS_ROWS}}
        </tbody>
    </table>
    <div>Subtotal legacy: {{SUB_TOTAL}}</div>
    <div>Recibido legacy: {{MONTO_RECIBIDO}}</div>
</body>
</html>
"""

        html = build_receipt_html(
            venta_id="V-005",
            fecha="2026-04-01 12:10:00",
            total=45.0,
            monto_pagado=50.0,
            vuelto=5.0,
            metodo_pago="EFECTIVO",
            items=[
                {"producto_id": 2, "nombre": "Teclado Mecanico", "cantidad": 1, "precio_unitario": 45.0, "subtotal": 45.0},
            ],
            template_html=template,
        )

        self.assertIn("<tr><td>1</td><td>00000002</td><td>Teclado Mecanico</td><td>L 45.00</td><td>L 45.00</td></tr>", html)
        self.assertIn("Subtotal legacy: 39.13", html)
        self.assertIn("Recibido legacy: 50.00", html)

    def test_load_receipt_labels_uses_defaults_when_config_is_missing(self):
        values = {
            "recibo_doc_title": "FACTURA FISCAL",
            "recibo_label_monto_recibido": "Pago recibido",
        }

        def get_config(key, default=None):
            return values.get(key, default)

        labels = load_receipt_labels(get_config)

        self.assertEqual(labels["DOC_TITLE"], "FACTURA FISCAL")
        self.assertEqual(labels["LABEL_MONTO_RECIBIDO"], "Pago recibido")
        self.assertEqual(labels["LABEL_VUELTO"], default_receipt_labels()["LABEL_VUELTO"])


if __name__ == "__main__":
    unittest.main()
