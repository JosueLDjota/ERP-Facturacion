"""
Wrapper de compatibilidad para generacion de recibos HTML.

La implementacion real vive en `erp.infrastructure.printing.receipt_builder`.
Se conserva este archivo para mantener estabilidad en pruebas y modulos legacy
que aun importan desde la raiz del proyecto.
"""

from erp.infrastructure.printing.receipt_builder import DEFAULT_EMPRESA, build_receipt_html

__all__ = ["DEFAULT_EMPRESA", "build_receipt_html"]
