# -*- coding: utf-8 -*-
"""
notificaciones.py
Sistema de notificaciones push profesional para ERP con gestión avanzada.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
import hashlib
from collections import deque
import threading
import queue
import logging


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationPayload:
    id: int
    notification_key: str
    title: str
    message: str
    type: str
    type_config: Dict[str, Any]
    timestamp: datetime
    action_callback: Optional[Callable]
    action_data: Any
    read: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'notification_key': self.notification_key,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'type_config': self.type_config,
            'timestamp': self.timestamp,
            'action_callback': self.action_callback,
            'action_data': self.action_data,
            'read': self.read,
        }

# ============================================================================
# CONSTANTES Y CONFIGURACIÓN (Definidas localmente)
# ============================================================================

# Paleta de colores (definida localmente)
PALETTE = {
    'blue_soft': '#f0f4f8',
    'blue_primary': '#3498db',
    'blue_dark': '#2c3e50',
    'white': '#ffffff',
    'black': '#000000',
    'gray_text': '#7f8c8d',
    'gray_border': '#e0e0e0',
    'surface_alt': '#ecf0f1',
    'danger': '#e74c3c'
}

# Fuentes (definidas localmente)
FONTS = {
    'title': ('Segoe UI', 12, 'bold'),
    'body': ('Segoe UI', 10),
    'small': ('Segoe UI', 8)
}

# Función de formato (definida localmente)
def format_hnl(valor):
    """Formatea valores monetarios."""
    try:
        return f"${valor:,.2f}"
    except (TypeError, ValueError):
        return f"${valor}"


class NotificationType:
    """Tipos de notificación con sus colores y estilos."""
    
    INFO = {
        'name': 'info',
        'title': 'Información',
        'bg_color': '#3498db',
        'fg_color': '#ffffff',
        'icon': 'ℹ️',
        'sound': None
    }
    
    SUCCESS = {
        'name': 'success',
        'title': 'Éxito',
        'bg_color': '#27ae60',
        'fg_color': '#ffffff',
        'icon': '✓',
        'sound': None
    }
    
    WARNING = {
        'name': 'warning',
        'title': 'Advertencia',
        'bg_color': '#f39c12',
        'fg_color': '#ffffff',
        'icon': '⚠',
        'sound': None
    }
    
    ERROR = {
        'name': 'error',
        'title': 'Error',
        'bg_color': '#e74c3c',
        'fg_color': '#ffffff',
        'icon': '✗',
        'sound': None
    }
    
    STOCK_ALERT = {
        'name': 'stock_alert',
        'title': 'Alerta de Stock',
        'bg_color': '#e67e22',
        'fg_color': '#ffffff',
        'icon': '📦',
        'sound': None
    }
    
    SALE = {
        'name': 'sale',
        'title': 'Venta',
        'bg_color': '#2ecc71',
        'fg_color': '#ffffff',
        'icon': '💰',
        'sound': None
    }
    
    LOGIN = {
        'name': 'login',
        'title': 'Acceso',
        'bg_color': '#3498db',
        'fg_color': '#ffffff',
        'icon': '👤',
        'sound': None
    }
    
    SYSTEM = {
        'name': 'system',
        'title': 'Sistema',
        'bg_color': '#9b59b6',
        'fg_color': '#ffffff',
        'icon': '🖥️',
        'sound': None
    }
    
    @classmethod
    def get_all(cls):
        """Obtiene todos los tipos de notificación."""
        return [getattr(cls, attr) for attr in dir(cls) 
                if not attr.startswith('_') and isinstance(getattr(cls, attr), dict)]


# ============================================================================
# GESTOR DE NOTIFICACIONES PRINCIPAL
# ============================================================================

class NotificationManager:
    """Gestor profesional de notificaciones con persistencia y control avanzado."""
    
    def __init__(self, root: tk.Tk, db_manager=None):
        self.root = root
        self.db = db_manager
        self.notification_widgets: List["ProfessionalNotification"] = []
        self.notification_history: List[Dict[str, Any]] = []
        self.notification_queue: deque[tuple[NotificationPayload, int]] = deque()
        self.notification_counter = 0
        self._drain_job: str | None = None
        self._queue_processor_job: str | None = None
        self._layout_version = 0
        self._is_draining = False
        self._queued_or_visible_keys: set[str] = set()
        self.notification_state: Dict[str, Dict[str, Any]] = {}
        
        # Configuración avanzada
        self.config = {
            'stock_alerts': True,
            'sales_alerts': True,
            'login_alerts': True,
            'system_alerts': True,
            'sound_enabled': False,
            'max_history': 500,
            'max_visible': 5,
            'default_duration': 5000,
            'position': 'top_right',
            'animation_speed': 'normal',
            'group_similar': True,
            'similar_time_window': 30,  # segundos
            'show_timestamp': True,
            'show_icon': True,
            'show_progress_bar': True,
            'compact_mode': False,
            'dark_mode': False,
            'font_size': 10,
            'general_reminder_hours': 5,
            'repeat_general_notifications': False,
            'stock_reminder_minutes': 60,
            'persist_login_history': False,
        }
        
        # Control de duplicados
        self.recent_notifications = {}
        self.notification_lock = threading.Lock()
        
        # Rutas de persistencia
        self.config_file = self._get_config_path()
        self.history_file = self._get_history_path()
        self.state_file = self._get_state_path()
        
        # Cargar datos guardados
        self._load_config()
        self._load_history()
        self._load_state()
        
        # Variables de control
        self.notification_center = None
        self.update_queue = queue.Queue()
        self._start_queue_processor()
    
    # ========================================================================
    # PERSISTENCIA Y CONFIGURACIÓN
    # ========================================================================
    
    def _get_config_path(self) -> Path:
        """Obtiene la ruta del archivo de configuración."""
        try:
            app_dir = Path(__file__).parent.parent
            config_dir = app_dir / 'data'
            config_dir.mkdir(exist_ok=True)
            return config_dir / 'notifications_config.json'
        except OSError:
            return Path.home() / '.erp_notifications_config.json'
    
    def _get_history_path(self) -> Path:
        """Obtiene la ruta del archivo de historial."""
        try:
            app_dir = Path(__file__).parent.parent
            config_dir = app_dir / 'data'
            config_dir.mkdir(exist_ok=True)
            return config_dir / 'notifications_history.json'
        except OSError:
            return Path.home() / '.erp_notifications_history.json'

    def _get_state_path(self) -> Path:
        """Obtiene la ruta del archivo de estado interno."""
        try:
            app_dir = Path(__file__).parent.parent
            config_dir = app_dir / 'data'
            config_dir.mkdir(exist_ok=True)
            return config_dir / 'notifications_state.json'
        except OSError:
            return Path.home() / '.erp_notifications_state.json'
    
    def _load_config(self):
        """Carga la configuración desde archivo."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            logger.exception("Error cargando configuración de notificaciones.")
    
    def save_config(self):
        """Guarda la configuración en archivo."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.exception("Error guardando configuración de notificaciones.")
            return False
    
    def _load_history(self):
        """Carga el historial desde archivo."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    saved_history = json.load(f)
                    for notif in saved_history:
                        if 'timestamp' in notif:
                            notif['timestamp'] = datetime.fromisoformat(notif['timestamp'])
                        if 'last_displayed_at' in notif and notif['last_displayed_at']:
                            notif['last_displayed_at'] = datetime.fromisoformat(notif['last_displayed_at'])
                    self.notification_history = saved_history
        except Exception as e:
            logger.exception("Error cargando historial de notificaciones.")
            self.notification_history = []

    def _load_state(self):
        """Carga el estado de visualización y recordatorios."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.notification_state = data
        except Exception:
            logger.exception("Error cargando estado de notificaciones.")
            self.notification_state = {}
    
    def _save_history(self):
        """Guarda el historial en archivo."""
        try:
            history_to_save = []
            for notif in self.notification_history:
                notif_copy = notif.copy()
                if 'timestamp' in notif_copy:
                    notif_copy['timestamp'] = notif_copy['timestamp'].isoformat()
                if 'last_displayed_at' in notif_copy and isinstance(notif_copy['last_displayed_at'], datetime):
                    notif_copy['last_displayed_at'] = notif_copy['last_displayed_at'].isoformat()
                # No guardar callbacks
                notif_copy.pop('action_callback', None)
                notif_copy.pop('action_data', None)
                history_to_save.append(notif_copy)
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.exception("Error guardando historial de notificaciones.")

    def _save_state(self):
        """Guarda el estado de visualización y recordatorios."""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.notification_state, f, indent=2, ensure_ascii=False)
        except Exception:
            logger.exception("Error guardando estado de notificaciones.")
    
    def _start_queue_processor(self):
        """Inicia el procesador de cola en segundo plano."""
        def process_queue():
            try:
                while True:
                    callback = self.update_queue.get_nowait()
                    try:
                        callback()
                    except Exception:
                        logger.exception("Error procesando callback interno de notificaciones.")
            except queue.Empty:
                pass
            finally:
                self._queue_processor_job = self.root.after(50, process_queue)
        
        self._queue_processor_job = self.root.after(50, process_queue)
    
    # ========================================================================
    # CONTROL DE NOTIFICACIONES
    # ========================================================================
    
    def _get_notification_hash(self, title: str, message: str, type_name: str) -> str:
        """Genera un hash único para la notificación para control de duplicados."""
        content = f"{title}|{message}|{type_name}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_duplicate(self, title: str, message: str, type_name: str) -> bool:
        """Verifica si una notificación similar ya fue mostrada recientemente."""
        if not self.config['group_similar']:
            return False
        
        notification_hash = self._get_notification_hash(title, message, type_name)
        now = datetime.now()
        
        if notification_hash in self.recent_notifications:
            last_time = self.recent_notifications[notification_hash]
            time_diff = (now - last_time).total_seconds()
            
            if time_diff < self.config['similar_time_window']:
                return True
        
        # Actualizar registro
        self.recent_notifications[notification_hash] = now
        
        # Limpiar registros antiguos
        self._clean_old_records()
        
        return False
    
    def _clean_old_records(self):
        """Limpia registros de notificaciones antiguos."""
        now = datetime.now()
        to_remove = []
        
        for hash_key, timestamp in self.recent_notifications.items():
            if (now - timestamp).total_seconds() > self.config['similar_time_window']:
                to_remove.append(hash_key)
        
        for hash_key in to_remove:
            del self.recent_notifications[hash_key]
    
    def show_notification(self, title: str, message: str, type_name: str = "info", 
                         duration: int = None, action_callback: Callable = None, 
                         action_data: Any = None, force: bool = False,
                         unique_key: str | None = None,
                         persist_history: bool = True,
                         reminder_seconds: int | None = None,
                         show_once: bool = False,
                         history_mode: str = "append"):
        """Muestra una notificación con control de duplicados."""
        if threading.current_thread() is not threading.main_thread():
            self.update_queue.put(
                lambda: self.show_notification(
                    title,
                    message,
                    type_name=type_name,
                    duration=duration,
                    action_callback=action_callback,
                    action_data=action_data,
                    force=force,
                    unique_key=unique_key,
                    persist_history=persist_history,
                    reminder_seconds=reminder_seconds,
                    show_once=show_once,
                    history_mode=history_mode,
                )
            )
            return None
        
        # Verificar duplicados
        if not force and self._is_duplicate(title, message, type_name):
            return None
        
        duration = duration or self.config['default_duration']
        unique_key = unique_key or self._build_unique_key(type_name, title, message)
        now = datetime.now()
        state = self.notification_state.get(unique_key, {})

        if not force and not self._should_display_notification(
            state=state,
            show_once=show_once,
            reminder_seconds=reminder_seconds,
        ):
            return None

        if unique_key in self._queued_or_visible_keys:
            return None
        
        # Obtener configuración del tipo
        notification_type = self._get_notification_type(type_name)
        
        payload = NotificationPayload(
            id=self.notification_counter,
            notification_key=unique_key,
            title=title,
            message=message,
            type=type_name,
            type_config=notification_type,
            timestamp=datetime.now(),
            action_callback=action_callback,
            action_data=action_data,
            read=False,
        )
        
        self.notification_counter += 1

        self._register_notification_state(
            unique_key=unique_key,
            payload=payload,
            reminder_seconds=reminder_seconds,
            persist_history=persist_history,
            history_mode=history_mode,
            shown_at=now,
        )
        
        # Mostrar notificación
        self.notification_queue.append((payload, duration))
        self._queued_or_visible_keys.add(unique_key)
        self._schedule_drain()
        
        return payload.as_dict()

    def _build_unique_key(self, type_name: str, title: str, message: str) -> str:
        digest = hashlib.md5(f"{type_name}|{title}|{message}".encode('utf-8')).hexdigest()
        return f"{type_name}:{digest}"

    def _should_display_notification(self, state: Dict[str, Any], show_once: bool, reminder_seconds: int | None) -> bool:
        last_shown_at = self._parse_timestamp(state.get('last_shown_at'))
        if show_once and last_shown_at is not None:
            return False

        if reminder_seconds and last_shown_at is not None:
            elapsed = (datetime.now() - last_shown_at).total_seconds()
            if elapsed < reminder_seconds:
                return False

        return True

    def _register_notification_state(
        self,
        *,
        unique_key: str,
        payload: NotificationPayload,
        reminder_seconds: int | None,
        persist_history: bool,
        history_mode: str,
        shown_at: datetime,
    ):
        entry = dict(self.notification_state.get(unique_key, {}))
        entry.update(
            {
                'key': unique_key,
                'title': payload.title,
                'message': payload.message,
                'type': payload.type,
                'last_shown_at': shown_at.isoformat(),
                'last_hash': self._get_notification_hash(payload.title, payload.message, payload.type),
                'reminder_seconds': reminder_seconds,
                'display_count': int(entry.get('display_count', 0)) + 1,
            }
        )

        if persist_history:
            self._upsert_history_entry(unique_key, payload, history_mode, shown_at)
            entry['history_saved'] = True

        self.notification_state[unique_key] = entry
        self._save_state()

    def _upsert_history_entry(
        self,
        unique_key: str,
        payload: NotificationPayload,
        history_mode: str,
        shown_at: datetime,
    ):
        existing_index = next(
            (index for index, item in enumerate(self.notification_history) if item.get('notification_key') == unique_key),
            None,
        )
        payload_dict = payload.as_dict()
        payload_dict['notification_key'] = unique_key
        payload_dict['last_displayed_at'] = shown_at

        if existing_index is not None:
            if history_mode == "append":
                return
            current = self.notification_history[existing_index]
            current.update(
                {
                    'title': payload.title,
                    'message': payload.message,
                    'type': payload.type,
                    'type_config': payload.type_config,
                    'timestamp': current.get('timestamp') or shown_at,
                    'last_displayed_at': shown_at,
                }
            )
            if existing_index != 0:
                item = self.notification_history.pop(existing_index)
                self.notification_history.insert(0, item)
        else:
            self.notification_history.insert(0, payload_dict)

        if len(self.notification_history) > self.config['max_history']:
            self.notification_history = self.notification_history[: self.config['max_history']]
        self._save_history()

    def _parse_timestamp(self, raw_value: Any) -> datetime | None:
        if not raw_value:
            return None
        try:
            return datetime.fromisoformat(str(raw_value))
        except ValueError:
            return None
    
    def _get_notification_type(self, type_name: str) -> Dict:
        """Obtiene la configuración del tipo de notificación."""
        type_map = {
            'info': NotificationType.INFO,
            'success': NotificationType.SUCCESS,
            'warning': NotificationType.WARNING,
            'error': NotificationType.ERROR,
            'stock_alert': NotificationType.STOCK_ALERT,
            'sale': NotificationType.SALE,
            'login': NotificationType.LOGIN,
            'system': NotificationType.SYSTEM
        }
        return type_map.get(type_name, NotificationType.INFO)
    
    def _schedule_drain(self, delay: int = 0):
        """Programa una sola pasada de procesamiento de cola."""
        if self._drain_job is not None:
            return
        self._drain_job = self.root.after(delay, self._drain_queue)

    def _drain_queue(self):
        """Vacía la cola FIFO respetando siempre el máximo visible."""
        self._drain_job = None
        if self._is_draining:
            self._schedule_drain(25)
            return

        self._is_draining = True
        try:
            self._prune_closed_notifications()
            visible_limit = max(1, int(self.config.get('max_visible', 5) or 5))

            while self.notification_queue and len(self.notification_widgets) < visible_limit:
                payload, duration = self.notification_queue.popleft()
                notification = ProfessionalNotification(
                    self.root,
                    payload.as_dict(),
                    duration,
                    self.on_notification_close,
                    self.config,
                    self._build_notification_slot(len(self.notification_widgets)),
                )
                notification.notification_key = payload.notification_key
                self.notification_widgets.append(notification)

            self._reposition_notifications()

            if self.notification_queue and len(self.notification_widgets) < visible_limit:
                self._schedule_drain(25)
        finally:
            self._is_draining = False
    
    def on_notification_close(self, notification):
        """Callback cuando se cierra una notificación."""
        notification_key = getattr(notification, 'notification_key', None)
        if notification_key:
            self._queued_or_visible_keys.discard(notification_key)
        if notification in self.notification_widgets:
            self.notification_widgets.remove(notification)
            self._reposition_notifications()
        
        self._schedule_drain(25)
    
    def _reposition_notifications(self):
        """Reposiciona todas las notificaciones visibles."""
        self._prune_closed_notifications()
        positions = self._get_positions()
        self._layout_version += 1
        
        for i, widget in enumerate(self.notification_widgets):
            if i < len(positions):
                widget.animate_to(positions[i]['x'], positions[i]['y'], layout_version=self._layout_version)
    
    def _get_positions(self) -> List[Dict]:
        """Calcula las posiciones para las notificaciones."""
        positions = []
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        offset_x = 20
        offset_y = 80
        spacing = 15
        
        for i, widget in enumerate(self.notification_widgets):
            width = widget.width
            height = widget.height
            if self.config['position'] == 'top_right':
                x = screen_width - width - offset_x
                y = offset_y + sum(
                    self.notification_widgets[idx].height + spacing for idx in range(i)
                )
            elif self.config['position'] == 'top_left':
                x = offset_x
                y = offset_y + sum(
                    self.notification_widgets[idx].height + spacing for idx in range(i)
                )
            elif self.config['position'] == 'bottom_right':
                x = screen_width - width - offset_x
                y = screen_height - offset_y - height - sum(
                    self.notification_widgets[idx].height + spacing for idx in range(i)
                )
            else:  # bottom_left
                x = offset_x
                y = screen_height - offset_y - height - sum(
                    self.notification_widgets[idx].height + spacing for idx in range(i)
                )
            
            positions.append({'x': x, 'y': y})
        
        return positions

    def _build_notification_slot(self, index: int) -> Dict[str, int]:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = 360 if not self.config['compact_mode'] else 330
        height = 118 if not self.config['compact_mode'] else 92
        offset_x = 20
        offset_y = 80

        if self.config['position'] == 'top_left':
            return {
                'start_x': -width,
                'start_y': offset_y,
                'exit_x': -width - 30,
                'exit_y': offset_y,
            }
        if self.config['position'] == 'bottom_right':
            return {
                'start_x': screen_width + 30,
                'start_y': screen_height - offset_y - height,
                'exit_x': screen_width + width + 30,
                'exit_y': screen_height - offset_y - height,
            }
        if self.config['position'] == 'bottom_left':
            return {
                'start_x': -width,
                'start_y': screen_height - offset_y - height,
                'exit_x': -width - 30,
                'exit_y': screen_height - offset_y - height,
            }
        return {
            'start_x': screen_width + 30,
            'start_y': offset_y,
            'exit_x': screen_width + width + 30,
            'exit_y': offset_y,
        }

    def _prune_closed_notifications(self):
        self.notification_widgets = [
            widget for widget in self.notification_widgets
            if not widget.is_closed
        ]
    
    # ========================================================================
    # NOTIFICACIONES ESPECÍFICAS
    # ========================================================================
    
    def check_stock_alerts(self):
        """Verifica alertas de stock bajo."""
        if not self.config['stock_alerts'] or not self.db:
            return
        
        try:
            # Versión segura con manejo de errores si no existe el método
            if hasattr(self.db, 'fetch'):
                low_stock_items = self.db.fetch(
                    """
                    SELECT id, nombre, stock, COALESCE(stock_minimo, 5)
                    FROM Productos
                    WHERE stock <= COALESCE(stock_minimo, 5)
                    """
                )
                
                for item_id, nombre, stock, stock_min in low_stock_items:
                    self.show_notification(
                        f"Stock bajo pendiente: {nombre}",
                        f"Ya revisaste, hay un producto con stock bajo.\n"
                        f"Stock actual: {stock} unidades\n"
                        f"Mínimo requerido: {stock_min}",
                        type_name="stock_alert",
                        duration=8000,
                        action_callback=self._open_product_inventory,
                        action_data={'id': item_id, 'nombre': nombre},
                        unique_key=f"stock-alert:{item_id}",
                        persist_history=True,
                        reminder_seconds=max(300, int(self.config.get('stock_reminder_minutes', 60)) * 60),
                        show_once=False,
                        history_mode="update",
                    )
        except Exception as e:
            logger.exception("Error verificando alertas de stock.")
    
    def _open_product_inventory(self, product_data):
        """Abre el inventario del producto."""
        messagebox.showinfo(
            "Gestión de Inventario",
            f"Abriendo gestión para el producto: {product_data['nombre']}\n\n"
            f"Por favor, actualiza el stock o realiza un pedido de reabastecimiento."
        )
        
        if hasattr(self.root, 'show_frame') and hasattr(self.root, 'frames'):
            try:
                if 'Productos' in self.root.frames:
                    self.root.show_frame(self.root.frames['Productos'], "Productos")
            except Exception:
                logger.exception("No se pudo abrir el módulo de productos desde notificaciones.")
    
    def notify_login(self, username: str, role: str):
        """Notificación de inicio de sesión."""
        if self.config['login_alerts']:
            self.show_notification(
                f"Inicio de Sesión",
                f"Usuario: {username}\nRol: {role}\nIP: {self._get_client_ip()}",
                type_name="login",
                duration=4000,
                unique_key=f"login:{username}:{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                persist_history=bool(self.config.get('persist_login_history', False)),
                history_mode="update",
            )
    
    def notify_sale_success(self, venta_id: int, total: float, cliente: str = None):
        """Notificación de venta exitosa."""
        if self.config['sales_alerts']:
            message = f"Venta #{venta_id}\nTotal: {format_hnl(total)}"
            if cliente:
                message += f"\nCliente: {cliente}"
            
            self.show_notification(
                "Venta Completada",
                message,
                type_name="sale",
                duration=5000,
                action_callback=self._view_sale_details,
                action_data=venta_id,
                unique_key=f"sale:{venta_id}",
                persist_history=True,
                show_once=True,
                history_mode="update",
            )
    
    def _view_sale_details(self, venta_id):
        """Ver detalles de una venta."""
        messagebox.showinfo(
            "Detalles de Venta",
            f"Mostrando detalles de la venta #{venta_id}\n\n"
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )
    
    def notify_system_info(self, message: str, level: str = "info"):
        """Notificación de información del sistema."""
        if self.config['system_alerts']:
            repeat_general = bool(self.config.get('repeat_general_notifications', False))
            self.show_notification(
                "Sistema",
                message,
                type_name=level,
                duration=4000,
                unique_key=f"system:{level}:{hashlib.md5(message.encode('utf-8')).hexdigest()}",
                persist_history=True,
                reminder_seconds=(
                    max(3600, int(self.config.get('general_reminder_hours', 5)) * 3600)
                    if repeat_general
                    else None
                ),
                show_once=not repeat_general,
                history_mode="update",
            )
    
    def _get_client_ip(self) -> str:
        """Obtiene la IP del cliente (simulado)."""
        return "127.0.0.1"
    
    # ========================================================================
    # GESTIÓN DE HISTORIAL
    # ========================================================================
    
    def clear_history(self):
        """Limpia todo el historial de notificaciones."""
        self.notification_history.clear()
        self._save_history()
        
        if self.notification_center and self.notification_center.winfo_exists():
            self.notification_center.refresh_history()
    
    def get_unread_count(self) -> int:
        """Obtiene el número de notificaciones no leídas."""
        return sum(1 for n in self.notification_history if not n.get('read', False))
    
    def mark_as_read(self, notification_id: int):
        """Marca una notificación como leída."""
        for notif in self.notification_history:
            if notif.get('id') == notification_id:
                notif['read'] = True
                break
        self._save_history()
    
    def mark_all_read(self):
        """Marca todas las notificaciones como leídas."""
        for notif in self.notification_history:
            notif['read'] = True
        self._save_history()
        
        if self.notification_center and self.notification_center.winfo_exists():
            self.notification_center.refresh_history()
    
    # ========================================================================
    # INTERFAZ DE USUARIO
    # ========================================================================
    
    def show_notification_center(self):
        """Muestra el centro de notificaciones."""
        if self.notification_center and self.notification_center.winfo_exists():
            self.notification_center.lift()
            self.notification_center.focus_force()
        else:
            self.notification_center = ProfessionalNotificationCenter(self.root, self)
            self.notification_center.protocol("WM_DELETE_WINDOW", self._on_center_close)
    
    def _on_center_close(self):
        """Maneja el cierre del centro de notificaciones."""
        if self.notification_center:
            self.notification_center.destroy()
            self.notification_center = None


# ============================================================================
# WIDGET DE NOTIFICACIÓN PROFESIONAL
# ============================================================================

class ProfessionalNotification:
    """Widget de notificación profesional con animaciones avanzadas."""
    
    def __init__(self, parent, data: Dict, duration: int, 
                 close_callback: Callable, config: Dict, slot: Dict[str, int]):
        self.parent = parent
        self.data = data
        self.duration = duration
        self.close_callback = close_callback
        self.config = config
        self.slot = slot

        self.width = 360 if not config['compact_mode'] else 330
        self.height = 118 if not config['compact_mode'] else 92
        self.current_x = float(slot['start_x'])
        self.current_y = float(slot['start_y'])
        self.target_x = int(slot['start_x'])
        self.target_y = int(slot['start_y'])
        self.is_closing = False
        self.is_closed = False
        self._motion_job: str | None = None
        self._progress_job: str | None = None
        self._auto_close_job: str | None = None
        self._layout_version = 0
        self._progress_elapsed = 0
        self._progress_interval_ms = 40
        
        self._create_window()
        self._create_content()
        self._start_progress()
        self._start_timer()
    
    def _create_window(self):
        """Crea la ventana de notificación."""
        self.window = tk.Toplevel(self.parent)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.withdraw()
        
        try:
            self.window.attributes('-alpha', 0.98)
        except tk.TclError:
            logger.debug("La plataforma no soporta alpha en Toplevel.")
        
        self.window.geometry(f'{self.width}x{self.height}+{int(self.current_x)}+{int(self.current_y)}')
        self.window.deiconify()
    
    def _create_content(self):
        """Crea el contenido de la notificación."""
        type_config = self.data['type_config']
        bg_color = type_config['bg_color']
        fg_color = type_config['fg_color']
        
        # Frame principal
        self.main_frame = tk.Frame(self.window, bg=bg_color, relief='flat')
        self.main_frame.pack(fill='both', expand=True)
        
        # Barra superior con efecto de gradiente (simulado)
        top_bar = tk.Frame(self.main_frame, bg=self._darken_color(bg_color, 0.1), height=3)
        top_bar.pack(fill='x')
        
        # Contenido principal
        content_frame = tk.Frame(self.main_frame, bg=bg_color)
        content_frame.pack(fill='both', expand=True, padx=12, pady=10)
        
        # Icono
        if self.config['show_icon']:
            icon_label = tk.Label(content_frame, text=type_config['icon'], 
                                 font=('Segoe UI', 24), bg=bg_color, fg=fg_color)
            icon_label.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        
        # Título y botón cerrar
        title_frame = tk.Frame(content_frame, bg=bg_color)
        title_frame.grid(row=0, column=1, sticky='ew', padx=(0, 5))
        
        title_font = ('Segoe UI Semibold', self.config['font_size'] + 2)
        tk.Label(title_frame, text=self.data['title'], font=title_font,
                bg=bg_color, fg=fg_color, anchor='w').pack(side='left', fill='x', expand=True)
        
        close_btn = tk.Label(title_frame, text='✕', font=('Segoe UI', 12, 'bold'),
                            bg=bg_color, fg=fg_color, cursor='hand2')
        close_btn.pack(side='right')
        close_btn.bind('<Button-1>', lambda e: self.close())
        
        # Mensaje
        msg_frame = tk.Frame(content_frame, bg=bg_color)
        msg_frame.grid(row=1, column=1, sticky='ew', pady=(5, 0))
        
        message_font = ('Segoe UI', self.config['font_size'])
        message_label = tk.Label(msg_frame, text=self.data['message'], 
                                font=message_font, bg=bg_color, fg=fg_color,
                                anchor='w', justify='left', wraplength=260)
        message_label.pack(fill='x')
        
        # Timestamp
        if self.config['show_timestamp']:
            timestamp = self.data['timestamp'].strftime('%H:%M:%S · %d/%m/%Y')
            tk.Label(msg_frame, text=timestamp, font=('Segoe UI', 8),
                    bg=bg_color, fg=self._lighten_color(fg_color, 0.3),
                    anchor='e').pack(fill='x', pady=(5, 0))
        
        # Barra de progreso
        if self.config['show_progress_bar']:
            self.progress_frame = tk.Frame(self.main_frame, bg=bg_color, height=2)
            self.progress_frame.pack(fill='x', side='bottom')
            
            self.progress_bar = tk.Canvas(self.progress_frame, height=2, 
                                         bg=self._darken_color(bg_color, 0.2),
                                         highlightthickness=0)
            self.progress_bar.pack(fill='x')
        
        # Bind click si tiene callback
        if self.data.get('action_callback'):
            for widget in [self.window, self.main_frame, content_frame]:
                widget.bind('<Button-1>', self._on_click)
                widget.config(cursor='hand2')
        
        content_frame.columnconfigure(1, weight=1)
    
    def _darken_color(self, color: str, factor: float) -> str:
        """Oscurece un color."""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            
            r = int(r * (1 - factor))
            g = int(g * (1 - factor))
            b = int(b * (1 - factor))
            
            return f'#{r:02x}{g:02x}{b:02x}'
        except (ValueError, TypeError, IndexError):
            return '#000000'
    
    def _lighten_color(self, color: str, factor: float) -> str:
        """Aclara un color."""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            
            r = int(r + (255 - r) * factor)
            g = int(g + (255 - g) * factor)
            b = int(b + (255 - b) * factor)
            
            return f'#{r:02x}{g:02x}{b:02x}'
        except (ValueError, TypeError, IndexError):
            return '#ffffff'
    
    def animate_to(self, target_x: int, target_y: int, layout_version: int = 0):
        """Anima a una posición cancelando cualquier animación previa."""
        if self.is_closed:
            return
        self._layout_version = layout_version
        self.target_x = int(target_x)
        self.target_y = int(target_y)
        self._start_motion(target_x, target_y, duration_ms=180)

    def _start_motion(self, target_x: int, target_y: int, duration_ms: int):
        self._cancel_motion_job()
        if self.is_closed:
            return

        start_x = self.current_x
        start_y = self.current_y
        delta_x = float(target_x) - start_x
        delta_y = float(target_y) - start_y
        steps = max(6, duration_ms // 16)

        def ease_out_cubic(value: float) -> float:
            return 1 - ((1 - value) ** 3)

        def step(index: int = 1):
            if self.is_closed:
                return
            progress = min(1.0, index / steps)
            eased = ease_out_cubic(progress)
            self.current_x = start_x + (delta_x * eased)
            self.current_y = start_y + (delta_y * eased)
            self._apply_geometry()

            if progress < 1.0:
                self._motion_job = self.window.after(16, lambda: step(index + 1))
            else:
                self.current_x = float(target_x)
                self.current_y = float(target_y)
                self._motion_job = None
                self._apply_geometry()

        step()

    def _cancel_motion_job(self):
        if self._motion_job is None:
            return
        try:
            self.window.after_cancel(self._motion_job)
        except tk.TclError:
            pass
        self._motion_job = None

    def _apply_geometry(self):
        try:
            self.window.geometry(
                f'{self.width}x{self.height}+{int(round(self.current_x))}+{int(round(self.current_y))}'
            )
        except tk.TclError:
            self.is_closed = True
    
    def _start_progress(self):
        """Inicia la barra de progreso."""
        if self.config['show_progress_bar']:
            self._update_progress()
    
    def _update_progress(self):
        """Actualiza la barra de progreso."""
        if self.is_closing or self.is_closed or not self.config['show_progress_bar']:
            return

        self._progress_elapsed = min(self.duration, self._progress_elapsed + self._progress_interval_ms)
        progress_ratio = self._progress_elapsed / max(1, self.duration)
        progress_width = int(self.width * progress_ratio)
        self.progress_bar.delete('all')
        self.progress_bar.create_rectangle(0, 0, progress_width, 2, fill='white', outline='')

        if self._progress_elapsed < self.duration:
            self._progress_job = self.window.after(self._progress_interval_ms, self._update_progress)
        else:
            self._progress_job = None
    
    def _start_timer(self):
        """Inicia el temporizador de cierre."""
        self._auto_close_job = self.window.after(self.duration, self.close)
    
    def _on_click(self, event=None):
        """Maneja el click en la notificación."""
        if self.is_closing or self.is_closed:
            return

        callback = self.data.get('action_callback')
        action_data = self.data.get('action_data')
        if callback:
            try:
                callback(action_data) if action_data is not None else callback()
            except Exception:
                logger.exception("Error ejecutando callback de notificación.")
        self.close()
    
    def close(self):
        """Cierra la notificación con animación."""
        if self.is_closing or self.is_closed:
            return
        
        self.is_closing = True
        self._cancel_jobs_for_close()
        self._start_motion(self.slot['exit_x'], self.slot['exit_y'], duration_ms=160)
        self.window.after(170, self._finalize_close)

    def _cancel_jobs_for_close(self):
        self._cancel_motion_job()
        for attr in ('_progress_job', '_auto_close_job'):
            job_id = getattr(self, attr)
            if job_id is None:
                continue
            try:
                self.window.after_cancel(job_id)
            except tk.TclError:
                pass
            setattr(self, attr, None)

    def _finalize_close(self):
        if self.is_closed:
            return
        self.is_closed = True
        try:
            self.window.destroy()
        except tk.TclError:
            pass
        if self.close_callback:
            self.close_callback(self)


# ============================================================================
# CENTRO DE NOTIFICACIONES PROFESIONAL
# ============================================================================

class ProfessionalNotificationCenter(tk.Toplevel):
    """Centro de notificaciones."""
    
    def __init__(self, parent, manager: NotificationManager):
        super().__init__(parent)
        self.manager = manager
        self.title("Centro de Notificaciones")
        self.configure(bg=PALETTE['blue_soft'])
        self.resizable(True, True)  # Permitir redimensionar si quieres
        
        self._setup_ui()
        self._load_notifications()
        
        # Configurar tamaño: alto completo, ancho personalizado
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Definir el ancho que quieres (puedes cambiarlo)
        ancho_ventana = 900  # Cambia este valor según prefieras
        
        # Alto: toda la pantalla (de arriba a abajo)
        alto_ventana = screen_height
        
        # Posición horizontal centrada
        x = (screen_width - ancho_ventana) // 2
        
        # Posición vertical: desde el borde superior (y=0)
        y = 0
        
        # Aplicar geometría
        self.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
    
    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        # Frame principal
        main_frame = tk.Frame(self, bg=PALETTE['blue_soft'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=PALETTE['white'], height=80)
        header_frame.pack(fill='x', pady=(0, 20))
        header_frame.pack_propagate(False)
        
        # Título y estadísticas
        title_frame = tk.Frame(header_frame, bg=PALETTE['white'])
        title_frame.pack(side='left', padx=20, pady=15)
        
        tk.Label(title_frame, text="Centro de Notificaciones", 
                font=('Segoe UI Semibold', 20), bg=PALETTE['white'],
                fg=PALETTE['blue_dark']).pack(anchor='w')
        
        stats_frame = tk.Frame(title_frame, bg=PALETTE['white'])
        stats_frame.pack(anchor='w', pady=(5, 0))
        
        unread_count = self.manager.get_unread_count()
        tk.Label(stats_frame, text=f"📬 {len(self.manager.notification_history)} total  •  🔔 {unread_count} no leídas",
                font=('Segoe UI', 10), bg=PALETTE['white'], fg=PALETTE['gray_text']).pack()
        
        # Botones de acción
        actions_frame = tk.Frame(header_frame, bg=PALETTE['white'])
        actions_frame.pack(side='right', padx=20, pady=15)
        
        self._create_button(actions_frame, "📥 Marcar todas leídas", self._mark_all_read, 'secondary')
        self._create_button(actions_frame, "🗑️ Limpiar historial", self._clear_history, 'danger')
        self._create_button(actions_frame, "⚙️ Configuración", self._open_settings, 'primary')
        
        # Notebook para tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Tab de historial
        self.history_tab = tk.Frame(self.notebook, bg=PALETTE['blue_soft'])
        self.notebook.add(self.history_tab, text="📋 Historial")
        self._create_history_tab()
        
        # Tab de estadísticas
        self.stats_tab = tk.Frame(self.notebook, bg=PALETTE['blue_soft'])
        self.notebook.add(self.stats_tab, text="📊 Estadísticas")
        self._create_stats_tab()
    
    def _create_button(self, parent, text, command, style='primary'):
        """Crea un botón con estilo."""
        colors = {
            'primary': {'bg': PALETTE['blue_primary'], 'fg': 'white'},
            'secondary': {'bg': PALETTE['surface_alt'], 'fg': PALETTE['blue_dark']},
            'danger': {'bg': PALETTE['danger'], 'fg': 'white'}
        }
        
        btn = tk.Button(parent, text=text, command=command,
                       font=('Segoe UI Semibold', 9),
                       bg=colors[style]['bg'], fg=colors[style]['fg'],
                       padx=15, pady=8, cursor='hand2',
                       relief='flat', borderwidth=0)
        btn.pack(side='left', padx=5)
        
        # Hover effect
        def on_enter(e):
            btn['bg'] = self._darken_color(colors[style]['bg'], 0.1)
        
        def on_leave(e):
            btn['bg'] = colors[style]['bg']
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def _darken_color(self, color: str, factor: float) -> str:
        """Oscurece un color."""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = int(r * (1 - factor))
            g = int(g * (1 - factor))
            b = int(b * (1 - factor))
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return color
    
    def _create_history_tab(self):
        """Crea la pestaña de historial con filtros."""
        # Frame de filtros
        filter_frame = tk.Frame(self.history_tab, bg=PALETTE['blue_soft'])
        filter_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(filter_frame, text="Filtrar por tipo:", 
                bg=PALETTE['blue_soft'], font=('Segoe UI', 10)).pack(side='left', padx=5)
        
        self.filter_var = tk.StringVar(value='todos')
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                    values=['todos', 'info', 'success', 'warning', 
                                           'error', 'stock_alert', 'sale', 'login', 'system'],
                                    width=15, state='readonly')
        filter_combo.pack(side='left', padx=5)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_history())
        
        tk.Label(filter_frame, text="Buscar:", bg=PALETTE['blue_soft'],
                font=('Segoe UI', 10)).pack(side='left', padx=(20, 5))
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var,
                               font=('Segoe UI', 10), width=25)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.refresh_history())
        
        # Canvas con scroll para las notificaciones
        canvas_frame = tk.Frame(self.history_tab, bg=PALETTE['blue_soft'])
        canvas_frame.pack(fill='both', expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg=PALETTE['blue_soft'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=PALETTE['blue_soft'])
        
        self.scrollable_frame.bind('<Configure>', lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox('all')))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.history_items = []
    
    def _create_stats_tab(self):
        """Crea la pestaña de estadísticas."""
        stats_frame = tk.Frame(self.stats_tab, bg=PALETTE['blue_soft'])
        stats_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Título
        tk.Label(stats_frame, text="Estadísticas de Notificaciones",
                font=('Segoe UI Semibold', 16), bg=PALETTE['blue_soft'],
                fg=PALETTE['blue_dark']).pack(anchor='w', pady=(0, 20))
        
        # Grid de estadísticas
        stats_grid = tk.Frame(stats_frame, bg=PALETTE['blue_soft'])
        stats_grid.pack(fill='both', expand=True)
        
        # Calcular estadísticas
        total = len(self.manager.notification_history)
        unread = self.manager.get_unread_count()
        
        # Por tipos
        type_counts = {}
        for notif in self.manager.notification_history:
            type_name = notif['type']
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # Mostrar estadísticas
        self._create_stat_card(stats_grid, "Total Notificaciones", str(total), "📬", 0, 0)
        self._create_stat_card(stats_grid, "No Leídas", str(unread), "🔔", 0, 1)
        self._create_stat_card(stats_grid, "Última semana", 
                              self._count_last_week(), "📅", 0, 2)
        
        # Tipos de notificación
        type_frame = tk.LabelFrame(stats_frame, text="Por Tipo", 
                                  bg=PALETTE['white'], font=('Segoe UI Semibold', 11),
                                  fg=PALETTE['blue_dark'], padx=10, pady=10)
        type_frame.pack(fill='x', pady=(20, 0))
        
        for i, (type_name, count) in enumerate(sorted(type_counts.items(), 
                                                       key=lambda x: x[1], reverse=True)):
            color = self._get_type_color(type_name)
            tk.Label(type_frame, text=f"{self._get_type_icon(type_name)} {type_name.upper()}:",
                    bg=PALETTE['white'], font=('Segoe UI', 10)).grid(row=i, column=0, sticky='w', pady=5)
            tk.Label(type_frame, text=str(count), bg=PALETTE['white'],
                    font=('Segoe UI Semibold', 12), fg=color).grid(row=i, column=1, padx=20, pady=5)
    
    def _create_stat_card(self, parent, title, value, icon, row, col):
        """Crea una tarjeta de estadística."""
        card = tk.Frame(parent, bg=PALETTE['white'], relief='raised', bd=1)
        card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
        
        tk.Label(card, text=icon, font=('Segoe UI', 32), 
                bg=PALETTE['white']).pack(pady=(15, 5))
        tk.Label(card, text=value, font=('Segoe UI Semibold', 24),
                bg=PALETTE['white'], fg=PALETTE['blue_primary']).pack()
        tk.Label(card, text=title, font=('Segoe UI', 10),
                bg=PALETTE['white'], fg=PALETTE['gray_text']).pack(pady=(0, 15))
        
        parent.columnconfigure(col, weight=1)
    
    def _count_last_week(self) -> int:
        """Cuenta notificaciones de la última semana."""
        week_ago = datetime.now() - timedelta(days=7)
        return sum(1 for n in self.manager.notification_history 
                  if n['timestamp'] >= week_ago)
    
    def _get_type_color(self, type_name: str) -> str:
        """Obtiene el color para un tipo de notificación."""
        colors = {
            'info': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'error': '#e74c3c',
            'stock_alert': '#e67e22',
            'sale': '#2ecc71',
            'login': '#3498db',
            'system': '#9b59b6'
        }
        return colors.get(type_name, '#3498db')
    
    def _get_type_icon(self, type_name: str) -> str:
        """Obtiene el ícono para un tipo de notificación."""
        icons = {
            'info': 'ℹ️',
            'success': '✓',
            'warning': '⚠',
            'error': '✗',
            'stock_alert': '📦',
            'sale': '💰',
            'login': '👤',
            'system': '🖥️'
        }
        return icons.get(type_name, '📋')
    
    def refresh_history(self):
        """Refresca la lista de historial."""
        # Limpiar items existentes
        for item in self.history_items:
            item.destroy()
        self.history_items.clear()
        
        # Filtrar notificaciones
        filter_type = self.filter_var.get()
        search_text = self.search_var.get().lower()
        
        filtered = self.manager.notification_history
        
        if filter_type != 'todos':
            filtered = [n for n in filtered if n['type'] == filter_type]
        
        if search_text:
            filtered = [n for n in filtered if search_text in n['title'].lower() or 
                       search_text in n['message'].lower()]
        
        # Crear items
        for notif in filtered:
            item = self._create_history_item(notif)
            self.history_items.append(item)
        
        # Mostrar mensaje si no hay resultados
        if not filtered:
            empty_label = tk.Label(self.scrollable_frame, 
                                  text="✨ No hay notificaciones que mostrar",
                                  font=('Segoe UI', 12), bg=PALETTE['blue_soft'],
                                  fg=PALETTE['gray_text'])
            empty_label.pack(pady=50)
            self.history_items.append(empty_label)
    
    def _create_history_item(self, notif: Dict) -> tk.Frame:
        """Crea un item individual en el historial."""
        type_config = self._get_type_config(notif['type'])
        bg_color = type_config['bg_color']
        
        item_frame = tk.Frame(self.scrollable_frame, bg=PALETTE['white'], 
                             relief='flat', bd=1, highlightbackground=PALETTE['gray_border'],
                             highlightthickness=1)
        item_frame.pack(fill='x', padx=5, pady=5)
        
        # Barra de color
        color_bar = tk.Frame(item_frame, bg=bg_color, width=5)
        color_bar.pack(side='left', fill='y')
        
        # Contenido
        content_frame = tk.Frame(item_frame, bg=PALETTE['white'])
        content_frame.pack(side='left', fill='both', expand=True, padx=15, pady=12)
        
        # Header con título y fecha
        header_frame = tk.Frame(content_frame, bg=PALETTE['white'])
        header_frame.pack(fill='x')
        
        # Icono y título
        icon_text = f"{type_config['icon']} {notif['title']}"
        title_label = tk.Label(header_frame, text=icon_text, 
                              font=('Segoe UI Semibold', 11),
                              bg=PALETTE['white'], fg=PALETTE['blue_dark'])
        title_label.pack(side='left')
        
        # Estado de lectura
        if not notif.get('read', False):
            unread_dot = tk.Label(header_frame, text="●", font=('Segoe UI', 8),
                                 bg=PALETTE['white'], fg=bg_color)
            unread_dot.pack(side='left', padx=(5, 0))
        
        # Fecha
        fecha = notif['timestamp'].strftime('%d/%m/%Y %H:%M:%S')
        fecha_label = tk.Label(header_frame, text=fecha, font=('Segoe UI', 9),
                              bg=PALETTE['white'], fg=PALETTE['gray_text'])
        fecha_label.pack(side='right')
        
        # Mensaje
        msg_label = tk.Label(content_frame, text=notif['message'], 
                            font=('Segoe UI', 10), bg=PALETTE['white'],
                            fg=PALETTE['black'], wraplength=600, justify='left')
        msg_label.pack(anchor='w', pady=(5, 0))
        
        # Botones de acción si tiene callback
        btn_frame = tk.Frame(content_frame, bg=PALETTE['white'])
        
        if notif.get('action_callback'):
            action_btn = tk.Button(btn_frame, text="Ver detalles", 
                                  command=lambda n=notif: self._execute_action(n),
                                  font=('Segoe UI', 9), bg=PALETTE['blue_primary'],
                                  fg='white', padx=10, pady=3, cursor='hand2',
                                  relief='flat', borderwidth=0)
            action_btn.pack(side='left')
            
            # Hover effect
            def on_enter(e):
                action_btn['bg'] = self._darken_color(PALETTE['blue_primary'], 0.1)
            
            def on_leave(e):
                action_btn['bg'] = PALETTE['blue_primary']
            
            action_btn.bind('<Enter>', on_enter)
            action_btn.bind('<Leave>', on_leave)
        
        # Botón marcar como leído
        if not notif.get('read', False):
            read_btn = tk.Button(btn_frame, text="Marcar como leído", 
                                command=lambda n=notif: self._mark_as_read(n),
                                font=('Segoe UI', 9), bg=PALETTE['surface_alt'],
                                fg=PALETTE['blue_dark'], padx=10, pady=3,
                                cursor='hand2', relief='flat', borderwidth=0)
            read_btn.pack(side='left', padx=(5, 0))
        
        if btn_frame.winfo_children():
            btn_frame.pack(anchor='w', pady=(8, 0))
        
        return item_frame
    
    def _get_type_config(self, type_name: str) -> Dict:
        """Obtiene la configuración del tipo de notificación."""
        type_map = {
            'info': NotificationType.INFO,
            'success': NotificationType.SUCCESS,
            'warning': NotificationType.WARNING,
            'error': NotificationType.ERROR,
            'stock_alert': NotificationType.STOCK_ALERT,
            'sale': NotificationType.SALE,
            'login': NotificationType.LOGIN,
            'system': NotificationType.SYSTEM
        }
        return type_map.get(type_name, NotificationType.INFO)
    
    def _execute_action(self, notif: Dict):
        """Ejecuta la acción de una notificación."""
        callback = notif.get('action_callback')
        action_data = notif.get('action_data')
        if callback:
            try:
                callback(action_data) if action_data else callback()
                self._mark_as_read(notif)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo ejecutar la acción: {e}")
    
    def _mark_as_read(self, notif: Dict):
        """Marca una notificación como leída."""
        notif['read'] = True
        self.manager.mark_as_read(notif.get('id'))
        self.refresh_history()
    
    def _mark_all_read(self):
        """Marca todas como leídas."""
        self.manager.mark_all_read()
        self.refresh_history()
        messagebox.showinfo("Éxito", "Todas las notificaciones marcadas como leídas.")
    
    def _clear_history(self):
        """Limpia el historial."""
        if messagebox.askyesno("Confirmar", "¿Deseas eliminar TODO el historial de notificaciones?\n\nEsta acción no se puede deshacer."):
            self.manager.clear_history()
            self.refresh_history()
            messagebox.showinfo("Éxito", "Historial limpiado correctamente.")
    
    def _open_settings(self):
        """Abre la ventana de configuración."""
        SettingsWindow(self, self.manager)
    
    def _load_notifications(self):
        """Carga las notificaciones iniciales."""
        self.refresh_history()


# ============================================================================
# VENTANA DE CONFIGURACIÓN PROFESIONAL
# ============================================================================

class SettingsWindow(tk.Toplevel):
    """Ventana de configuración profesional para notificaciones."""
    
    def __init__(self, parent, manager: NotificationManager):
        super().__init__(parent)
        self.manager = manager
        self.title("Configuración de Notificaciones")
        self.geometry("1000x800")
        self.configure(bg=PALETTE['blue_soft'])
        self.resizable(True, True)
        
        self._setup_ui()
        self._load_config()
        self.state('zoomed')
        # Centrar ventana
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _setup_ui(self):
        """Configura la interfaz de configuración."""
        main_frame = tk.Frame(self, bg=PALETTE['blue_soft'])
        main_frame.pack(fill='both', expand=True, padx=30, pady=20)
        main_frame.columnconfigure(0, weight=1)
        
        # Título
        tk.Label(main_frame, text="Configuración de Notificaciones",
                font=('Segoe UI Semibold', 18), bg=PALETTE['blue_soft'],
                fg=PALETTE['blue_dark']).pack(anchor='w', pady=(0, 20))
        
        # Notebook para pestañas
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
        
        # Pestaña General
        general_tab = tk.Frame(notebook, bg=PALETTE['blue_soft'])
        notebook.add(general_tab, text="⚙️ General")
        self._create_general_tab(general_tab)
        
        # Pestaña Tipos
        types_tab = tk.Frame(notebook, bg=PALETTE['blue_soft'])
        notebook.add(types_tab, text="📋 Tipos")
        self._create_types_tab(types_tab)
        
        # Pestaña Apariencia
        appearance_tab = tk.Frame(notebook, bg=PALETTE['blue_soft'])
        notebook.add(appearance_tab, text="🎨 Apariencia")
        self._create_appearance_tab(appearance_tab)
        
        # Pestaña Avanzado
        advanced_tab = tk.Frame(notebook, bg=PALETTE['blue_soft'])
        notebook.add(advanced_tab, text="🔧 Avanzado")
        self._create_advanced_tab(advanced_tab)

        help_tab = tk.Frame(notebook, bg=PALETTE['blue_soft'])
        notebook.add(help_tab, text="❓ Ayuda")
        self._create_help_tab(help_tab)
        
        # Botones de acción
        btn_frame = tk.Frame(main_frame, bg=PALETTE['blue_soft'])
        btn_frame.pack(fill='x', pady=(20, 0))
        
        self._create_button(btn_frame, "Guardar Configuración", self._save_config, 'primary')
        self._create_button(btn_frame, "Cancelar", self.destroy, 'secondary')
        self._create_button(btn_frame, "Restaurar Predeterminados", self._reset_defaults, 'danger')

    def _create_spinbox(self, parent, variable, *, from_, to, increment=1, width=8):
        spin = tk.Spinbox(
            parent,
            from_=from_,
            to=to,
            increment=increment,
            textvariable=variable,
            width=width,
            relief='solid',
            borderwidth=1,
            font=('Segoe UI', 10),
        )
        return spin
    
    def _create_general_tab(self, parent):
        """Crea la pestaña general."""
        config_frame = tk.Frame(parent, bg=PALETTE['blue_soft'])
        config_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        summary = tk.LabelFrame(config_frame, text="Comportamiento general", bg=PALETTE['white'],
                                fg=PALETTE['blue_dark'], font=('Segoe UI Semibold', 11), padx=18, pady=16)
        summary.pack(fill='x', pady=(0, 16))
        
        # Duración
        duration_frame = tk.Frame(summary, bg=PALETTE['white'])
        duration_frame.pack(fill='x', pady=10)
        
        tk.Label(duration_frame, text="Duración predeterminada:", 
                font=('Segoe UI', 10), bg=PALETTE['white']).pack(side='left')
        
        self.duration_var = tk.IntVar(value=self.manager.config['default_duration'] // 1000)
        duration_spin = self._create_spinbox(duration_frame, self.duration_var, from_=2, to=15)
        duration_spin.pack(side='left', padx=10)
        tk.Label(duration_frame, text="segundos", font=('Segoe UI', 10),
                bg=PALETTE['white']).pack(side='left')
        
        # Posición
        pos_frame = tk.Frame(summary, bg=PALETTE['white'])
        pos_frame.pack(fill='x', pady=10)
        
        tk.Label(pos_frame, text="Posición en pantalla:", 
                font=('Segoe UI', 10), bg=PALETTE['white']).pack(side='left')
        
        self.position_var = tk.StringVar(value=self.manager.config['position'])
        position_combo = ttk.Combobox(pos_frame, textvariable=self.position_var,
                                      values=['top_right', 'top_left', 'bottom_right', 'bottom_left'],
                                      width=15, state='readonly')
        position_combo.pack(side='left', padx=10)
        
        # Máximo visible
        max_frame = tk.Frame(summary, bg=PALETTE['white'])
        max_frame.pack(fill='x', pady=10)
        
        tk.Label(max_frame, text="Máximo notificaciones visibles:", 
                font=('Segoe UI', 10), bg=PALETTE['white']).pack(side='left')
        
        self.max_visible_var = tk.IntVar(value=self.manager.config['max_visible'])
        max_spin = self._create_spinbox(max_frame, self.max_visible_var, from_=1, to=10)
        max_spin.pack(side='left', padx=10)
        
        # Agrupar similares
        self.group_var = tk.BooleanVar(value=self.manager.config['group_similar'])
        tk.Checkbutton(summary, text="Agrupar notificaciones similares",
                      variable=self.group_var, bg=PALETTE['white'],
                      font=('Segoe UI', 10)).pack(anchor='w', pady=10)
        
        # Ventana de tiempo para similares
        time_frame = tk.Frame(summary, bg=PALETTE['white'])
        time_frame.pack(fill='x', pady=5)
        
        tk.Label(time_frame, text="Ventana de tiempo para similares:", 
                font=('Segoe UI', 10), bg=PALETTE['white']).pack(side='left')
        
        self.time_window_var = tk.IntVar(value=self.manager.config['similar_time_window'])
        time_spin = self._create_spinbox(time_frame, self.time_window_var, from_=5, to=120, increment=5)
        time_spin.pack(side='left', padx=10)
        tk.Label(time_frame, text="segundos", font=('Segoe UI', 10),
                bg=PALETTE['white']).pack(side='left')

        reminders = tk.LabelFrame(config_frame, text="Recordatorios inteligentes", bg=PALETTE['white'],
                                  fg=PALETTE['blue_dark'], font=('Segoe UI Semibold', 11), padx=18, pady=16)
        reminders.pack(fill='x')

        self.repeat_general_var = tk.BooleanVar(value=self.manager.config.get('repeat_general_notifications', False))
        tk.Checkbutton(
            reminders,
            text="Permitir que las notificaciones generales se repitan si corresponde",
            variable=self.repeat_general_var,
            bg=PALETTE['white'],
            font=('Segoe UI', 10),
        ).pack(anchor='w', pady=(0, 10))

        general_frame = tk.Frame(reminders, bg=PALETTE['white'])
        general_frame.pack(fill='x', pady=6)
        tk.Label(general_frame, text="Repetición de recordatorios generales:", font=('Segoe UI', 10),
                 bg=PALETTE['white']).pack(side='left')
        self.general_hours_var = tk.IntVar(value=int(self.manager.config.get('general_reminder_hours', 5)))
        self._create_spinbox(general_frame, self.general_hours_var, from_=1, to=24).pack(side='left', padx=10)
        tk.Label(general_frame, text="horas", font=('Segoe UI', 10), bg=PALETTE['white']).pack(side='left')

        stock_frame = tk.Frame(reminders, bg=PALETTE['white'])
        stock_frame.pack(fill='x', pady=6)
        tk.Label(stock_frame, text="Recordatorio de stock bajo:", font=('Segoe UI', 10),
                 bg=PALETTE['white']).pack(side='left')
        self.stock_minutes_var = tk.IntVar(value=int(self.manager.config.get('stock_reminder_minutes', 60)))
        self._create_spinbox(stock_frame, self.stock_minutes_var, from_=15, to=240, increment=15).pack(side='left', padx=10)
        tk.Label(stock_frame, text="minutos", font=('Segoe UI', 10), bg=PALETTE['white']).pack(side='left')
    
    def _create_types_tab(self, parent):
        """Crea la pestaña de tipos de notificaciones."""
        config_frame = tk.Frame(parent, bg=PALETTE['blue_soft'])
        config_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(config_frame, text="Activar/Desactivar tipos de notificaciones:",
                font=('Segoe UI Semibold', 11), bg=PALETTE['blue_soft']).pack(anchor='w', pady=(0, 15))
        
        # Variables para cada tipo
        self.type_vars = {
            'stock_alerts': tk.BooleanVar(value=self.manager.config['stock_alerts']),
            'sales_alerts': tk.BooleanVar(value=self.manager.config['sales_alerts']),
            'login_alerts': tk.BooleanVar(value=self.manager.config['login_alerts']),
            'system_alerts': tk.BooleanVar(value=self.manager.config['system_alerts'])
        }
        
        types = [
            ('📦 Alertas de Stock Bajo', 'stock_alerts'),
            ('💰 Notificaciones de Ventas', 'sales_alerts'),
            ('👤 Notificaciones de Inicio de Sesión', 'login_alerts'),
            ('🖥️ Notificaciones del Sistema', 'system_alerts')
        ]
        
        for label, key in types:
            tk.Checkbutton(config_frame, text=label, variable=self.type_vars[key],
                          bg=PALETTE['blue_soft'], font=('Segoe UI', 10),
                          anchor='w').pack(fill='x', pady=8)
    
    def _create_appearance_tab(self, parent):
        """Crea la pestaña de apariencia."""
        config_frame = tk.Frame(parent, bg=PALETTE['blue_soft'])
        config_frame.pack(fill='both', expand=True, padx=20, pady=20)
        options = tk.LabelFrame(config_frame, text="Diseño visual", bg=PALETTE['white'],
                                fg=PALETTE['blue_dark'], font=('Segoe UI Semibold', 11), padx=18, pady=16)
        options.pack(fill='x')
        
        # Modo compacto
        self.compact_var = tk.BooleanVar(value=self.manager.config['compact_mode'])
        tk.Checkbutton(options, text="Modo compacto (notificaciones más pequeñas)",
                      variable=self.compact_var, bg=PALETTE['white'],
                      font=('Segoe UI', 10)).pack(anchor='w', pady=5)
        
        # Mostrar timestamp
        self.timestamp_var = tk.BooleanVar(value=self.manager.config['show_timestamp'])
        tk.Checkbutton(options, text="Mostrar fecha y hora en notificaciones",
                      variable=self.timestamp_var, bg=PALETTE['white'],
                      font=('Segoe UI', 10)).pack(anchor='w', pady=5)
        
        # Mostrar ícono
        self.icon_var = tk.BooleanVar(value=self.manager.config['show_icon'])
        tk.Checkbutton(options, text="Mostrar íconos en notificaciones",
                      variable=self.icon_var, bg=PALETTE['white'],
                      font=('Segoe UI', 10)).pack(anchor='w', pady=5)
        
        # Mostrar barra de progreso
        self.progress_var = tk.BooleanVar(value=self.manager.config['show_progress_bar'])
        tk.Checkbutton(options, text="Mostrar barra de progreso",
                      variable=self.progress_var, bg=PALETTE['white'],
                      font=('Segoe UI', 10)).pack(anchor='w', pady=5)
        
        # Tamaño de fuente
        font_frame = tk.Frame(options, bg=PALETTE['white'])
        font_frame.pack(fill='x', pady=15)
        
        tk.Label(font_frame, text="Tamaño de fuente:", font=('Segoe UI', 10),
                bg=PALETTE['white']).pack(side='left')
        
        self.font_var = tk.IntVar(value=self.manager.config['font_size'])
        font_spin = self._create_spinbox(font_frame, self.font_var, from_=8, to=14)
        font_spin.pack(side='left', padx=10)
        
        # Animación
        anim_frame = tk.Frame(options, bg=PALETTE['white'])
        anim_frame.pack(fill='x', pady=10)
        
        tk.Label(anim_frame, text="Velocidad de animación:", 
                font=('Segoe UI', 10), bg=PALETTE['white']).pack(side='left')
        
        self.anim_var = tk.StringVar(value=self.manager.config['animation_speed'])
        anim_combo = ttk.Combobox(anim_frame, textvariable=self.anim_var,
                                  values=['slow', 'normal', 'fast'], width=10)
        anim_combo.pack(side='left', padx=10)
    
    def _create_advanced_tab(self, parent):
        """Crea la pestaña avanzada."""
        config_frame = tk.Frame(parent, bg=PALETTE['blue_soft'])
        config_frame.pack(fill='both', expand=True, padx=20, pady=20)
        card = tk.LabelFrame(config_frame, text="Persistencia y mantenimiento", bg=PALETTE['white'],
                             fg=PALETTE['blue_dark'], font=('Segoe UI Semibold', 11), padx=18, pady=16)
        card.pack(fill='x')
        
        # Límite de historial
        history_frame = tk.Frame(card, bg=PALETTE['white'])
        history_frame.pack(fill='x', pady=10)
        
        tk.Label(history_frame, text="Límite de historial:", 
                font=('Segoe UI', 10), bg=PALETTE['white']).pack(side='left')
        
        self.max_history_var = tk.IntVar(value=self.manager.config['max_history'])
        history_spin = self._create_spinbox(
            history_frame,
            self.max_history_var,
            from_=100,
            to=1000,
            increment=50,
            width=10,
        )
        history_spin.pack(side='left', padx=10)
        
        # Sonido
        self.sound_var = tk.BooleanVar(value=self.manager.config['sound_enabled'])
        tk.Checkbutton(card, text="Habilitar sonidos de notificación",
                      variable=self.sound_var, bg=PALETTE['white'],
                      font=('Segoe UI', 10)).pack(anchor='w', pady=10)

        self.persist_login_var = tk.BooleanVar(value=self.manager.config.get('persist_login_history', False))
        tk.Checkbutton(
            card,
            text="Guardar inicios de sesión en el historial",
            variable=self.persist_login_var,
            bg=PALETTE['white'],
            font=('Segoe UI', 10),
        ).pack(anchor='w', pady=5)

        info = tk.Label(
            card,
            text=(
                "Las notificaciones normales se muestran una sola vez por clave.\n"
                "Los recordatorios generales reutilizan la misma entrada de historial.\n"
                "Las alertas de stock bajo solo actualizan la entrada existente por producto."
            ),
            justify='left',
            bg=PALETTE['white'],
            fg=PALETTE['gray_text'],
            font=('Segoe UI', 10),
        )
        info.pack(anchor='w', pady=(10, 16))
        
        # Limpiar historial
        tk.Label(card, text="Mantenimiento:", font=('Segoe UI Semibold', 11),
                bg=PALETTE['white']).pack(anchor='w', pady=(8, 10))
        
        clear_btn = tk.Button(card, text="Limpiar Todo el Historial",
                             command=self._confirm_clear_history,
                             bg=PALETTE['danger'], fg='white', padx=20, pady=5,
                             font=('Segoe UI', 10), cursor='hand2')
        clear_btn.pack(anchor='w')

    def _create_help_tab(self, parent):
        frame = tk.Frame(parent, bg=PALETTE['blue_soft'])
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        card = tk.LabelFrame(frame, text="Cómo usar las notificaciones", bg=PALETTE['white'],
                             fg=PALETTE['blue_dark'], font=('Segoe UI Semibold', 11), padx=18, pady=16)
        card.pack(fill='both', expand=True)

        help_text = tk.Text(card, wrap='word', font=('Segoe UI', 10), relief='flat', bg=PALETTE['white'])
        help_text.pack(fill='both', expand=True)
        help_text.insert(
            '1.0',
            (
                "1. Notificación normal\n"
                "Se muestra una sola vez por clave y no reaparece al reiniciar.\n\n"
                "2. Recordatorio general\n"
                "Puede repetirse cada cierto número de horas si activas esa opción.\n"
                "La entrada del historial se reutiliza en lugar de duplicarse.\n\n"
                "3. Stock bajo\n"
                "Se recuerda por producto cada cierto tiempo mientras siga activo.\n"
                "No crea múltiples entradas en historial para el mismo producto.\n\n"
                "4. Historial\n"
                "Solo guarda eventos persistentes y válidos. Las visualizaciones temporales no saturan el centro.\n\n"
                "5. Duración y posición\n"
                "Puedes ajustar cuánto duran en pantalla y dónde aparecen.\n\n"
                "6. Agrupación\n"
                "Evita disparos repetidos en pocos segundos para el mismo contenido.\n"
            ),
        )
        help_text.config(state='disabled')
    
    def _create_button(self, parent, text, command, style='primary'):
        """Crea un botón con estilo."""
        colors = {
            'primary': {'bg': PALETTE['blue_primary'], 'fg': 'white'},
            'secondary': {'bg': PALETTE['surface_alt'], 'fg': PALETTE['blue_dark']},
            'danger': {'bg': PALETTE['danger'], 'fg': 'white'}
        }
        
        btn = tk.Button(parent, text=text, command=command,
                       font=('Segoe UI Semibold', 10),
                       bg=colors[style]['bg'], fg=colors[style]['fg'],
                       padx=20, pady=8, cursor='hand2',
                       relief='flat', borderwidth=0)
        btn.pack(side='left', padx=5)
        
        # Hover effect
        def on_enter(e):
            btn['bg'] = self._darken_color(colors[style]['bg'], 0.1)
        
        def on_leave(e):
            btn['bg'] = colors[style]['bg']
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def _darken_color(self, color: str, factor: float) -> str:
        """Oscurece un color."""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = int(r * (1 - factor))
            g = int(g * (1 - factor))
            b = int(b * (1 - factor))
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return color
    
    def _load_config(self):
        """Carga la configuración actual."""
        self.duration_var.set(self.manager.config['default_duration'] // 1000)
        self.position_var.set(self.manager.config['position'])
        self.max_visible_var.set(self.manager.config['max_visible'])
        self.group_var.set(self.manager.config['group_similar'])
        self.time_window_var.set(self.manager.config['similar_time_window'])
        self.repeat_general_var.set(self.manager.config.get('repeat_general_notifications', False))
        self.general_hours_var.set(int(self.manager.config.get('general_reminder_hours', 5)))
        self.stock_minutes_var.set(int(self.manager.config.get('stock_reminder_minutes', 60)))
        self.type_vars['stock_alerts'].set(self.manager.config['stock_alerts'])
        self.type_vars['sales_alerts'].set(self.manager.config['sales_alerts'])
        self.type_vars['login_alerts'].set(self.manager.config['login_alerts'])
        self.type_vars['system_alerts'].set(self.manager.config['system_alerts'])
        self.compact_var.set(self.manager.config['compact_mode'])
        self.timestamp_var.set(self.manager.config['show_timestamp'])
        self.icon_var.set(self.manager.config['show_icon'])
        self.progress_var.set(self.manager.config['show_progress_bar'])
        self.font_var.set(self.manager.config['font_size'])
        self.anim_var.set(self.manager.config['animation_speed'])
        self.max_history_var.set(self.manager.config['max_history'])
        self.sound_var.set(self.manager.config['sound_enabled'])
        self.persist_login_var.set(self.manager.config.get('persist_login_history', False))
    
    def _save_config(self):
        """Guarda la configuración."""
        # General
        self.manager.config['default_duration'] = self.duration_var.get() * 1000
        self.manager.config['position'] = self.position_var.get()
        self.manager.config['max_visible'] = self.max_visible_var.get()
        self.manager.config['group_similar'] = self.group_var.get()
        self.manager.config['similar_time_window'] = self.time_window_var.get()
        self.manager.config['repeat_general_notifications'] = self.repeat_general_var.get()
        self.manager.config['general_reminder_hours'] = self.general_hours_var.get()
        self.manager.config['stock_reminder_minutes'] = self.stock_minutes_var.get()
        
        # Tipos
        self.manager.config['stock_alerts'] = self.type_vars['stock_alerts'].get()
        self.manager.config['sales_alerts'] = self.type_vars['sales_alerts'].get()
        self.manager.config['login_alerts'] = self.type_vars['login_alerts'].get()
        self.manager.config['system_alerts'] = self.type_vars['system_alerts'].get()
        
        # Apariencia
        self.manager.config['compact_mode'] = self.compact_var.get()
        self.manager.config['show_timestamp'] = self.timestamp_var.get()
        self.manager.config['show_icon'] = self.icon_var.get()
        self.manager.config['show_progress_bar'] = self.progress_var.get()
        self.manager.config['font_size'] = self.font_var.get()
        self.manager.config['animation_speed'] = self.anim_var.get()
        
        # Avanzado
        self.manager.config['max_history'] = self.max_history_var.get()
        self.manager.config['sound_enabled'] = self.sound_var.get()
        self.manager.config['persist_login_history'] = self.persist_login_var.get()
        
        # Guardar
        if self.manager.save_config():
            messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
            self.manager._reposition_notifications()
            self.destroy()
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")
    
    def _reset_defaults(self):
        """Restaura la configuración predeterminada."""
        if messagebox.askyesno("Confirmar", "¿Restaurar configuración predeterminada?\n\nSe perderán todos los cambios personalizados."):
            default_config = {
                'default_duration': 5000,
                'position': 'top_right',
                'max_visible': 5,
                'group_similar': True,
                'similar_time_window': 30,
                'stock_alerts': True,
                'sales_alerts': True,
                'login_alerts': True,
                'system_alerts': True,
                'compact_mode': False,
                'show_timestamp': True,
                'show_icon': True,
                'show_progress_bar': True,
                'font_size': 10,
                'animation_speed': 'normal',
                'max_history': 500,
                'sound_enabled': False,
                'general_reminder_hours': 5,
                'repeat_general_notifications': False,
                'stock_reminder_minutes': 60,
                'persist_login_history': False,
            }
            
            for key, value in default_config.items():
                self.manager.config[key] = value
            
            # Recargar las variables en la interfaz
            self._load_config()
            self.destroy()
            SettingsWindow(self.master, self.manager)
    
    def _confirm_clear_history(self):
        """Confirma limpieza de historial."""
        if messagebox.askyesno("Confirmar", "¿Eliminar TODO el historial de notificaciones?\n\nEsta acción no se puede deshacer."):
            self.manager.clear_history()
            messagebox.showinfo("Éxito", "Historial limpiado correctamente.")
