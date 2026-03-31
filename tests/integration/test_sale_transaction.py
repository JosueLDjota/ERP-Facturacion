import os
import shutil
import unittest
from pathlib import Path

from database import DBManager
from erp.domain.use_cases.receipt_use_case import ReceiptStorageError
from erp.domain.use_cases.sale_use_case import SaleProcessingError, SaleService


class FailingReceiptStorage:
    def __init__(self, db):
        self.db = db

    def save_receipt(self, html_content: str, venta_id: str) -> str:
        raise ReceiptStorageError("Ruta sin permisos")


class SaleTransactionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path("tests_runtime") / "sale_transaction"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = os.path.join(str(self.temp_dir), "sales_test.db")
        self.db = DBManager(self.db_path)
        self.service = SaleService(self.db, FailingReceiptStorage(self.db))

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def test_sale_rolls_back_when_receipt_storage_fails(self):
        product = self.db.fetch_one("SELECT id, stock FROM Productos ORDER BY id LIMIT 1")
        self.assertIsNotNone(product)
        product_id, initial_stock = int(product[0]), int(product[1])

        with self.assertRaises(SaleProcessingError):
            self.service.process_sale(
                sale_id="VENTA-ROLLBACK-001",
                fecha="2026-03-30 10:00:00",
                items=[
                    {
                        "producto_id": product_id,
                        "nombre": "Producto rollback",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "descuento_porcentaje": 0,
                        "tax_rate": 0.15,
                        "tax_exempt": False,
                    }
                ],
                usuario_id=1,
                cliente_id=None,
                metodo_pago="EFECTIVO",
                amount_received=115.0,
                tipo_recibo="POS-NORMAL",
                receipt_mode="ticket",
                tax_included=False,
            )

        sale = self.db.fetch_one("SELECT id FROM Ventas WHERE id = ?", ("VENTA-ROLLBACK-001",))
        self.assertIsNone(sale)
        detail = self.db.fetch_one("SELECT id FROM DetalleVenta WHERE venta_id = ?", ("VENTA-ROLLBACK-001",))
        self.assertIsNone(detail)
        current_stock = self.db.fetch_one("SELECT stock FROM Productos WHERE id = ?", (product_id,))
        self.assertEqual(int(current_stock[0]), initial_stock)


if __name__ == "__main__":
    unittest.main()
