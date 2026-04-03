"""
Archivo de entrada de la aplicacion ERP de escritorio.

Este modulo levanta Tkinter, inicializa la conexion principal a SQLite,
construye el contexto compartido de la sesion y conecta la navegacion de la
UI con los casos de uso ya encapsulados en `erp/`.

Responsabilidades principales:
- crear la aplicacion y el tema visual global,
- resolver autenticacion inicial,
- mantener usuario actual, secciones permitidas y contenedores de frames,
- actuar como composition root de servicios compartidos para la UI.
"""

import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

from database import DBManager
from erp.data.repositories.backup_repository import BackupRepository
from erp.data.repositories.user_repository import UserRepository
from erp.domain.services.access_control import (
    CONFIG_SECTION,
    allowed_sections_for_role,
    can_access_section,
)
from erp.domain.services.backup_service import BackupService
from erp.domain.use_cases.auth.login_user import LoginUser
from erp.infrastructure.io.file_manager import FileManager
from erp.ui.frames import (
    ClientsFrame,
    ConfigFrame,
    DashboardFrame,
    ProductFrame,
    RegistroVentasFrame,
    SalesFrame,
    SupplierFrame,
    WholesaleSalesFrame,
)
from erp.ui.notifications import NotificationManager
from erp.ui.shared import PALETTE, apply_app_theme, normalize_theme_name, resolve_resource_path

# Configurar logging profesional
def setup_logging():
    """Configura el sistema de logging de la aplicacion."""
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"erp_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class AppConfig:
    """Configuracion centralizada de la aplicacion."""
    
    APP_NAME = "TECH SYSTEMS ERP"
    APP_VERSION = "2.0.0"
    APP_COMPANY = "Tech Systems Solutions"
    MIN_WIDTH = 1200
    MIN_HEIGHT = 760
    SIDEBAR_WIDTH = 272
    
    # Colores profesionales
    COLORS = {
        'primary': '#2c3e50',
        'secondary': '#3498db',
        'success': '#27ae60',
        'danger': '#e74c3c',
        'warning': '#f39c12',
        'info': '#3498db',
        'dark': '#2c3e50',
        'light': '#ecf0f1',
        'sidebar_bg': '#1a2634',
        'topbar_bg': '#ffffff',
    }
    
    # Rutas de recursos
    ASSETS_DIR = Path(__file__).resolve().parent / "assets"
    ICON_FILE = ASSETS_DIR / "logo.ico"
    LOGO_FILE = ASSETS_DIR / "logo.jpg"

class ExceptionHandler:
    """Manejador global de excepciones para la aplicacion."""
    
    def __init__(self, app=None):
        self.app = app
        
    def handle_exception(self, exc_type, exc_value, exc_tb):
        """Maneja excepciones no capturadas."""
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"Excepcion no manejada:\n{error_msg}")
        
        if self.app:
            try:
                messagebox.showerror(
                    "Error Critico",
                    f"Ha ocurrido un error inesperado.\n\n{exc_value}\n\n"
                    "El error ha sido registrado en el archivo de logs.\n"
                    "Por favor, contacte al soporte tecnico.",
                    parent=self.app
                )
            except:
                pass
        
        # Cerrar la aplicacion de manera controlada
        if self.app:
            try:
                self.app.on_closing()
            except:
                pass
        sys.exit(1)

class ERPApp(tk.Tk):
    """Aplicacion principal del sistema ERP."""

    def __init__(self):
        try:
            super().__init__()
            logger.info("Iniciando aplicacion ERP...")
            
            # Configurar manejador de excepciones
            self.exception_handler = ExceptionHandler(self)
            sys.excepthook = self.exception_handler.handle_exception
            
            # Configurar ventana principal
            self.title(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
            self.state("zoomed")
            self.minsize(AppConfig.MIN_WIDTH, AppConfig.MIN_HEIGHT)
            self.base_dir = Path(__file__).resolve().parent
            
            # Inicializar componentes
            self._init_components()
            
            # Aplicar tema y configuracion
            self.current_theme = self.db.get_config("ui_theme", "light") or "light"
            self.style = apply_app_theme(self, self.current_theme)
            self._setup_window_icon()
            
            # Mostrar pantalla de login
            self.show_login()
            
            logger.info("Aplicacion inicializada correctamente")
            
        except Exception as e:
            logger.critical(f"Error al inicializar la aplicacion: {e}")
            messagebox.showerror(
                "Error de Inicializacion",
                f"No se pudo iniciar la aplicacion.\n\nError: {e}\n\n"
                "Revise el archivo de logs para mas detalles."
            )
            sys.exit(1)

    def _init_components(self):
        """Inicializa todos los componentes de la aplicacion."""
        try:
            self.db = DBManager()
            self.user_repository = UserRepository(self.db)
            self.backup_repository = BackupRepository(self.db)
            self.backup_service = BackupService(self.db, self.backup_repository)
            self.login_user = LoginUser(self.user_repository)
            self.file_manager = FileManager(self.db)
            self.notification_manager = NotificationManager(self, self.db)
            self.current_user = None
            self.allowed_sections = set()
            self.nav_widgets = {}
            self.current_section = tk.StringVar(value="Dashboard")
            self._session_start_time = datetime.now()
            self._stock_monitor_job = None
            self._detached_windows = {}
            
            # Variables de estado
            self._is_logged_in = False
            self._is_closing = False
            
        except Exception as e:
            logger.error(f"Error al inicializar componentes: {e}")
            raise

    def _setup_window_icon(self):
        """Configura el icono de la ventana."""
        if AppConfig.ICON_FILE.exists():
            try:
                self.iconbitmap(default=str(AppConfig.ICON_FILE))
                logger.debug("Icono de ventana cargado correctamente")
            except Exception as e:
                logger.warning(f"No se pudo cargar el icono: {e}")

    def apply_ui_theme(self, theme_name, *, persist=False):
        """Aplica el tema seleccionado a toda la aplicación en tiempo real."""
        normalized_theme = normalize_theme_name(theme_name)
        self.current_theme = normalized_theme
        self.style = apply_app_theme(self, normalized_theme)
        if persist:
            self.db.set_config("ui_theme", normalized_theme)

        for window in list(self._detached_windows.values()):
            if window and window.winfo_exists():
                apply_app_theme(window, normalized_theme)
                try:
                    window.configure(bg=PALETTE["blue_soft"])
                except tk.TclError:
                    pass

    def show_login(self):
        """Muestra la pantalla de inicio de sesion."""
        try:
            self.login_frame = ttk.Frame(self, style="App.TFrame")
            self.login_frame.pack(fill="both", expand=True, padx=40, pady=36)
            self.login_frame.columnconfigure(0, weight=1)
            self.login_frame.columnconfigure(1, weight=1)
            self.login_frame.rowconfigure(0, weight=1)

            # Panel izquierdo con informacion
            intro = ttk.Frame(self.login_frame, padding=36, style="AltSurface.TFrame")
            intro.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
            intro.columnconfigure(0, weight=1)
            intro.rowconfigure(4, weight=1)

            # Logo de la empresa
            self._load_company_logo(intro)
            
            # Panel derecho con formulario de login
            login_container = self._create_login_form()
            
            # Configurar atajos de teclado
            self.password_entry.bind("<Return>", lambda _event: self.authenticate())
            self.username_entry.focus_set()
            
            logger.info("Pantalla de login mostrada")
            
        except Exception as e:
            logger.error(f"Error al mostrar login: {e}")
            raise

    def _load_company_logo(self, parent):
        """Carga y muestra el logo de la empresa."""
        row_index = 0
        if AppConfig.LOGO_FILE.exists():
            try:
                logo_image = Image.open(AppConfig.LOGO_FILE)
                logo_image = logo_image.resize((200, 200), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_image)
                logo_label = ttk.Label(parent, image=logo_photo)
                logo_label.image = logo_photo
                logo_label.grid(row=row_index, column=0, sticky="w", pady=(0, 10))
                row_index += 1
            except Exception as e:
                logger.warning(f"No se pudo cargar el logo: {e}")
        
        ttk.Label(parent, text=AppConfig.APP_NAME, style="IntroTitle.TLabel").grid(
            row=row_index, column=0, sticky="w"
        )
        ttk.Label(
            parent,
            text="Gestion comercial y punto de venta en una sola plataforma.",
            style="IntroBody.TLabel",
        ).grid(row=row_index + 1, column=0, sticky="w", pady=(10, 12))
        ttk.Label(
            parent,
            text="Accede para administrar ventas, inventario, clientes y reportes.",
            style="IntroMuted.TLabel",
        ).grid(row=row_index + 2, column=0, sticky="w")

    def _create_login_form(self):
        """Crea el formulario de inicio de sesion."""
        login_container = ttk.LabelFrame(
            self.login_frame,
            text="Acceso al sistema",
            padding=28,
            style="Card.TLabelframe",
        )
        login_container.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        login_container.columnconfigure(0, weight=1)

        ttk.Label(login_container, text="Inicio de sesion", style="Subheader.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 18)
        )

        fields = ttk.Frame(login_container, style="Surface.TFrame")
        fields.grid(row=1, column=0, sticky="ew")
        fields.columnconfigure(0, weight=1)

        ttk.Label(fields, text="Usuario", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w")
        self.username_entry = ttk.Entry(fields, width=30)
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))

        ttk.Label(fields, text="Contrasena", style="FormLabel.TLabel").grid(row=2, column=0, sticky="w")
        password_row = ttk.Frame(fields, style="Surface.TFrame")
        password_row.grid(row=3, column=0, sticky="ew", pady=(4, 18))
        password_row.columnconfigure(0, weight=1)

        self._password_visible = False
        self.password_entry = ttk.Entry(password_row, show="*", width=30)
        self.password_entry.grid(row=0, column=0, sticky="ew")

        self.password_toggle_button = ttk.Button(
            password_row,
            text="👁",
            width=3,
            style="Secondary.TButton",
            command=self.toggle_password_visibility,
        )
        self.password_toggle_button.grid(row=0, column=1, padx=(8, 0))

        self.login_button = ttk.Button(
            login_container,
            text="Acceder",
            style="Primary.TButton",
            command=self.authenticate,
        )
        self.login_button.grid(row=2, column=0, sticky="ew")

        # Mensaje informativo
        info_text = "Presione Enter para confirmar el acceso.\nCredenciales seguras con cifrado."
        ttk.Label(
            login_container,
            text=info_text,
            style="Muted.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(14, 0))

        self.login_status_var = tk.StringVar(value="Listo para iniciar sesión.")
        self.login_status_label = ttk.Label(
            login_container,
            textvariable=self.login_status_var,
            style="Muted.TLabel",
            wraplength=360,
        )
        self.login_status_label.grid(row=4, column=0, sticky="w", pady=(10, 0))

        self.login_progress = ttk.Progressbar(login_container, mode="indeterminate")
        self.login_progress.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self.login_progress.grid_remove()

        # Verificar si hay usuarios registrados
        if not self.user_repository.has_users():
            ttk.Label(
                login_container,
                text="No hay usuarios registrados en esta base.\nCree uno antes de iniciar sesion.",
                style="Muted.TLabel",
                wraplength=360,
            ).grid(row=6, column=0, sticky="w", pady=(10, 0))
            self.login_button.state(["disabled"])
            logger.warning("No hay usuarios registrados en la base de datos")

        return login_container

    def toggle_password_visibility(self):
        """Alterna entre mostrar y ocultar la contraseña en el login."""
        self._password_visible = not self._password_visible
        self.password_entry.configure(show="" if self._password_visible else "*")
        self.password_toggle_button.configure(text="🙈" if self._password_visible else "👁")

    def _set_login_loading(self, is_loading, status_text=None):
        """Activa o desactiva el estado visual de carga del login."""
        if status_text is not None and hasattr(self, "login_status_var"):
            self.login_status_var.set(status_text)

        if is_loading:
            self.login_button.state(["disabled"])
            self.username_entry.state(["disabled"])
            self.password_entry.state(["disabled"])
            self.password_toggle_button.state(["disabled"])
            self.login_progress.grid()
            self.login_progress.start(12)
        else:
            if self.user_repository.has_users():
                self.login_button.state(["!disabled"])
            self.username_entry.state(["!disabled"])
            self.password_entry.state(["!disabled"])
            self.password_toggle_button.state(["!disabled"])
            self.login_progress.stop()
            self.login_progress.grid_remove()

    def authenticate(self):
        """Autentica al usuario en el sistema con feedback visual de carga."""
        self._set_login_loading(True, "Verificando credenciales...")
        self.after(350, self._perform_authentication)

    def _perform_authentication(self):
        """Ejecuta la autenticación real después de mostrar el estado de carga."""
        try:
            username = self.username_entry.get().strip()
            password = self.password_entry.get()
            
            logger.info(f"Intento de autenticacion para usuario: {username}")
            
            response = self.login_user.execute(username, password)

            if response.status == "missing_credentials":
                self._set_login_loading(False, response.message or "Complete usuario y contraseña.")
                messagebox.showwarning(
                    "Datos incompletos",
                    response.message,
                    parent=self,
                )
                return

            if response.status == "missing_users":
                self._set_login_loading(False, response.message or "No hay usuarios registrados.")
                messagebox.showerror(
                    "Sin usuarios",
                    response.message,
                    parent=self,
                )
                return

            if response.ok:
                self.login_status_var.set("Acceso correcto. Cargando el sistema...")
                self.current_user = response.user
                self.allowed_sections = allowed_sections_for_role(self.current_user[2])
                self._is_logged_in = True
                
                logger.info(f"Usuario autenticado: {username} (Rol: {self.current_user[2]})")
                
                self.login_frame.destroy()
                self.notification_manager.notify_login(self.current_user[1], self.current_user[2])
                self.show_main_interface()
                return

            self._set_login_loading(False, response.message or "Usuario o contraseña incorrectos.")
            logger.warning(f"Intento de autenticacion fallido para: {username}")
            messagebox.showerror(
                "Error de Autenticacion",
                response.message or "Usuario o contrasena incorrectos",
                parent=self
            )
            
        except Exception as e:
            self._set_login_loading(False, "Ocurrió un error al validar el acceso.")
            logger.error(f"Error durante autenticacion: {e}")
            messagebox.showerror(
                "Error",
                "Ocurrio un error durante la autenticacion.\nRevise el archivo de logs.",
                parent=self
            )

    def show_main_interface(self):
        """Muestra la interfaz principal de la aplicacion."""
        try:
            logger.info("Mostrando interfaz principal")
            
            self.container = ttk.Frame(self, style="App.TFrame")
            self.container.pack(fill="both", expand=True)
            self.container.columnconfigure(0, weight=1)
            self.container.rowconfigure(1, weight=1)

            # Barra superior con navegacion principal
            self.nav_frame = ttk.Frame(
                self.container,
                padding=(20, 14, 20, 12),
                style="Topbar.TFrame"
            )
            self.nav_frame.grid(row=0, column=0, sticky="ew")

            # Frame de contenido
            self.content_frame = ttk.Frame(
                self.container,
                padding=(24, 18, 24, 24),
                style="App.TFrame"
            )
            self.content_frame.grid(row=1, column=0, sticky="nsew")
            self.content_frame.rowconfigure(0, weight=1)
            self.content_frame.columnconfigure(0, weight=1)

            self._build_sidebar()

            # Iniciar verificacion periodica de stock
            self._start_stock_monitoring()
            
            self.notification_manager.notify_system_info(f"v{AppConfig.APP_VERSION}")
            self._on_nav_click("Dashboard")
            self.after(150, self._run_startup_backup_checks)
            
        except Exception as e:
            logger.error(f"Error al mostrar interfaz principal: {e}")
            raise

    def _run_startup_backup_checks(self):
        """Ejecuta respaldo automatico y alerta de vigencia al iniciar sesion."""
        auto_result = None
        try:
            auto_result = self.backup_service.run_automatic_backup_if_due(trigger="startup")
        except Exception as exc:
            logger.error(f"Error al ejecutar respaldo automatico de inicio: {exc}")

        if auto_result and auto_result.ok:
            self.notification_manager.notify_system_info(
                f"Respaldo automatico creado: {auto_result.file_name}",
                level="info",
            )
        elif auto_result and not auto_result.ok:
            logger.warning(f"No se pudo generar el respaldo automatico: {auto_result.message}")

        try:
            alert_status = self.backup_service.get_alert_status()
        except Exception as exc:
            logger.error(f"Error al verificar estado de respaldos: {exc}")
            return

        if alert_status.should_alert:
            self._show_backup_alert(alert_status.message)

    def _show_backup_alert(self, message):
        """Muestra una alerta visible cuando no existe un respaldo reciente."""
        self.notification_manager.notify_system_info(message, level="warning")
        if messagebox.askyesno(
            "Alerta de respaldos",
            f"{message}\n\nDesea abrir Configuracion para crear o revisar un respaldo ahora?",
            parent=self,
        ):
            self.open_backup_settings()

    def _start_stock_monitoring(self):
        """Inicia el monitoreo periodico de stock."""
        self._stop_stock_monitoring()

        def check_stock_periodically():
            self._stock_monitor_job = None
            try:
                self.notification_manager.check_stock_alerts()
                if self._is_logged_in and not self._is_closing:
                    self._stock_monitor_job = self.after(300000, check_stock_periodically)  # 5 minutos
            except Exception as e:
                logger.error(f"Error en monitoreo de stock: {e}")
                if self._is_logged_in and not self._is_closing:
                    self._stock_monitor_job = self.after(300000, check_stock_periodically)

        check_stock_periodically()

    def _stop_stock_monitoring(self):
        """Detiene el monitoreo periódico de stock cuando ya no aplica."""
        if self._stock_monitor_job is None:
            return
        try:
            self.after_cancel(self._stock_monitor_job)
        except Exception:
            pass
        self._stock_monitor_job = None

    def _build_sidebar(self):
        """Construye la barra superior de navegacion principal."""
        try:
            for child in self.nav_frame.winfo_children():
                child.destroy()
            self.nav_widgets.clear()
            self.nav_frame.columnconfigure(1, weight=1)

            ttk.Label(self.nav_frame, text=AppConfig.APP_NAME, style="TopbarTitle.TLabel").grid(
                row=0, column=0, sticky="w", padx=(0, 18)
            )

            # Definicion de frames
            class NotificationsFrame(ttk.Frame):
                def __init__(self, parent, app):
                    super().__init__(parent)
                    ttk.Label(self, text="Centro de Notificaciones", style="Subheader.TLabel").pack(pady=20)

            self.frames = {
                "Dashboard": DashboardFrame,
                "Ventas (POS)": SalesFrame,
                "Registro de Ventas": RegistroVentasFrame,
                "Clientes": ClientsFrame,
                "Productos": ProductFrame,
                "Proveedores": SupplierFrame,
                CONFIG_SECTION: ConfigFrame,
                "Notificaciones": NotificationsFrame,
            }

            nav_order = [
                "Dashboard",
                "Ventas (POS)",
                "Registro de Ventas",
                "Clientes",
                "Productos",
                "Proveedores",
                CONFIG_SECTION,
            ]

            nav_host = ttk.Frame(self.nav_frame, style="Topbar.TFrame")
            nav_host.grid(row=0, column=1, sticky="w")

            visible_sections = [section for section in nav_order if section in self.allowed_sections]

            for idx, section in enumerate(visible_sections):
                button = ttk.Button(
                    nav_host,
                    text=section,
                    style="TopbarNav.TButton",
                    command=lambda value=section: self._on_nav_click(value),
                )
                button.pack(side="left", padx=(0, 8 if idx < len(visible_sections) - 1 else 0))
                self.nav_widgets[section] = button

            actions = ttk.Frame(self.nav_frame, style="Topbar.TFrame")
            actions.grid(row=0, column=2, sticky="e")
            ttk.Label(
                actions,
                text=f"{self.current_user[1]} | {self.current_user[2]}",
                style="TopbarInfo.TLabel",
            ).pack(side="left", padx=(0, 10))
            ttk.Button(
                actions,
                text="Avisos",
                command=self.notification_manager.show_notification_center,
                style="TopbarAction.TButton",
            ).pack(side="left", padx=(0, 8))
            ttk.Button(
                actions,
                text="Salir",
                command=self.logout,
                style="TopbarDanger.TButton",
            ).pack(side="left")
            
            logger.debug(f"Barra lateral construida con {len(visible_sections)} secciones")
            
        except Exception as e:
            logger.error(f"Error al construir barra lateral: {e}")
            raise

    def _on_nav_click(self, title):
        """Maneja los clics en los botones de navegacion."""
        try:
            if not can_access_section(self.current_user[2], title):
                messagebox.showwarning(
                    "Acceso restringido",
                    "Su rol no tiene permisos para acceder a este modulo.",
                    parent=self,
                )
                return
            
            frame_class = self.frames[title]
            self.current_section.set(title)
            self._set_active_nav(title)

            if title in {"Ventas (POS)", "Ventas Mayoristas"}:
                self.open_detached_sales_window(title, frame_class)
                logger.debug(f"Navegacion desacoplada a: {title}")
                return

            self.show_frame(frame_class, title)
            
            logger.debug(f"Navegacion a: {title}")
            
        except Exception as e:
            logger.error(f"Error en navegacion a {title}: {e}")
            messagebox.showerror(
                "Error",
                f"No se pudo cargar el modulo {title}.\nError: {e}",
                parent=self
            )

    def _set_active_nav(self, selected_title):
        """Resalta el boton de navegacion activo."""
        for title, widget in self.nav_widgets.items():
            widget.configure(style="TopbarNavAccent.TButton" if title == selected_title else "TopbarNav.TButton")
    def open_detached_sales_window(self, title, frame_class):
        """Abre o reutiliza una ventana dedicada para ventas."""
        existing = self._detached_windows.get(title)
        if existing and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_force()
            self._show_detached_window_placeholder(title)
            return

        window = tk.Toplevel(self)
        window.title(f"{AppConfig.APP_NAME} | {title}")
        window.configure(bg=PALETTE["blue_soft"])
        window.state("zoomed")
        window.minsize(1240, 780)
        window.protocol("WM_DELETE_WINDOW", lambda current=title: self._close_detached_window(current, redirect_to_dashboard=True))
        self._detached_windows[title] = window
        apply_app_theme(window, self.current_theme)

        shell = ttk.Frame(window, style="App.TFrame", padding=(18, 18, 18, 18))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        header = ttk.Frame(shell, style="Topbar.TFrame", padding=(18, 16, 18, 16))
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=title, style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Ventana operativa dedicada. La barra de Windows permanece visible y la lógica central de ventas no cambia.",
            style="Muted.TLabel",
            wraplength=860,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(header, text="Cerrar ventana", command=lambda current=title: self._close_detached_window(current, redirect_to_dashboard=True), style="Secondary.TButton").grid(
            row=0, column=1, rowspan=2, sticky="e"
        )

        body = ttk.Frame(shell, style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        frame = frame_class(body, self)
        frame.grid(row=0, column=0, sticky="nsew")

        self._show_detached_window_placeholder(title)

    def _show_detached_window_placeholder(self, title):
        """Muestra una tarjeta de estado en el panel principal cuando la sección vive en otra ventana."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        card = ttk.LabelFrame(self.content_frame, text=title, padding=24, style="Card.TLabelframe")
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text=f"{title} se ejecuta en una ventana dedicada.", style="Subheader.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            card,
            text="Use el botón inferior para traer la ventana al frente. Esta separación mejora el espacio operativo sin mover la lógica de ventas, recibos ni cobro fuera de su flujo actual.",
            style="Muted.TLabel",
            wraplength=760,
        ).grid(row=1, column=0, sticky="w", pady=(8, 18))
        ttk.Button(
            card,
            text="Abrir o enfocar ventana",
            style="Primary.TButton",
            command=lambda current=title: self._focus_detached_window(current),
        ).grid(row=2, column=0, sticky="w")

    def _focus_detached_window(self, title):
        window = self._detached_windows.get(title)
        if window and window.winfo_exists():
            window.deiconify()
            window.lift()
            window.focus_force()

    def _close_detached_window(self, title, *, redirect_to_dashboard=False):
        window = self._detached_windows.pop(title, None)
        if window and window.winfo_exists():
            window.destroy()
        if redirect_to_dashboard and self._is_logged_in and hasattr(self, "content_frame") and self.content_frame.winfo_exists():
            self.current_section.set("Dashboard")
            self._set_active_nav("Dashboard")
            self.show_frame(self.frames["Dashboard"], "Dashboard")
            self.deiconify()
            self.lift()
            self.focus_force()

    def _close_detached_windows(self):
        for title in list(self._detached_windows.keys()):
            self._close_detached_window(title, redirect_to_dashboard=False)

    def show_frame(self, frame_class, title):
        """Muestra un frame especifico en el area de contenido."""
        try:
            for widget in self.content_frame.winfo_children():
                widget.destroy()

            frame = frame_class(self.content_frame, self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.current_frame = frame
            
        except Exception as e:
            logger.error(f"Error al mostrar frame {title}: {e}")
            raise

    def open_product_editor(self, product_id):
        """Navega al módulo de productos y enfoca un producto específico para edición."""
        title = "Productos"
        frame_class = self.frames[title]
        self.current_section.set(title)
        self._set_active_nav(title)
        self.show_frame(frame_class, title)

        frame = getattr(self, "current_frame", None)
        if frame and hasattr(frame, "focus_product"):
            frame.focus_product(product_id)

    def open_backup_settings(self):
        """Navega a Configuracion y enfoca la pestaña de respaldos."""
        title = next(
            (section for section in self.frames if str(section).lower().startswith("configur")),
            None,
        )
        if not title:
            return

        self.current_section.set(title)
        self._set_active_nav(title)
        self.show_frame(self.frames[title], title)

        frame = getattr(self, "current_frame", None)
        if frame and hasattr(frame, "focus_backup_tab"):
            frame.focus_backup_tab()

    def _confirm_session_end_backup(self, *, trigger: str, continue_action_label: str) -> bool:
        """Ejecuta el respaldo automatico al terminar sesion cuando aplica."""
        if not self._is_logged_in:
            return True

        auto_result = None
        try:
            auto_result = self.backup_service.run_automatic_backup_if_due(trigger=trigger)
        except Exception as exc:
            logger.error(f"Error al ejecutar respaldo automatico de fin de sesion ({trigger}): {exc}")
            return True

        if auto_result and auto_result.ok:
            logger.info(f"Respaldo automatico generado al finalizar sesion: {auto_result.file_name}")
            return True

        if auto_result and not auto_result.ok:
            return messagebox.askyesno(
                "Respaldo automatico fallido",
                (
                    f"{auto_result.message}\n\n"
                    f"Desea {continue_action_label} de todos modos sin generar el respaldo automatico?"
                ),
                parent=self,
            )

        return True

    def logout(self):
        """Cierra la sesion actual."""
        try:
            if messagebox.askyesno("Cerrar sesion", "Desea cerrar sesion?", parent=self):
                if not self._confirm_session_end_backup(
                    trigger="logout",
                    continue_action_label="cerrar sesion",
                ):
                    return
                logger.info(f"Usuario {self.current_user[1]} cerro sesion")
                self._is_logged_in = False
                self._stop_stock_monitoring()
                self._close_detached_windows()
                self.container.destroy()
                self.current_user = None
                self.allowed_sections.clear()
                self.nav_widgets.clear()
                self.show_login()
                
        except Exception as e:
            logger.error(f"Error durante logout: {e}")

    def on_closing(self):
        """Maneja el cierre de la aplicacion."""
        if self._is_closing:
            return
            
        self._is_closing = True
        
        try:
            if messagebox.askokcancel("Salir", "Desea salir del sistema?", parent=self):
                logger.info(f"Aplicacion cerrada por el usuario")
                
                # Registrar tiempo de sesion
                if self._is_logged_in:
                    session_duration = datetime.now() - self._session_start_time
                    logger.info(f"Duracion de sesion: {session_duration}")
                    if not self._confirm_session_end_backup(
                        trigger="on_close",
                        continue_action_label="salir",
                    ):
                        self._is_closing = False
                        return

                self._stop_stock_monitoring()
                self._close_detached_windows()

                if hasattr(self, 'notification_manager'):
                    self.notification_manager.shutdown()
                
                # Cerrar conexiones
                if hasattr(self, 'db'):
                    self.db.close()
                    logger.debug("Conexion a base de datos cerrada")
                
                self.destroy()
                return

            self._is_closing = False
                
        except Exception as e:
            logger.error(f"Error al cerrar aplicacion: {e}")
            self.destroy()


def main():
    """Punto de entrada principal de la aplicacion."""
    try:
        logger.info("=" * 60)
        logger.info(f"Iniciando {AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        logger.info(f"Compañia: {AppConfig.APP_COMPANY}")
        logger.info("=" * 60)
        
        app = ERPApp()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
        
    except Exception as e:
        logger.critical(f"Error fatal en la aplicacion: {e}")
        logger.critical(traceback.format_exc())
        messagebox.showerror(
            "Error Fatal",
            f"No se pudo iniciar la aplicacion.\n\nError: {e}\n\n"
            "Revise el archivo de logs para mas detalles."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
