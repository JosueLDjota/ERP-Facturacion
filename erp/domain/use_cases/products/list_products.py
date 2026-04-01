from __future__ import annotations

# Contexto del archivo:
# Caso de uso de consulta del catalogo de productos para la UI. Encapsula la
# busqueda por texto y por codigo de producto en un contrato simple para
# formularios y tablas legacy.

from dataclasses import dataclass

from erp.data.repositories.product_repository import ProductRepository


@dataclass(slots=True)
class ListProducts:
    products: ProductRepository

    def execute(self, search_term: str = "") -> list[dict]:
        return self.products.list_for_ui(search_term)
