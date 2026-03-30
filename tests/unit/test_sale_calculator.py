import unittest

from erp.domain.services.sale_calculator import CartLine, calculate_sale_totals


class SaleCalculatorTests(unittest.TestCase):
    def test_calculates_totals_with_discount(self):
        totals = calculate_sale_totals(
            [
                CartLine(producto_id=1, cantidad=2, precio_unitario=100.0, descuento_porcentaje=0.1),
                CartLine(producto_id=2, cantidad=1, precio_unitario=50.0, descuento_porcentaje=0.0),
            ]
        )
        self.assertEqual(totals.subtotal, 250.0)
        self.assertEqual(totals.descuento_total, 20.0)
        self.assertEqual(totals.total, 230.0)


if __name__ == "__main__":
    unittest.main()
