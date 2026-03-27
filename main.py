"""
main.py
Punto de entrada de la aplicación ERP fusionado
"""

import tkinter as tk
from tkinter import ttk, messagebox
from database import DBManager
from file_manager import FileManager
from frames import (
    DashboardFrame,
    ProductFrame,
    SupplierFrame,
    ConfigFrame,
    SalesFrame,
    ClientsFrame,
    RegistroVentasFrame,
)
# 🔔 Importar notificaciones
from frames.notificaciones import NotificationManager


class ERPApp(tk.Tk):
    """Aplicación principal del sistema ERP."""
    

    def __init__(self):
        super().__init__()

        self.title("Sistema ERP Profesional")
        self.geometry("1400x900")
        self.configure(bg="#f0f0f0")

        # Inicializar base de datos y gestor de archivos
        self.db = DBManager()
        self.file_manager = FileManager(self.db)

        # Inicializar notificaciones
        self.notification_manager = NotificationManager(self, self.db)

        # Usuario actual
        self.current_user = None

        # Configurar estilo
        self.configure_styles()

        # Mostrar login
        self.show_login()

    def configure_styles(self):
        """Configura los estilos visuales de la aplicación."""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure("TFrame", background="#f4f7f6")
        self.style.configure("TLabel", background="#f4f7f6", font=("Arial", 11))
        self.style.configure(
            "TButton",
            font=("Arial", 10, "bold"),
            padding=10,
            relief="flat",
            background="#3e5973",
            foreground="white",
        )
        self.style.map("TButton", background=[("active", "#2e4153")])

        self.style.configure("Accent.TButton", background="#ff6e40", foreground="white")
        self.style.map("Accent.TButton", background=[("active", "#e65100")])

        self.style.configure("Header.TLabel", font=("Arial", 18, "bold"), foreground="#1e3d59")
        self.style.configure("Card.TFrame", background="white", relief="raised", borderwidth=1)

    def show_login(self):
        """Muestra la pantalla de login."""
        self.login_frame = ttk.Frame(self, padding="40")
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

        login_container = ttk.Frame(self.login_frame, padding="30", relief="groove")
        login_container.pack()

        ttk.Label(login_container, text="SISTEMA ERP", font=("Arial", 20, "bold"), foreground="#1e3d59")\
            .grid(row=0, column=0, columnspan=2, pady=(0, 20))
        ttk.Label(login_container, text="Inicio de Sesión", font=("Arial", 14))\
            .grid(row=1, column=0, columnspan=2, pady=(0, 20))

        ttk.Label(login_container, text="Usuario:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.username_entry = ttk.Entry(login_container, width=25)
        self.username_entry.grid(row=2, column=1, padx=10, pady=10)
        self.username_entry.insert(0, "admin")

        ttk.Label(login_container, text="Contraseña:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.password_entry = ttk.Entry(login_container, show="*", width=25)
        self.password_entry.grid(row=3, column=1, padx=10, pady=10)
        self.password_entry.insert(0, "1234")

        ttk.Button(login_container, text="Acceder", command=self.authenticate, style="Accent.TButton")\
            .grid(row=4, column=0, columnspan=2, pady=20, sticky="ew")

        self.password_entry.bind("<Return>", lambda e: self.authenticate())

    def authenticate(self):
        """Autentica al usuario."""
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
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")

    def show_main_interface(self):
        """Muestra la interfaz principal después del login."""
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        nav_frame = ttk.Frame(self.container, width=220, padding="15", relief="flat")
        nav_frame.pack(side="left", fill="y")
        nav_frame.pack_propagate(False)

        ttk.Label(nav_frame, text="ERP Sistema", font=("Arial", 18, "bold"), foreground="#ff6e40")\
            .pack(pady=(0, 10))
        ttk.Label(nav_frame, text=f"Usuario: {self.current_user[1]}", font=("Arial", 9), foreground="#666")\
            .pack(pady=(0, 5))
        ttk.Label(nav_frame, text=f"Rol: {self.current_user[2]}", font=("Arial", 9), foreground="#666")\
            .pack(pady=(0, 25))

        ttk.Separator(nav_frame, orient="horizontal").pack(fill="x", pady=10)

        self.content_frame = ttk.Frame(self.container, padding="20")
        self.content_frame.pack(side="right", fill="both", expand=True)

        

        # 🔔 Botón de Notificaciones independiente
        ttk.Button(nav_frame, text="🔔 Notificaciones",
                   command=self.notification_manager.show_notification_center).pack(fill="x", pady=5)

        # Frame de Notificaciones interno
        class NotificationsFrame(ttk.Frame):
            def __init__(self, parent, app):
                super().__init__(parent)
                ttk.Label(self, text="Centro de Notificaciones 🔔", font=("Arial", 14, "bold")).pack(pady=20)


        # Diccionario de frames
        self.frames = {
            "Dashboard": DashboardFrame,
            "Ventas (POS)": CompuertaFrame,
            "Registro de Ventas": RegistroVentasFrame,
            "Clientes": ClientsFrame,
            "Productos": ProductFrame,
            "Proveedores": SupplierFrame,
            "Configuración": ConfigFrame,
            "Notificaciones": NotificationsFrame
        }

        # Botones de navegación
        nav_buttons = [
            ("Dashboard", "Dashboard"),
            ("Ventas (POS)", "Ventas (POS)"),
            ("Registro de Ventas", "Registro de Ventas"),
            ("Clientes", "Clientes"),
            ("Productos", "Productos"),
            ("Proveedores", "Proveedores"),
            ("Configuración", "Configuración")
        ]

        for title, frame_name in nav_buttons:
            is_accent = "Ventas" in title
            btn = ttk.Button(
                nav_frame,
                text=title,
                command=lambda f=self.frames[frame_name], t=title: self.show_frame(f, t),
                style="Accent.TButton" if is_accent else "TButton"
            )
            btn.pack(fill="x", pady=5)

        ttk.Separator(nav_frame, orient="horizontal").pack(fill="x", pady=20)
        ttk.Button(nav_frame, text="Cerrar Sesión", command=self.logout).pack(side="bottom", fill="x", pady=10)

        self.show_frame(DashboardFrame, "Dashboard")

        # ⚙️ Verificar stock cada 5 minutos
        def check_stock_periodically():
            self.notification_manager.check_stock_alerts()
            self.after(300000, check_stock_periodically)

        check_stock_periodically()
        self.notification_manager.notify_system_info("v1.0.0")

    def show_frame(self, FrameClass, title):
        """Muestra el frame solicitado."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.content_frame, text=title, style="Header.TLabel").pack(fill="x", pady=(0, 20))
        frame = FrameClass(self.content_frame, self)
        frame.pack(fill="both", expand=True)

    def logout(self):
        """Cierra sesión y vuelve al login."""
        if messagebox.askyesno("Cerrar Sesión", "¿Desea cerrar sesión?"):
            self.container.destroy()
            self.current_user = None
            self.show_login()

    def on_closing(self):
        """Maneja el cierre de la aplicación."""
        if messagebox.askokcancel("Salir", "¿Desea salir del sistema?"):
            self.db.close()
            self.destroy()
class CompuertaFrame(ttk.Frame):
    """Frame para decidir tipo de venta: Normal o Especial."""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        container = ttk.Frame(self, padding=40, style='Card.TFrame')
        container.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(container, text="🧾 Tipo de Venta", style='Header.TLabel').pack(pady=(0, 20))
        ttk.Label(container, text="Seleccione el tipo de venta que desea realizar:", font=('Arial', 11)).pack(pady=(0, 15))

        # Botones
        ttk.Button(container, text="🛒 Venta Normal", style='Accent.TButton',
                   command=self.open_normal_sale).pack(fill="x", pady=10)
        ttk.Button(container, text="💼 Venta Especial", style='Accent.TButton',
                   command=self.open_special_sale).pack(fill="x", pady=10)

    def open_normal_sale(self):
        from frames.sales import SalesFrame  # import dinámico
        self.app.show_frame(SalesFrame, "Venta Normal 🛒")

    def open_special_sale(self):
        from frames.sales_may import WholesaleSalesFrame  # import dinámico
        self.app.show_frame(WholesaleSalesFrame, "Venta Especial 💼")



def main():
    """Función principal."""
    app = ERPApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
