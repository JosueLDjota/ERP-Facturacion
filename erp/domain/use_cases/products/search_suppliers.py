from __future__ import annotations

# Contexto del archivo:
# Caso de uso de busqueda parcial de proveedores. Se usa sobre todo en
# formularios de productos para sugerencias y seleccion por nombre sin depender
# de consultas SQL embebidas en la interfaz.

from dataclasses import dataclass

from erp.data.repositories.supplier_repository import SupplierRepository


@dataclass(slots=True)
class SearchSuppliers:
    suppliers: SupplierRepository

    def execute(self, search_term: str = "", limit: int = 8) -> list[dict]:
        return self.suppliers.search_by_name(search_term, limit=limit)
