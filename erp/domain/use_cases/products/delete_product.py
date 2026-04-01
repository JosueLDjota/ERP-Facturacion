from __future__ import annotations

# Contexto del archivo:
# Caso de uso de eliminacion de productos. Existe para que la UI no invoque
# borrados directos sobre la base y para dejar un punto unico de evolucion si
# mas adelante se agregan reglas previas a la eliminacion.

from dataclasses import dataclass

from erp.data.repositories.product_repository import ProductRepository


@dataclass(slots=True)
class DeleteProduct:
    products: ProductRepository

    def execute(self, product_id: int) -> None:
        self.products.delete(int(product_id))
