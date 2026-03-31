import unittest

from erp.domain.services.invoice_calculator import calculate_invoice_totals


class InvoiceCalculatorTests(unittest.TestCase):
    def test_calculates_tax_when_prices_do_not_include_isv(self):
        totals = calculate_invoice_totals(
            items=[
                {"producto_id": 4, "nombre": "Laptop HP", "cantidad": 1, "precio_unitario": 650.0, "tax_rate": 0.15},
                {"producto_id": 1, "nombre": 'Monitor 27"', "cantidad": 1, "precio_unitario": 320.0, "tax_rate": 0.15},
            ],
            tax_included=False,
            payment_method="EFECTIVO",
            amount_received=1200.0,
        )

        self.assertEqual(totals.base_gravada_15, 970.0)
        self.assertEqual(totals.impuesto_15, 145.5)
        self.assertEqual(totals.total, 1115.5)
        self.assertEqual(totals.monto_recibido, 1200.0)
        self.assertEqual(totals.vuelto, 84.5)
        self.assertEqual(totals.validation_errors, [])

    def test_separates_base_and_tax_when_prices_include_isv(self):
        totals = calculate_invoice_totals(
            items=[
                {"producto_id": 4, "nombre": "Laptop HP", "cantidad": 1, "precio_unitario": 650.0, "tax_rate": 0.15},
                {"producto_id": 1, "nombre": 'Monitor 27"', "cantidad": 1, "precio_unitario": 320.0, "tax_rate": 0.15},
            ],
            tax_included=True,
            payment_method="TRANSFERENCIA",
            amount_received=1000.0,
        )

        self.assertEqual(totals.base_gravada_15, 843.48)
        self.assertEqual(totals.impuesto_15, 126.52)
        self.assertEqual(totals.total, 970.0)
        self.assertEqual(totals.monto_recibido, 970.0)
        self.assertEqual(totals.vuelto, 0.0)
        self.assertEqual(totals.validation_errors, [])

    def test_with_tax_included_45_shows_base_and_tax_correctly(self):
        totals = calculate_invoice_totals(
            items=[
                {"producto_id": 2, "nombre": "Teclado Mecanico", "cantidad": 1, "precio_unitario": 45.0, "tax_rate": 0.15},
            ],
            tax_included=True,
            payment_method="EFECTIVO",
            amount_received=50.0,
        )

        self.assertEqual(totals.base_gravada_15, 39.13)
        self.assertEqual(totals.impuesto_15, 5.87)
        self.assertEqual(totals.total, 45.0)
        self.assertEqual(totals.vuelto, 5.0)

    def test_flags_insufficient_cash_payment(self):
        totals = calculate_invoice_totals(
            items=[
                {"producto_id": 4, "nombre": "Laptop HP", "cantidad": 1, "precio_unitario": 650.0, "tax_rate": 0.15},
            ],
            tax_included=False,
            payment_method="EFECTIVO",
            amount_received=700.0,
        )

        self.assertIn("El monto recibido en efectivo no puede ser menor al total.", totals.validation_errors)


if __name__ == "__main__":
    unittest.main()
