"""
main.py
Punto de entrada de la aplicacion ERP.
"""

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from database import DBManager
from file_manager import FileManager
from frames import (
    ClientsFrame,
    ConfigFrame,
    DashboardFrame,
    ProductFrame,
    RegistroVentasFrame,
    SupplierFrame,
    UnifiedPOSFrame,
)
from frames.notificaciones import NotificationManager
from frames.ui import apply_app_theme, resolve_resource_path


class ERPApp(tk.Tk):
    """Aplicacion principal del sistema ERP."""

    def __init__(self):
        super().__init__()

        self.title("TECH SISTEMS ERP")
        self.geometry("1440x920")
        self.minsize(1200, 760)
        self.base_dir = Path(__file__).resolve().parent

        self.db = DBManager()
        self.file_manager = FileManager(self.db)
        self.notification_manager = NotificationManager(self, self.db)
        self.current_user = None
        self.nav_widgets = {}
        self.current_section = tk.StringVar(value="Dashboard")

        self.style = apply_app_theme(self)
        self._setup_window_icon()
        self.show_login()

    def _setup_window_icon(self):
        icon_candidates = [
            resolve_resource_path("assets", "icons", "app.ico"),
            resolve_resource_path("assets", "app.ico"),
            self.base_dir / "app.ico",
        ]
        for icon_path in icon_candidates:
            if icon_path.exists():
                try:
                    self.iconbitmap(default=str(icon_path))
                except Exception:
                    pass
                break

    def show_login(self):
        self.login_frame = ttk.Frame(self, style="App.TFrame")
        self.login_frame.pack(fill="both", expand=True, padx=40, pady=36)
        self.login_frame.columnconfigure(0, weight=1)
        self.login_frame.columnconfigure(1, weight=1)
        self.login_frame.rowconfigure(0, weight=1)

        intro = ttk.Frame(self.login_frame, padding=36, style="AltSurface.TFrame")
        intro.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        intro.columnconfigure(0, weight=1)
        intro.rowconfigure(3, weight=1)

        ttk.Label(intro, text="TECH SISTEMS ERP", style="IntroTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            intro,
            text="Gestion comercial y punto de venta en una sola plataforma.",
            style="IntroBody.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(10, 12))
        ttk.Label(
            intro,
            text="Accede para administrar ventas, inventario, clientes y reportes.",
            style="IntroMuted.TLabel",
        ).grid(row=2, column=0, sticky="w")

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
        self.username_entry.insert(0, "admin")

        ttk.Label(fields, text="Contrasena", style="FormLabel.TLabel").grid(row=2, column=0, sticky="w")
        self.password_entry = ttk.Entry(fields, show="*", width=30)
        self.password_entry.grid(row=3, column=0, sticky="ew", pady=(4, 18))
        self.password_entry.insert(0, "1234")

        ttk.Button(
            login_container,
            text="Acceder",
            style="Primary.TButton",
            command=self.authenticate,
        ).grid(row=2, column=0, sticky="ew")

        ttk.Label(
            login_container,
            text="Sugerencia: Enter tambien confirma el acceso.",
            style="Muted.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(14, 0))

        self.password_entry.bind("<Return>", lambda _event: self.authenticate())

    def authenticate(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        user = self.db.fetch(
            "SELECT id, nombre, rol FROM Usuarios WHERE usuario = ? AND contrasena = ?",
            (username, password),
        )

        if user:
            self.current_user = user[0]
            self.login_frame.destroy()
            self.notification_manager.notify_login(self.current_user[1], self.current_user[2])
            self.show_main_interface()
            return

        messagebox.showerror("Error", "Usuario o contrasena incorrectos", parent=self)

    def show_main_interface(self):
        self.container = ttk.Frame(self, style="App.TFrame")
        self.container.pack(fill="both", expand=True)
        self.container.columnconfigure(1, weight=1)
        self.container.rowconfigure(0, weight=1)

        self.nav_frame = ttk.Frame(self.container, width=272, padding=18, style="Sidebar.TFrame")
        self.nav_frame.grid(row=0, column=0, sticky="ns")
        self.nav_frame.grid_propagate(False)
        self.nav_frame.columnconfigure(0, weight=1)

        content_shell = ttk.Frame(self.container, style="App.TFrame")
        content_shell.grid(row=0, column=1, sticky="nsew")
        content_shell.rowconfigure(1, weight=1)
        content_shell.columnconfigure(0, weight=1)

        topbar = ttk.Frame(content_shell, padding=(24, 18, 24, 12), style="Topbar.TFrame")
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.columnconfigure(0, weight=1)

        ttk.Label(topbar, text="Panel principal", style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(topbar, textvariable=self.current_section, style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Button(
            topbar,
            text="Notificaciones",
            command=self.notification_manager.show_notification_center,
            style="Secondary.TButton",
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        self.content_frame = ttk.Frame(content_shell, padding=(24, 14, 24, 24), style="App.TFrame")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.content_frame.rowconfigure(0, weight=1)
        self.content_frame.columnconfigure(0, weight=1)

        self._build_sidebar()

        def check_stock_periodically():
            self.notification_manager.check_stock_alerts()
            self.after(300000, check_stock_periodically)

        check_stock_periodically()
        self.notification_manager.notify_system_info("v1.1.0")
        self._on_nav_click("Dashboard")

    def _build_sidebar(self):
        ttk.Label(self.nav_frame, text="TECH SISTEMS ERP", style="SidebarTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(4, 2)
        )
        ttk.Label(self.nav_frame, text=f"Usuario: {self.current_user[1]}", style="SidebarText.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Label(self.nav_frame, text=f"Rol: {self.current_user[2]}", style="SidebarText.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 14)
        )

        separator = tk.Frame(self.nav_frame, height=1, bg="#1E3358")
        separator.grid(row=3, column=0, sticky="ew", pady=(4, 12))

        class NotificationsFrame(ttk.Frame):
            def __init__(self, parent, app):
                super().__init__(parent)
                ttk.Label(self, text="Centro de Notificaciones", style="Subheader.TLabel").pack(pady=20)

        self.frames = {
            "Dashboard": DashboardFrame,
            "Ventas (POS)": UnifiedPOSFrame,
            "Registro de Ventas": RegistroVentasFrame,
            "Clientes": ClientsFrame,
            "Productos": ProductFrame,
            "Proveedores": SupplierFrame,
            "Configuración": ConfigFrame,
            "Notificaciones": NotificationsFrame,
        }

        nav_order = [
            "Dashboard",
            "Ventas (POS)",
            "Registro de Ventas",
            "Clientes",
            "Productos",
            "Proveedores",
            "Configuración",
        ]

        nav_host = ttk.Frame(self.nav_frame, style="Sidebar.TFrame")
        nav_host.grid(row=4, column=0, sticky="nsew")
        nav_host.columnconfigure(0, weight=1)
        self.nav_frame.rowconfigure(4, weight=1)

        for idx, section in enumerate(nav_order):
            button = ttk.Button(
                nav_host,
                text=section,
                style="Nav.TButton",
                command=lambda value=section: self._on_nav_click(value),
            )
            button.grid(row=idx, column=0, sticky="ew", pady=4)
            self.nav_widgets[section] = button

        bottom = ttk.Frame(self.nav_frame, style="Sidebar.TFrame")
        bottom.grid(row=5, column=0, sticky="ew", pady=(14, 10))
        ttk.Button(bottom, text="Cerrar sesion", command=self.logout, style="Danger.TButton").pack(fill="x")

    def _on_nav_click(self, title):
        frame_class = self.frames[title]
        self.current_section.set(title)
        self._set_active_nav(title)
        self.show_frame(frame_class, title)

    def _set_active_nav(self, selected_title):
        for title, widget in self.nav_widgets.items():
            widget.configure(style="NavAccent.TButton" if title == selected_title else "Nav.TButton")

    def show_frame(self, frame_class, title):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        frame = frame_class(self.content_frame, self)
        frame.grid(row=0, column=0, sticky="nsew")

    def logout(self):
        if messagebox.askyesno("Cerrar sesion", "Desea cerrar sesion?", parent=self):
            self.container.destroy()
            self.current_user = None
            self.nav_widgets.clear()
            self.show_login()

    def on_closing(self):
        if messagebox.askokcancel("Salir", "Desea salir del sistema?", parent=self):
            self.db.close()
            self.destroy()


def main():
    app = ERPApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
