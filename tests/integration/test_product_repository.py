import os
import shutil
import unittest
from pathlib import Path

from database import DBManager
from erp.data.repositories.product_repository import ProductRepository
from erp.domain.entities.product import Product


class ProductRepositoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path("tests_runtime") / "product_repository"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = os.path.join(str(self.temp_dir), "test_erp.db")
        self.db = DBManager(self.db_path)
        self.repo = ProductRepository(self.db)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

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
