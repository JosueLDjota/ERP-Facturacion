from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class CartLine:
    producto_id: int
    cantidad: int
    precio_unitario: float
    descuento_porcentaje: float = 0.0


@dataclass(slots=True)
class SaleTotals:
    subtotal: float
    descuento_total: float
    total: float


def calculate_sale_totals(lines: Iterable[CartLine]) -> SaleTotals:
    subtotal = 0.0
    discount = 0.0
    for line in lines:
        line_subtotal = float(line.precio_unitario) * int(line.cantidad)
        line_discount = line_subtotal * float(line.descuento_porcentaje or 0)
        subtotal += line_subtotal
        discount += line_discount

    total = subtotal - discount
    return SaleTotals(
        subtotal=round(subtotal, 2),
        descuento_total=round(discount, 2),
        total=round(total, 2),
    )
