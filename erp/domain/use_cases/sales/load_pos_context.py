from __future__ import annotations

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
