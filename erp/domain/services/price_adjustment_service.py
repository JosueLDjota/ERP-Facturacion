from __future__ import annotations

# Contexto del archivo:
# Servicio puro para calcular ajustes porcentuales y redondeos de precio.
# Se mantiene aislado para que la politica de recalculo masivo no dependa de la
# UI ni del repositorio que finalmente persiste los precios.

from dataclasses import dataclass


@dataclass(slots=True)
class PriceAdjustmentService:
    def normalize(self, price: float, pct: float, step: float) -> float:
        if step <= 0:
            raise ValueError("El redondeo debe ser mayor que 0.")
        adjusted_price = float(price) * (1 + (float(pct) / 100.0))
        adjusted_price = round(adjusted_price / float(step)) * float(step)
        return max(0.01, round(adjusted_price, 2))
