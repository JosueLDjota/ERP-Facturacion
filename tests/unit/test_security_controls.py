import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import DBManager
from erp.domain.services.access_control import (
    allowed_sections_for_role,
    can_manage_legacy_registry,
)


class SecurityControlsTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "erp_test.db"

    def tearDown(self):
        self._temp_dir.cleanup()

    def test_seeded_admin_password_is_stored_as_hash(self):
        db = DBManager(str(self.db_path))
        try:
            stored_password = db.fetch(
                "SELECT contrasena FROM Usuarios WHERE usuario = ?",
                ("admin",),
            )[0][0]
            self.assertTrue(DBManager.is_password_hashed(stored_password))
            self.assertEqual(db.authenticate_user("admin", "1234")[1], "Administrador")
        finally:
            db.close()

    def test_plaintext_passwords_are_migrated_on_startup(self):
        db = DBManager(str(self.db_path))
        try:
            db.execute(
                "INSERT INTO Usuarios (nombre, usuario, contrasena, rol) VALUES (?, ?, ?, ?)",
                ("Legacy User", "legacy", "secreto", "Administrador"),
            )
        finally:
            db.close()

        reopened = DBManager(str(self.db_path))
        try:
            stored_password = reopened.fetch(
                "SELECT contrasena FROM Usuarios WHERE usuario = ?",
                ("legacy",),
            )[0][0]
            self.assertTrue(DBManager.is_password_hashed(stored_password))
            self.assertIsNotNone(reopened.authenticate_user("legacy", "secreto"))
        finally:
            reopened.close()

    def test_existing_database_does_not_reseed_default_admin_when_users_are_deleted(self):
        db = DBManager(str(self.db_path))
        db.close()

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("DELETE FROM Usuarios")
            conn.commit()
        finally:
            conn.close()

        reopened = DBManager(str(self.db_path))
        try:
            total_users = reopened.fetch("SELECT COUNT(*) FROM Usuarios")[0][0]
            self.assertEqual(total_users, 0)
            self.assertFalse(reopened.has_users())
        finally:
            reopened.close()

    def test_create_pos_sale_rolls_back_if_any_item_fails(self):
        db = DBManager(str(self.db_path))
        try:
            product_id, product_name, price, stock = db.fetch(
                "SELECT id, nombre, precio, stock FROM Productos ORDER BY id LIMIT 1"
            )[0]

            cart_data = {
                int(product_id): {
                    "nombre": product_name,
                    "cantidad": 1,
                    "precio_unitario": float(price),
                    "descuento_porcentaje": 0.0,
                },
                999999: {
                    "nombre": "Producto inexistente",
                    "cantidad": 1,
                    "precio_unitario": 10.0,
                    "descuento_porcentaje": 0.0,
                },
            }

            with self.assertRaises(ValueError):
                db.create_pos_sale(
                    sale_id="VENTA-ROLLBACK",
                    fecha="2026-03-31 10:00:00",
                    total=float(price) + 10.0,
                    pagado=float(price) + 10.0,
                    vuelto=0.0,
                    metodo_pago="EFECTIVO",
                    usuario_id=1,
                    cliente_id=None,
                    tipo_recibo="POS-NORMAL",
                    cart_data=cart_data,
                )

            current_stock = db.fetch(
                "SELECT stock FROM Productos WHERE id = ?",
                (product_id,),
            )[0][0]
            sales_count = db.fetch(
                "SELECT COUNT(*) FROM Ventas WHERE id = ?",
                ("VENTA-ROLLBACK",),
            )[0][0]
            detail_count = db.fetch(
                "SELECT COUNT(*) FROM DetalleVenta WHERE venta_id = ?",
                ("VENTA-ROLLBACK",),
            )[0][0]

            self.assertEqual(current_stock, stock)
            self.assertEqual(sales_count, 0)
            self.assertEqual(detail_count, 0)
        finally:
            db.close()


class AccessControlTests(unittest.TestCase):
    def test_admin_role_has_sensitive_access(self):
        sections = allowed_sections_for_role("Administrador")
        self.assertIn("Configuración", sections)
        self.assertIn("Productos", sections)
        self.assertTrue(can_manage_legacy_registry("Administrador"))

    def test_sales_role_keeps_pos_access_but_not_legacy_cleanup(self):
        sections = allowed_sections_for_role("Vendedor")
        self.assertIn("Ventas (POS)", sections)
        self.assertIn("Ventas Mayoristas", sections)
        self.assertNotIn("Configuración", sections)
        self.assertFalse(can_manage_legacy_registry("Vendedor"))


if __name__ == "__main__":
    unittest.main()
