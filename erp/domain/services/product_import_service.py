from __future__ import annotations

# Contexto del archivo:
# Servicio que normaliza y valida lotes de productos antes de importarlos.
# Su trabajo es preparar una coleccion segura para persistencia atomica, detectar
# duplicados internos y reutilizar las reglas de validacion del catalogo.

from dataclasses import dataclass

from erp.domain.entities.product import Product
from erp.domain.services.product_validation_service import ProductValidationService


@dataclass(slots=True)
class ProductImportService:
    validator: ProductValidationService

    def prepare_batch(
        self,
        rows: list[tuple],
        *,
        supplier_exists,
        codigo_exists,
    ) -> list[Product]:
        prepared = []
        seen_codes = set()

        for row in rows:
            nombre = row[0] if len(row) > 0 else ""
            descripcion = row[1] if len(row) > 1 else ""
            precio = row[2] if len(row) > 2 else ""
            stock = row[3] if len(row) > 3 else ""
            proveedor_id = row[4] if len(row) > 4 else ""
            codigo_producto = row[5] if len(row) > 5 else ""

            product = self.validator.validate(
                nombre=nombre,
                descripcion=descripcion,
                precio=precio,
                stock=stock,
                proveedor_id=proveedor_id,
                codigo_producto=codigo_producto,
                supplier_exists=supplier_exists,
                codigo_exists=codigo_exists,
            )

            normalized_code = str(product.codigo_producto or "").strip()
            if normalized_code:
                if normalized_code in seen_codes:
                    raise ValueError(f"Codigo de producto duplicado en importacion: {normalized_code}.")
                seen_codes.add(normalized_code)

            prepared.append(product)

        return prepared
