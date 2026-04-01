from __future__ import annotations

# Contexto del archivo:
# Caso de uso de alta y actualizacion de productos. Orquesta validacion de
# negocio, verificacion de proveedor y persistencia del catalogo, devolviendo un
# resultado simple para que la pantalla solo muestre mensajes y refresque datos.

from dataclasses import dataclass

from erp.data.repositories.product_repository import ProductRepository
from erp.data.repositories.supplier_repository import SupplierRepository
from erp.domain.services.product_validation_service import ProductValidationService


@dataclass(slots=True)
class SaveProductResult:
    product_id: int
    created: bool


@dataclass(slots=True)
class SaveProduct:
    products: ProductRepository
    suppliers: SupplierRepository
    validator: ProductValidationService

    def execute(
        self,
        *,
        nombre: str,
        precio,
        stock,
        proveedor_id,
        descripcion: str = "",
        codigo_producto: str = "",
        product_id: int | None = None,
    ) -> SaveProductResult:
        product = self.validator.validate(
            nombre=nombre,
            precio=precio,
            stock=stock,
            proveedor_id=proveedor_id,
            descripcion=descripcion,
            codigo_producto=codigo_producto,
            current_product_id=product_id,
            supplier_exists=self.suppliers.exists,
            codigo_exists=self.products.codigo_exists,
        )
        created = product.id is None
        saved_id = self.products.save(product)
        return SaveProductResult(product_id=saved_id, created=created)
