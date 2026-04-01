import tempfile
import unittest
from pathlib import Path

from database import DBManager


class ProductTaxonomyMigrationTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "product_taxonomy.db"

    def tearDown(self):
        self._temp_dir.cleanup()

    def test_schema_and_seed_catalog_are_created(self):
        db = DBManager(str(self.db_path))
        try:
            tables = {
                row[0]
                for row in db.fetch(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                )
            }
            self.assertIn("Categorias", tables)
            self.assertIn("Marcas", tables)

            product_columns = {
                row[1]
                for row in db.fetch("PRAGMA table_info(Productos)")
            }
            self.assertIn("categoria_id", product_columns)
            self.assertIn("marca_id", product_columns)

            categories = {
                row[0]
                for row in db.fetch("SELECT nombre FROM Categorias")
            }
            brands = {
                row[0]
                for row in db.fetch("SELECT nombre FROM Marcas")
            }
            self.assertIn("Laptops", categories)
            self.assertIn("Otros", categories)
            self.assertIn("HP", brands)
            self.assertIn("Generica", brands)
        finally:
            db.close()

    def test_products_are_classified_without_overwriting_existing_assignments(self):
        db = DBManager(str(self.db_path))
        try:
            acer_id = db.fetch("SELECT id FROM Marcas WHERE nombre = 'Acer'")[0][0]
            hp_id = db.fetch("SELECT id FROM Marcas WHERE nombre = 'HP'")[0][0]
            dell_id = db.fetch("SELECT id FROM Marcas WHERE nombre = 'Dell'")[0][0]
            generic_id = db.fetch("SELECT id FROM Marcas WHERE nombre = 'Generica'")[0][0]
            laptops_id = db.fetch("SELECT id FROM Categorias WHERE nombre = 'Laptops'")[0][0]
            consumibles_id = db.fetch("SELECT id FROM Categorias WHERE nombre = 'Consumibles'")[0][0]
            wearables_id = db.fetch("SELECT id FROM Categorias WHERE nombre = 'Wearables'")[0][0]
            monitores_id = db.fetch("SELECT id FROM Categorias WHERE nombre = 'Monitores'")[0][0]

            product_a = db.execute(
                """
                INSERT INTO Productos (nombre, descripcion, precio, stock, proveedor_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Laptop Acer Aspire 5", "Notebook empresarial", 25000.0, 4, 1),
            )
            product_b = db.execute(
                """
                INSERT INTO Productos (nombre, descripcion, precio, stock, proveedor_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Toner HP LaserJet", "Consumible para impresion", 1200.0, 8, 1),
            )
            product_c = db.execute(
                """
                INSERT INTO Productos (nombre, descripcion, precio, stock, proveedor_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("SmartFit3", "Reloj inteligente, diseñado para deporte.", 1800.0, 6, 1),
            )
            product_d = db.execute(
                """
                INSERT INTO Productos (
                    nombre, descripcion, precio, stock, proveedor_id, marca_id, categoria_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("Laptop Acer conservada", "No debe sobrescribirse", 20000.0, 2, 1, dell_id, monitores_id),
            )

            report = db.ensure_product_taxonomy()

            assigned_a = db.fetch(
                "SELECT marca_id, categoria_id FROM Productos WHERE id = ?",
                (product_a,),
            )[0]
            assigned_b = db.fetch(
                "SELECT marca_id, categoria_id FROM Productos WHERE id = ?",
                (product_b,),
            )[0]
            assigned_c = db.fetch(
                "SELECT marca_id, categoria_id FROM Productos WHERE id = ?",
                (product_c,),
            )[0]
            preserved_d = db.fetch(
                "SELECT marca_id, categoria_id FROM Productos WHERE id = ?",
                (product_d,),
            )[0]

            self.assertEqual(assigned_a, (acer_id, laptops_id))
            self.assertEqual(assigned_b, (hp_id, consumibles_id))
            self.assertEqual(assigned_c, (generic_id, wearables_id))
            self.assertEqual(preserved_d, (dell_id, monitores_id))
            self.assertGreaterEqual(report["products_updated_brand"], 3)
            self.assertGreaterEqual(report["products_updated_category"], 3)
        finally:
            db.close()

    def test_migration_is_idempotent_and_can_write_summary(self):
        db = DBManager(str(self.db_path))
        try:
            first_report = db.ensure_product_taxonomy()
            second_report = db.ensure_product_taxonomy()

            self.assertEqual(second_report["tables_created"], [])
            self.assertEqual(second_report["columns_added"], [])
            self.assertEqual(second_report["brands_inserted"], [])
            self.assertEqual(second_report["categories_inserted"], [])
            self.assertEqual(second_report["products_updated_brand"], 0)
            self.assertEqual(second_report["products_updated_category"], 0)

            summary_path = Path(self._temp_dir.name) / "resumen_taxonomia.mb"
            written_path = db.write_product_taxonomy_summary(first_report, summary_path)
            self.assertEqual(written_path, summary_path)
            summary_text = summary_path.read_text(encoding="utf-8")
            self.assertIn("Resumen de migracion de catalogo", summary_text)
            self.assertIn("Productos clasificados como Generica", summary_text)
            self.assertIn("Productos clasificados como Otros", summary_text)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
