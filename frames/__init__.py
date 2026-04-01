"""
Paquete legacy de pantallas Tkinter.

Este namespace sigue agrupando las implementaciones fisicas actuales de la UI.
Se conserva porque gran parte de la aplicacion todavia instancia frames desde
esta carpeta, aunque la arquitectura nueva ya expone un namespace organizado en
`erp.ui.frames`.
"""

from .dashboard import DashboardFrame
from .products import ProductFrame
from .suppliers import SupplierFrame
from .config import ConfigFrame
from .sales import UnifiedPOSFrame, SalesFrame, WholesaleSalesFrame
from .clients import ClientsFrame
from .registro import RegistroVentasFrame

__all__ = [
    "DashboardFrame",
    "ProductFrame",
    "SupplierFrame",
    "ConfigFrame",
    "UnifiedPOSFrame",
    "SalesFrame",
    "WholesaleSalesFrame",
    "ClientsFrame",
    "RegistroVentasFrame",
]
