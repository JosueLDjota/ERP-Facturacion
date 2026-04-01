import tempfile
import unittest
from pathlib import Path

from database import DBManager
from erp.data.repositories.product_repository import ProductRepository
from erp.data.repositories.product_taxonomy_repository import ProductTaxonomyRepository
from erp.data.repositories.supplier_repository import SupplierRepository
from erp.domain.services.price_adjustment_service import PriceAdjustmentService
from erp.domain.services.product_import_service import ProductImportService
from erp.domain.services.product_validation_service import ProductValidationService
from erp.domain.use_cases.products.adjust_prices import AdjustPrices
from erp.domain.use_cases.products.bulk_import_products import BulkImportProducts
from erp.domain.use_cases.products.list_products import ListProducts
from erp.domain.use_cases.products.save_product import SaveProduct


class ProductPhase2UseCasesTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "erp_products_phase2.db"
        self.db = DBManager(str(self.db_path))
        self.products = ProductRepository(self.db)
        self.suppliers = SupplierRepository(self.db)
        self.taxonomy = ProductTaxonomyRepository(self.db)
        self.validator = ProductValidationService()
        self.import_service = ProductImportService(self.validator)

    def tearDown(self):
        self.db.close()
        self._temp_dir.cleanup()

    def test_save_product_creates_with_codigo_producto(self):
        category_id = self.db.fetch("SELECT id FROM Categorias WHERE nombre = 'Accesorios' LIMIT 1")[0][0]
        brand_id = self.db.fetch("SELECT id FROM Marcas WHERE nombre = 'Logitech' LIMIT 1")[0][0]
        result = SaveProduct(self.products, self.suppliers, self.validator, self.taxonomy).execute(
            nombre="Producto Fase 2",
            descripcion="Prueba",
            precio="L 150.50",
            stock="8",
            proveedor_id="1",
            codigo_producto="7501234567890",
            categoria_id=str(category_id),
            marca_id=str(brand_id),
        )

        stored = self.products.get_detail(result.product_id)
        self.assertTrue(result.created)
        self.assertEqual(stored["codigo_producto"], "7501234567890")
        self.assertEqual(stored["categoria_id"], category_id)
        self.assertEqual(stored["marca_id"], brand_id)

    def test_save_product_rejects_duplicate_codigo_producto(self):
        saver = SaveProduct(self.products, self.suppliers, self.validator, self.taxonomy)
        saver.execute(
            nombre="Producto A",
            descripcion="",
            precio="10",
            stock="2",
            proveedor_id="1",
            codigo_producto="7501234567890",
        )

        with self.assertRaises(ValueError):
            saver.execute(
                nombre="Producto B",
                descripcion="",
                precio="12",
                stock="2",
                proveedor_id="1",
                codigo_producto="7501234567890",
            )

    def test_list_products_searches_by_codigo_producto(self):
        saver = SaveProduct(self.products, self.suppliers, self.validator, self.taxonomy)
        saver.execute(
            nombre="Escaner Test",
            descripcion="",
            precio="15",
            stock="4",
            proveedor_id="1",
            codigo_producto="7890001112223",
        )

        matches = ListProducts(self.products).execute("1112223")
        self.assertTrue(any(item["codigo_producto"] == "7890001112223" for item in matches))

    def test_list_products_searches_by_category_and_brand(self):
        saver = SaveProduct(self.products, self.suppliers, self.validator, self.taxonomy)
        category_id = self.db.fetch("SELECT id FROM Categorias WHERE nombre = 'Monitores' LIMIT 1")[0][0]
        brand_id = self.db.fetch("SELECT id FROM Marcas WHERE nombre = 'Samsung' LIMIT 1")[0][0]
        saver.execute(
            nombre="Monitor Curvo 27",
            descripcion="",
            precio="4200",
            stock="3",
            proveedor_id="1",
            codigo_producto="7890001112299",
            categoria_id=str(category_id),
            marca_id=str(brand_id),
        )

        category_matches = ListProducts(self.products).execute("monitores")
        brand_matches = ListProducts(self.products).execute("samsung")

        self.assertTrue(any(item["categoria_nombre"] == "Monitores" for item in category_matches))
        self.assertTrue(any(item["marca_nombre"] == "Samsung" for item in brand_matches))

    def test_bulk_import_products_rolls_back_full_batch_on_invalid_supplier(self):
        before_count = self.db.fetch("SELECT COUNT(*) FROM Productos")[0][0]
        rows = [
            ("Importado 1", "Desc", 25.0, 3, 1, "7501234567891"),
            ("Importado 2", "Desc", 30.0, 2, 999999, "7501234567892"),
        ]

        with self.assertRaises(ValueError):
            BulkImportProducts(self.products, self.suppliers, self.import_service).execute(rows)

        after_count = self.db.fetch("SELECT COUNT(*) FROM Productos")[0][0]
        self.assertEqual(before_count, after_count)

    def test_adjust_prices_updates_existing_products(self):
        first_product = self.products.list_all()[0]
        original_price = float(first_product.precio)

        result = AdjustPrices(self.products, PriceAdjustmentService()).execute(pct=10, step=0.5)
        updated = self.products.get_detail(first_product.id)

        self.assertGreater(result.updated, 0)
        self.assertNotEqual(round(original_price, 2), round(updated["precio"], 2))


if __name__ == "__main__":
    unittest.main()
