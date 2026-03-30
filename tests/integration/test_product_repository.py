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
        self.repo.save(
            Product(
                id=None,
                nombre="Producto test",
                descripcion="Demo",
                precio=20.0,
                stock=5,
                proveedor_id=1,
            )
        )
        rows = self.repo.search_by_name("test")
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0].nombre, "Producto test")


if __name__ == "__main__":
    unittest.main()
