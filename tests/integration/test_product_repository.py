import os
import tempfile
import unittest

from database import DBManager
from erp.data.repositories.product_repository import ProductRepository
from erp.domain.entities.product import Product


class ProductRepositoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_erp.db")
        self.db = DBManager(self.db_path)
        self.repo = ProductRepository(self.db)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_insert_and_list_product(self):
        category_id = self.db.fetch("SELECT id FROM Categorias WHERE nombre = 'Laptops' LIMIT 1")[0][0]
        brand_id = self.db.fetch("SELECT id FROM Marcas WHERE nombre = 'Acer' LIMIT 1")[0][0]
        self.repo.save(
            Product(
                id=None,
                nombre="Producto test",
                descripcion="Demo",
                precio=20.0,
                stock=5,
                proveedor_id=1,
                categoria_id=category_id,
                marca_id=brand_id,
            )
        )
        rows = self.repo.search_by_name("test")
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0].nombre, "Producto test")
        self.assertEqual(rows[0].categoria_id, category_id)
        self.assertEqual(rows[0].marca_id, brand_id)


if __name__ == "__main__":
    unittest.main()
