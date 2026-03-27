"""
frames/__init__.py
Hace que frames sea un paquete importable
"""

from .dashboard import DashboardFrame
from .products import ProductFrame
from .suppliers import SupplierFrame
from .config import ConfigFrame
from .sales import SalesFrame
from .clients import ClientsFrame
from .registro import RegistroVentasFrame

__all__ = [
    "DashboardFrame",
    "ProductFrame",
    "SupplierFrame",
    "ConfigFrame",
    "SalesFrame",
    "ClientsFrame",
    "RegistroVentasFrame",
]
