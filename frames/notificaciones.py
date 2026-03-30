# -*- coding: utf-8 -*-
"""
notificaciones.py
Sistema de notificaciones push avanzado para ERP....
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from tkinter import messagebox
from .ui import format_hnl

class NotificationManager:
    def __init__(self, root, db_manager):
        self.root = root
        self.db = db_manager
        self.notification_widgets = []
        self.notification_history = []
        self.notification_queue = []
        self.is_animating = False
        self.max_notifications = 5
        self.notification_duration = 5000
        self.config = {
            'stock_alerts': True,
            'sales_alerts': True,
            'login_alerts': True,
            'system_alerts': True,
            'sound_enabled': False
        }

    # ---------------- Métodos de notificación ----------------
    def show_notification(self, title, message, type="info", duration=None, action_callback=None, action_data=None):
        duration = duration or self.notification_duration
        data = {
            'title': title,
            'message': message,
            'type': type,
            'timestamp': datetime.now(),
            'action_callback': action_callback,
            'action_data': action_data
        }
        self.notification_history.insert(0, data)
        if len(self.notification_history) > 100:
            self.notification_history.pop()
        self.notification_queue.append((data, duration))
        if not self.is_animating:
            self.show_next_notification()

    def show_next_notification(self):
        if not self.notification_queue:
            self.is_animating = False
            return
        self.is_animating = True
        data, duration = self.notification_queue.pop(0)
        notification = NotificationWidget(self.root, data, duration, self.on_notification_close)
        self.notification_widgets.append(notification)
        self.reposition_notifications()
        self.root.after(duration + 300, lambda: self.finish_notification(notification))

    def finish_notification(self, notification):
        self.close_notification(notification)
        self.is_animating = False
        self.root.after(150, self.show_next_notification)

    def close_notification(self, notification):
        if notification in self.notification_widgets:
            notification.close()
            self.notification_widgets.remove(notification)
            self.reposition_notifications()

    def on_notification_close(self, notification):
        if notification in self.notification_widgets:
            self.notification_widgets.remove(notification)
            self.reposition_notifications()

    def reposition_notifications(self):
        screen_width = self.root.winfo_screenwidth()
        y_offset = 80
        spacing = 10
        y_pos = y_offset
        for widget in self.notification_widgets:
            target_x = screen_width - widget.width - 20
            target_y = y_pos
            widget.animate_to(target_x, target_y)
            y_pos += widget.height + spacing

    # ---------------- Notificaciones específicas ----------------
    def check_stock_alerts(self):
        if not self.config['stock_alerts']:
            return
        low_stock_items = self.db.fetch("SELECT nombre, stock FROM Productos WHERE stock <= 10")
        for nombre, stock in low_stock_items:
            self.show_notification(
                "⚠ Stock Bajo",
                f"Producto: {nombre}\nCantidad: {stock}",
                type="warning",
                duration=5000,
                action_callback=self.open_low_stock_product,
                action_data=nombre
            )

    def open_low_stock_product(self, product_name):
        messagebox.showinfo(
            "Producto con Stock Bajo",
            f"El producto '{product_name}' tiene stock bajo. Por favor, actualízalo o realiza pedido."
        )
        # Abrir frame de productos si tu ERP tiene method show_frame
        if hasattr(self.root, 'show_frame'):
            self.root.show_frame(self.root.frames['Productos'], "Productos")

    def notify_login(self, username, role):
        if self.config['login_alerts']:
            self.show_notification(
                "✓ Sesión Iniciada",
                f"Bienvenido {username}\nRol: {role}\n{datetime.now().strftime('%d/%m/%Y %H:%M')}",
                type="success",
                duration=4000
            )

    def notify_sale_success(self, venta_id, total):
        if self.config['sales_alerts']:
            self.show_notification(
                "✓ Venta Exitosa",
                f"Venta: {venta_id}\nTotal: {format_hnl(total)}\n{datetime.now().strftime('%H:%M:%S')}",
                type="success",
                duration=4000
            )

    def notify_sale_cancelled(self):
        if self.config['sales_alerts']:
            self.show_notification(
                "✕ Venta Cancelada",
                f"La venta fue cancelada\n{datetime.now().strftime('%H:%M:%S')}",
                type="warning",
                duration=3000
            )

    def notify_system_info(self, app_version):
        if self.config['system_alerts']:
            self.show_notification(
                "🚀 Sistema ERP Iniciado",
                f"Versión: {app_version}\nSistema listo para usar\n{datetime.now().strftime('%d/%m/%Y %H:%M')}",
                type="info",
                duration=5000
            )

    def show_notification_center(self):
        NotificationCenter(self.root, self)

# ---------------- Widget de notificación ----------------

class NotificationWidget:
    """Widget individual de notificación con animación."""

    def __init__(self, parent, data, duration, close_callback):
        self.parent = parent
        self.data = data
        self.duration = duration
        self.close_callback = close_callback

        self.width = 350
        self.height = 100

        self.colors = {
            'info': {'bg': '#3498db', 'fg': 'white'},
            'success': {'bg': '#27ae60', 'fg': 'white'},
            'warning': {'bg': '#f39c12', 'fg': 'white'},
            'error': {'bg': '#e74c3c', 'fg': 'white'}
        }

        color_scheme = self.colors.get(data['type'], self.colors['info'])

        # Ventana Toplevel
        self.window = tk.Toplevel(parent)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        try:
            self.window.attributes('-alpha', 0.95)
        except:
            pass

        # Posición inicial fuera de pantalla
        # Posición inicial alineada a la derecha, fuera del borde superior
        screen_width = parent.winfo_screenwidth()
        self.current_x = screen_width - self.width - 20
        self.current_y = -self.height  # empieza arriba, fuera de la pantalla
        self.window.geometry(f'{self.width}x{self.height}+{int(self.current_x)}+{int(self.current_y)}')


        # Frame principal
        main_frame = tk.Frame(self.window, bg=color_scheme['bg'], relief='raised', borderwidth=2)
        main_frame.pack(fill='both', expand=True)

        # Título y cerrar
        top_frame = tk.Frame(main_frame, bg=color_scheme['bg'])
        top_frame.pack(fill='x', padx=10, pady=(10, 5))

        tk.Label(top_frame, text=data['title'], font=('Arial', 11, 'bold'),
                 fg=color_scheme['fg'], bg=color_scheme['bg'], anchor='w').pack(side='left', fill='x', expand=True)

        close_btn = tk.Label(top_frame, text='✕', font=('Arial', 14, 'bold'),
                             fg=color_scheme['fg'], bg=color_scheme['bg'], cursor='hand2')
        close_btn.pack(side='right')
        close_btn.bind('<Button-1>', lambda e: self.close())

        # Mensaje
        tk.Label(main_frame, text=data['message'], font=('Arial', 9),
                 fg=color_scheme['fg'], bg=color_scheme['bg'], anchor='w', justify='left', wraplength=320
                 ).pack(fill='both', expand=True, padx=10, pady=5)

        # Timestamp
        tk.Label(main_frame, text=data['timestamp'].strftime('%H:%M:%S'), font=('Arial', 8),
                 fg=color_scheme['fg'], bg=color_scheme['bg'], anchor='e').pack(fill='x', padx=10, pady=(0, 10))

       # Barra de progreso
        self.progress_bar = tk.Canvas(main_frame, height=3, bg=color_scheme['bg'], highlightthickness=0)
        self.progress_bar.pack(fill='x', side='bottom')

        if callable(data.get('action_callback')):
            self.window.bind('<Button-1>', self.on_click)
            self.window.config(cursor='hand2')

        self.animate_in()
        self.start_progress()


    # ---------------- Animaciones ----------------

    def animate_in(self):
       screen_width = self.parent.winfo_screenwidth()
       target_x = screen_width - self.width - 20
       # El target_y lo va a manejar el NotificationManager según la pila
       target_y = self.current_y
       self.animate_to(target_x, target_y)


    def animate_to(self, target_x, target_y):
        steps = 25
        delay = 20
        dx = (target_x - self.current_x) / steps
        dy = (target_y - self.current_y) / steps

        def step(count=0):
            if count < steps:
                self.current_x += dx
                self.current_y += dy
                self.window.geometry(f'{self.width}x{self.height}+{int(self.current_x)}+{int(self.current_y)}')
                self.window.after(delay, lambda: step(count + 1))
            else:
                self.current_x = target_x
                self.current_y = target_y

        step()

    def start_progress(self):
        self.progress_width = 0
        self.progress_step = self.width / (self.duration / 50)
        self.update_progress()

    def update_progress(self):
        if self.progress_width < self.width:
            self.progress_bar.delete('all')
            self.progress_bar.create_rectangle(0, 0, self.progress_width, 3, fill='white', outline='')
            self.progress_width += self.progress_step
            self.window.after(50, self.update_progress)

    def on_click(self, event=None):
        callback = self.data.get('action_callback')
        action_data = self.data.get('action_data')
        if callback:
            callback(action_data) if action_data else callback()
        self.close()

    def close(self):
        screen_width = self.parent.winfo_screenwidth()
        target_y = self.parent.winfo_screenheight() + self.height
        target_x = self.current_x  # mantener la misma X
        steps = 25
        delay = 20
        dx = (target_x - self.current_x) / steps

        def step(count=0):
            if count < steps:
                self.current_x += dx
                try:
                    self.window.geometry(f'{self.width}x{self.height}+{int(self.current_x)}+{int(self.current_y)}')
                except:
                    pass
                self.window.after(delay, lambda: step(count + 1))
            else:
                try:
                    self.window.destroy()
                except:
                    pass
                self.close_callback(self)

        step()


# ---------------- Centro de Notificaciones ----------------

class NotificationCenter(tk.Toplevel):
    """Ventana con historial y configuración de notificaciones."""

    def __init__(self, parent, manager: NotificationManager):
        super().__init__(parent)
        self.manager = manager
        self.title("Centro de Notificaciones")
        self.geometry("600x500")

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill='both', expand=True)

        ttk.Label(main_frame, text="🔔 Centro de Notificaciones", font=('Arial', 16, 'bold')).pack(pady=(0, 10))
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)

        # Historial
        history_tab = ttk.Frame(notebook, padding=10)
        notebook.add(history_tab, text="Historial")
        self.create_history_tab(history_tab)

        # Configuración
        config_tab = ttk.Frame(notebook, padding=10)
        notebook.add(config_tab, text="Configuración")
        self.create_config_tab(config_tab)

        # Botones inferiores
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(10, 0))
        ttk.Button(btn_frame, text="Limpiar Historial", command=self.clear_history).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=self.destroy).pack(side='right', padx=5)

    # ---------------- Funciones internas ----------------

    def create_history_tab(self, parent):
        canvas = tk.Canvas(parent, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for notif in self.manager.notification_history:
            self.create_history_item(scrollable_frame, notif)

    def create_history_item(self, parent, notif):
        colors = {'info': '#3498db','success': '#27ae60','warning': '#f39c12','error': '#e74c3c'}
        color = colors.get(notif['type'], '#3498db')

        item_frame = tk.Frame(parent, bg='white', relief='raised', borderwidth=1)
        item_frame.pack(fill='x', padx=5, pady=5)
        item_frame.bind("<Button-1>", lambda e, n=notif: self.manager.handle_notification_click(n))
        item_frame.config(cursor="hand2")
        tk.Label(item_frame, bg=color, width=1).pack(side='left', fill='y')

        content_frame = tk.Frame(item_frame, bg='white')
        content_frame.pack(side='left', fill='both', expand=True, padx=10, pady=8)
        tk.Label(content_frame, text=notif['title'], font=('Arial', 10, 'bold'), bg='white', anchor='w').pack(fill='x')
        tk.Label(content_frame, text=notif['message'], font=('Arial', 9), bg='white', anchor='w', justify='left').pack(fill='x', pady=(3,0))
        tk.Label(content_frame, text=notif['timestamp'].strftime('%d/%m/%Y %H:%M:%S'), font=('Arial',8), fg='#666', bg='white', anchor='e').pack(fill='x', pady=(3,0))
        

    def create_config_tab(self, parent):
        ttk.Label(parent, text="Configuración de Notificaciones", font=('Arial', 12, 'bold')).pack(pady=(0,10))
        config_frame = ttk.LabelFrame(parent, text="Tipos de Notificaciones", padding=10)
        config_frame.pack(fill='both', expand=True)

        self.stock_var = tk.BooleanVar(value=self.manager.config['stock_alerts'])
        self.sales_var = tk.BooleanVar(value=self.manager.config['sales_alerts'])
        self.login_var = tk.BooleanVar(value=self.manager.config['login_alerts'])
        self.system_var = tk.BooleanVar(value=self.manager.config['system_alerts'])

        ttk.Checkbutton(config_frame, text="Alertas de Stock Bajo", variable=self.stock_var, command=self.save_config).pack(anchor='w', pady=3)
        ttk.Checkbutton(config_frame, text="Notificaciones de Ventas", variable=self.sales_var, command=self.save_config).pack(anchor='w', pady=3)
        ttk.Checkbutton(config_frame, text="Notificaciones de Inicio de Sesión", variable=self.login_var, command=self.save_config).pack(anchor='w', pady=3)
        ttk.Checkbutton(config_frame, text="Notificaciones del Sistema", variable=self.system_var, command=self.save_config).pack(anchor='w', pady=3)

        ttk.Button(config_frame, text="Probar Notificación", command=self.test_notification).pack(pady=10)

    def save_config(self):
        self.manager.config['stock_alerts'] = self.stock_var.get()
        self.manager.config['sales_alerts'] = self.sales_var.get()
        self.manager.config['login_alerts'] = self.login_var.get()
        self.manager.config['system_alerts'] = self.system_var.get()

    def test_notification(self):
        self.manager.show_notification("🧪 Notificación de prueba","Esta es una notificación de prueba", type="info", duration=4000)

    def clear_history(self):
        from tkinter import messagebox
        if messagebox.askyesno("Confirmar", "¿Desea limpiar todo el historial de notificaciones?"):
            self.manager.notification_history.clear()
            self.destroy()
            NotificationCenter(self.master, self.manager)
