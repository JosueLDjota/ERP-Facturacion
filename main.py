"""
main.py
Punto de entrada de la aplicación ERP.
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
    """Aplicación principal del sistema ERP."""

    def __init__(self):
        super().__init__()

        self.title("TECH SISTEMS ERP")
        self.geometry("1400x900")
        self.minsize(1200, 760)
        self.base_dir = Path(__file__).resolve().parent

        self.db = DBManager()
        self.file_manager = FileManager(self.db)
        self.notification_manager = NotificationManager(self, self.db)
        self.current_user = None

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
        self.login_frame = ttk.Frame(self, padding=40, style="App.TFrame")
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

        login_container = ttk.LabelFrame(
            self.login_frame,
            text="Acceso al sistema",
            padding=28,
            style="Card.TLabelframe",
        )
        login_container.pack()
        login_container.columnconfigure(1, weight=1)

        ttk.Label(login_container, text="TECH SISTEMS ERP", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 18)
        )
        ttk.Label(login_container, text="Inicio de sesión", style="Subheader.TLabel").grid(
            row=1, column=0, columnspan=2, pady=(0, 18)
        )

        ttk.Label(login_container, text="Usuario:", style="FormLabel.TLabel").grid(
            row=2, column=0, padx=10, pady=10, sticky="w"
        )
        self.username_entry = ttk.Entry(login_container, width=28)
        self.username_entry.grid(row=2, column=1, padx=10, pady=10)
        self.username_entry.insert(0, "admin")

        ttk.Label(login_container, text="Contraseña:", style="FormLabel.TLabel").grid(
            row=3, column=0, padx=10, pady=10, sticky="w"
        )
        self.password_entry = ttk.Entry(login_container, show="*", width=28)
        self.password_entry.grid(row=3, column=1, padx=10, pady=10)
        self.password_entry.insert(0, "1234")

        ttk.Button(
            login_container,
            text="Acceder",
            style="Primary.TButton",
            command=self.authenticate,
        ).grid(row=4, column=0, columnspan=2, pady=20, sticky="ew")

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

        messagebox.showerror("Error", "Usuario o contraseña incorrectos", parent=self)

    def show_main_interface(self):
        self.container = ttk.Frame(self, style="App.TFrame")
        self.container.pack(fill="both", expand=True)

        nav_frame = ttk.Frame(self.container, width=250, padding=18, style="Surface.TFrame")
        nav_frame.pack(side="left", fill="y")
        nav_frame.pack_propagate(False)

        ttk.Label(nav_frame, text="TECH SISTEMS ERP", style="Subheader.TLabel").pack(
            pady=(0, 10), anchor="w"
        )
        ttk.Label(nav_frame, text=f"Usuario: {self.current_user[1]}", style="Muted.TLabel").pack(
            pady=(0, 5), anchor="w"
        )
        ttk.Label(nav_frame, text=f"Rol: {self.current_user[2]}", style="Muted.TLabel").pack(
            pady=(0, 24), anchor="w"
        )
        ttk.Separator(nav_frame, orient="horizontal").pack(fill="x", pady=10)

        self.content_frame = ttk.Frame(self.container, padding=20, style="App.TFrame")
        self.content_frame.pack(side="right", fill="both", expand=True)

        ttk.Button(
            nav_frame,
            text="Notificaciones",
            command=self.notification_manager.show_notification_center,
            style="Secondary.TButton",
        ).pack(fill="x", pady=5)

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

        nav_buttons = [
            ("Dashboard", "Dashboard"),
            ("Ventas (POS)", "Ventas (POS)"),
            ("Registro de Ventas", "Registro de Ventas"),
            ("Clientes", "Clientes"),
            ("Productos", "Productos"),
            ("Proveedores", "Proveedores"),
            ("Configuración", "Configuración"),
        ]

        for title, frame_name in nav_buttons:
            is_primary = "Ventas" in title
            ttk.Button(
                nav_frame,
                text=title,
                command=lambda f=self.frames[frame_name], t=title: self.show_frame(f, t),
                style="NavAccent.TButton" if is_primary else "Nav.TButton",
            ).pack(fill="x", pady=5)

        ttk.Separator(nav_frame, orient="horizontal").pack(fill="x", pady=20)
        ttk.Button(nav_frame, text="Cerrar sesión", command=self.logout, style="Danger.TButton").pack(
            side="bottom", fill="x", pady=10
        )

        self.show_frame(DashboardFrame, "Dashboard")

        def check_stock_periodically():
            self.notification_manager.check_stock_alerts()
            self.after(300000, check_stock_periodically)

        check_stock_periodically()
        self.notification_manager.notify_system_info("v1.1.0")

    def show_frame(self, frame_class, title):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.content_frame, text=title, style="Header.TLabel").pack(fill="x", pady=(0, 20))
        frame = frame_class(self.content_frame, self)
        frame.pack(fill="both", expand=True)

    def logout(self):
        if messagebox.askyesno("Cerrar sesión", "¿Desea cerrar sesión?", parent=self):
            self.container.destroy()
            self.current_user = None
            self.show_login()

    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Desea salir del sistema?", parent=self):
            self.db.close()
            self.destroy()


def main():
    app = ERPApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
