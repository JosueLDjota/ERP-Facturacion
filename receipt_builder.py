"""
Wrapper de compatibilidad para utilidades de recibos.

La implementacion real vive en `erp.infrastructure.printing.receipt_builder`.
Se conserva este archivo para mantener estabilidad en pruebas y modulos legacy
que aun importan desde la raiz del proyecto.
"""

from erp.infrastructure.printing.receipt_builder import (
    DEFAULT_EMPRESA,
    DEFAULT_RECEIPT_LABELS,
    build_receipt_html,
    build_receipt_preview_text,
    build_receipt_view_model,
    default_receipt_labels,
    load_receipt_company,
    load_receipt_labels,
    load_receipt_render_settings,
)

__all__ = [
    "DEFAULT_EMPRESA",
    "DEFAULT_RECEIPT_LABELS",
    "build_receipt_html",
    "build_receipt_preview_text",
    "build_receipt_view_model",
    "default_receipt_labels",
    "load_receipt_company",
    "load_receipt_labels",
    "load_receipt_render_settings",
]
