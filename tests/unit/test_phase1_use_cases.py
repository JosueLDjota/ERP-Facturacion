import tempfile
import unittest
from pathlib import Path

from database import DBManager
from erp.data.repositories.sale_repository import SaleRepository
from erp.data.repositories.user_repository import UserRepository
from erp.domain.services.receipt_service import ReceiptService
from erp.domain.use_cases.auth.login_user import LoginUser
from erp.domain.use_cases.sales.create_pos_sale import CreatePOSSale
from erp.domain.use_cases.sales.load_pos_context import LoadPOSContext


class Phase1UseCasesTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "erp_phase1.db"
        self.db = DBManager(str(self.db_path))
        self.sale_repository = SaleRepository(self.db)
        self.user_repository = UserRepository(self.db)
        self.receipt_service = ReceiptService()

    def tearDown(self):
        self.db.close()
        self._temp_dir.cleanup()

    def test_login_user_accepts_seeded_admin(self):
        response = LoginUser(self.user_repository).execute("admin", "1234")

        self.assertTrue(response.ok)
        self.assertEqual(response.user[1], "Administrador")

    def test_login_user_rejects_invalid_credentials(self):
        response = LoginUser(self.user_repository).execute("admin", "incorrecta")

        self.assertFalse(response.ok)
        self.assertEqual(response.status, "invalid_credentials")

    def test_load_pos_context_returns_lists_for_ui(self):
        context = LoadPOSContext(self.sale_repository).execute()

        self.assertIsInstance(context.products, list)
        self.assertIsInstance(context.clients, list)
        self.assertIsInstance(context.discounts, list)
        self.assertGreater(len(context.products), 0)

    def test_create_pos_sale_persists_transaction_and_builds_receipt(self):
        product = next(item for item in self.sale_repository.list_products() if item["stock"] > 0)
        original_stock = product["stock"]
        unit_price = float(product["precio"])
        sale_data = {
            "venta_id": "FASE1-OK",
            "fecha": "2026-04-01 10:00:00",
            "pagado": unit_price,
            "metodo_pago": "EFECTIVO",
            "modo": "NORMAL",
            "cliente_id": None,
            "cart_snapshot": {
                int(product["id"]): {
                    "nombre": product["nombre"],
                    "cantidad": 1,
                    "precio_unitario": unit_price,
                    "descuento_porcentaje": 0.0,
                }
            },
            "tax_included": True,
        }

        result = CreatePOSSale(self.sale_repository, self.receipt_service).execute(
            sale_data,
            usuario_id=1,
            preview_mode="ticket",
        )

        stored_sale = self.db.fetch("SELECT id, total FROM Ventas WHERE id = ?", ("FASE1-OK",))
        current_stock = self.db.fetch("SELECT stock FROM Productos WHERE id = ?", (product["id"],))[0][0]

        self.assertEqual(stored_sale[0][0], "FASE1-OK")
        self.assertAlmostEqual(float(stored_sale[0][1]), result.total, places=2)
        self.assertEqual(current_stock, original_stock - 1)
        self.assertIn("FASE1-OK", result.receipt_html)
        self.assertIn("FACTURA", result.receipt_html)

    def test_create_pos_sale_rolls_back_when_stock_is_insufficient(self):
        product = next(item for item in self.sale_repository.list_products() if item["stock"] > 0)
        original_stock = product["stock"]
        requested_quantity = original_stock + 1
        sale_data = {
            "venta_id": "FASE1-ROLLBACK",
            "fecha": "2026-04-01 10:05:00",
            "pagado": float(product["precio"]) * requested_quantity,
            "metodo_pago": "EFECTIVO",
            "modo": "NORMAL",
            "cliente_id": None,
            "cart_snapshot": {
                int(product["id"]): {
                    "nombre": product["nombre"],
                    "cantidad": requested_quantity,
                    "precio_unitario": float(product["precio"]),
                    "descuento_porcentaje": 0.0,
                }
            },
            "tax_included": True,
        }

        with self.assertRaises(Exception):
            CreatePOSSale(self.sale_repository, self.receipt_service).execute(
                sale_data,
                usuario_id=1,
                preview_mode="ticket",
            )

        sale_count = self.db.fetch("SELECT COUNT(*) FROM Ventas WHERE id = ?", ("FASE1-ROLLBACK",))[0][0]
        current_stock = self.db.fetch("SELECT stock FROM Productos WHERE id = ?", (product["id"],))[0][0]

        self.assertEqual(sale_count, 0)
        self.assertEqual(current_stock, original_stock)

    def test_receipt_service_uses_fixed_internal_labels_and_business_data_from_db(self):
        self.db.set_config("empresa_nombre", "Mi ERP")
        self.db.set_config("recibo_doc_title", "RECIBO CENTRAL")
        self.db.set_config("recibo_template", "<html><body><h1>{{DOC_TITLE}}</h1><div>{{NOMBRE_NEGOCIO}}</div></body></html>")
        receipt_service = ReceiptService(self.db.get_config)

        html = receipt_service.build_html(
            venta_id="CFG-001",
            fecha="2026-04-01 10:00:00",
            total=10.0,
            monto_pagado=10.0,
            vuelto=0.0,
            cart_data={
                1: {
                    "nombre": "Producto demo",
                    "cantidad": 1,
                    "precio_unitario": 10.0,
                    "descuento_porcentaje": 0.0,
                }
            },
            metodo_pago="EFECTIVO",
        )

        self.assertIn("FACTURA", html)
        self.assertIn("Mi ERP", html)


if __name__ == "__main__":
    unittest.main()
