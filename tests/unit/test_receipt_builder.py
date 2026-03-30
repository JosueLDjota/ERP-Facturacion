import unittest

from receipt_builder import build_receipt_html


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


if __name__ == "__main__":
    unittest.main()
