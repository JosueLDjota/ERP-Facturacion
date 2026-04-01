from __future__ import annotations

# Contexto del archivo:
# Caso de uso para reajuste masivo de precios del catalogo. Separa la politica
# de calculo del repositorio que persiste cambios y entrega a la UI un resumen
# claro para vista previa y confirmacion.

from dataclasses import dataclass

from erp.data.repositories.product_repository import ProductRepository
from erp.domain.services.price_adjustment_service import PriceAdjustmentService


@dataclass(slots=True)
class AdjustPricesResult:
    updated: int
    total_products: int
    average_price: float


@dataclass(slots=True)
class AdjustPrices:
    products: ProductRepository
    price_adjuster: PriceAdjustmentService

    def get_preview(self) -> AdjustPricesResult:
        stats = self.products.get_price_stats()
        return AdjustPricesResult(
            updated=0,
            total_products=int(stats["total_products"]),
            average_price=float(stats["average_price"]),
        )

    def execute(self, *, pct: float, step: float) -> AdjustPricesResult:
        updated = self.products.adjust_prices(pct=float(pct), step=float(step), adjuster=self.price_adjuster)
        stats = self.products.get_price_stats()
        return AdjustPricesResult(
            updated=updated,
            total_products=int(stats["total_products"]),
            average_price=float(stats["average_price"]),
        )
