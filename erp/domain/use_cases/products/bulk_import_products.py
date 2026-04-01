from __future__ import annotations

# Contexto del archivo:
# Caso de uso de importacion masiva de productos. Toma filas crudas desde CSV,
# las valida como lote y delega al repositorio una persistencia atomica con
# rollback si cualquier elemento del lote es invalido.

from dataclasses import dataclass

from erp.data.repositories.product_repository import ProductRepository
from erp.data.repositories.supplier_repository import SupplierRepository
from erp.domain.services.product_import_service import ProductImportService


@dataclass(slots=True)
class BulkImportProducts:
    products: ProductRepository
    suppliers: SupplierRepository
    import_service: ProductImportService

    def execute(self, rows: list[tuple]) -> int:
        prepared = self.import_service.prepare_batch(
            rows,
            supplier_exists=self.suppliers.exists,
            codigo_exists=self.products.codigo_exists,
        )
        return self.products.import_many(prepared)
