"""
Wrapper legacy para la pantalla de ventas mayoristas.

La implementacion operativa vive en `frames.sales` para que ventas normal y
mayorista compartan exactamente la misma logica de carrito, cobro, recibos e
inventario. Este modulo se conserva solo por compatibilidad con imports
historicos.
"""

from .sales import WholesaleSalesFrame

__all__ = ["WholesaleSalesFrame"]
