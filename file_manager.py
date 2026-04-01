"""
Wrapper de compatibilidad para importacion y exportacion de archivos.

La implementacion real vive en `erp.infrastructure.io.file_manager`. Este
archivo se mantiene para no romper imports legacy mientras el codigo antiguo se
migra gradualmente a la estructura nueva.
"""

from erp.infrastructure.io.file_manager import FileManager, center_window

__all__ = ["FileManager", "center_window"]
