import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import DBManager


class ProductCodeMigrationTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "product_codes.db"

    def tearDown(self):
        self._temp_dir.cleanup()

    def test_existing_products_receive_unique_ean13_codes(self):
        db = DBManager(str(self.db_path))
        try:
            rows = db.fetch(
                """
                SELECT id, codigo_producto
                FROM Productos
                ORDER BY id
                """
            )
            self.assertTrue(rows)
            codes = [row[1] for row in rows]
            self.assertEqual(len(codes), len(set(codes)))
            self.assertTrue(all(code.isdigit() and len(code) == 13 for code in codes))

            index_rows = db.fetch(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                  AND name = ?
                """,
                (DBManager.PRODUCT_CODE_INDEX,),
            )
            self.assertEqual(index_rows[0][0], DBManager.PRODUCT_CODE_INDEX)
        finally:
            db.close()

    def test_existing_codigo_producto_is_preserved(self):
        db = DBManager(str(self.db_path))
        try:
            product_id = db.fetch("SELECT id FROM Productos ORDER BY id LIMIT 1")[0][0]
            preserved_code = "7501234567897"
            db.execute(
                "UPDATE Productos SET codigo_producto = ? WHERE id = ?",
                (preserved_code, product_id),
            )
            db._ensure_product_codes()

            stored_code = db.fetch(
                "SELECT codigo_producto FROM Productos WHERE id = ?",
                (product_id,),
            )[0][0]
            self.assertEqual(stored_code, preserved_code)
        finally:
            db.close()

    def test_duplicate_existing_codes_raise_integrity_error(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE Productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    precio REAL NOT NULL,
                    stock INTEGER NOT NULL,
                    proveedor_id INTEGER,
                    codigo_producto TEXT
                )
                """
            )
            conn.execute(
                "INSERT INTO Productos (nombre, precio, stock, codigo_producto) VALUES (?, ?, ?, ?)",
                ("Producto A", 10.0, 5, "7501234567897"),
            )
            conn.execute(
                "INSERT INTO Productos (nombre, precio, stock, codigo_producto) VALUES (?, ?, ?, ?)",
                ("Producto B", 15.0, 6, "7501234567897"),
            )
            conn.commit()
        finally:
            conn.close()

        db = object.__new__(DBManager)
        db.db_path = self.db_path
        db.is_new_database = False
        db.conn = sqlite3.connect(str(self.db_path))
        db.cursor = db.conn.cursor()
        db.last_error = None
        db._explicit_transaction_depth = 0
        db.conn.execute("PRAGMA foreign_keys = ON")
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db._ensure_product_codes()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
