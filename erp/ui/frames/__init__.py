"""
Namespace organizado de UI.

Este paquete ofrece un punto de importacion consistente para pantallas del ERP
desde la arquitectura nueva. Por ahora reexporta implementaciones legacy de
`frames/` mientras la migracion fisica de la UI se completa por etapas.
"""

from frames import (
    ClientsFrame,
    ConfigFrame,
    DashboardFrame,
    ProductFrame,
    RegistroVentasFrame,
    SupplierFrame,
    UnifiedPOSFrame,
    SalesFrame,
    WholesaleSalesFrame,
)

__all__ = [
    "ClientsFrame",
    "ConfigFrame",
    "DashboardFrame",
    "ProductFrame",
    "RegistroVentasFrame",
    "SupplierFrame",
    "UnifiedPOSFrame",
    "SalesFrame",
    "WholesaleSalesFrame",
]
