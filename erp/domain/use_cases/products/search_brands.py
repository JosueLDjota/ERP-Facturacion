from __future__ import annotations

# Contexto del archivo:
# Caso de uso de busqueda parcial de marcas para formularios de productos.
# Permite sugerencias por nombre sin depender de SQL embebido en la UI.

from dataclasses import dataclass

from erp.data.repositories.product_taxonomy_repository import ProductTaxonomyRepository


@dataclass(slots=True)
class SearchBrands:
    taxonomy: ProductTaxonomyRepository

    def execute(self, search_term: str = "", limit: int = 8) -> list[dict]:
        return self.taxonomy.search_brands_by_name(search_term, limit=limit)
