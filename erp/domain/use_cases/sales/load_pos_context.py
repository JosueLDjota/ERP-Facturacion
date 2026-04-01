from __future__ import annotations

# Contexto del archivo:
# Caso de uso de carga del contexto POS. Reune productos, clientes y descuentos
# necesarios para poblar la pantalla de ventas sin que la vista consulte SQL
# directo ni tenga que conocer de donde sale cada dataset.

from dataclasses import dataclass, field

from erp.data.repositories.sale_repository import SaleRepository


@dataclass(slots=True)
class POSContext:
    products: list[dict] = field(default_factory=list)
    clients: list[dict] = field(default_factory=list)
    discounts: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class LoadPOSContext:
    sales: SaleRepository

    def execute(
        self,
        *,
        load_products: bool = True,
        load_clients: bool = True,
        load_discounts: bool = True,
    ) -> POSContext:
        return POSContext(
            products=self.sales.list_products() if load_products else [],
            clients=self.sales.list_clients() if load_clients else [],
            discounts=self.sales.list_discounts() if load_discounts else [],
        )
