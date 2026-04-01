"""
Namespace organizado para componentes transversales de UI.

Este archivo reexporta el gestor de notificaciones mientras la implementacion
fisica aun permanece en `frames/`. Sirve como punto de entrada estable para la
arquitectura nueva sin forzar un movimiento riesgoso de todo el modulo.
"""

from frames.notificaciones import NotificationManager

__all__ = ["NotificationManager"]
