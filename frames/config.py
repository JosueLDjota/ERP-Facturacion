"""
frames/config.py
Configuracion del sistema, descuentos y plantilla de recibos.
"""

import tempfile
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from erp.data.repositories.config_repository import ConfigRepository, RepositoryError
from erp.ui.backup_panel import BackupSettingsPanel
from erp.ui.shared import PALETTE, get_available_themes
from frames.taxonomy import CatalogTaxonomyFrame
from receipt_builder import (
    build_receipt_html,
    build_receipt_view_model,
    load_receipt_render_settings,
)


class ConfigFrame(ttk.Frame):
    """Frame de configuracion del sistema."""

    HELP_TEXTS = {
        "main": (
            "Desde Configuración puedes administrar descuentos, abrir la gestión de "
            "categorías y marcas, editar la plantilla activa del recibo y personalizar "
            "la apariencia visual del sistema."
        ),
        "taxonomy": (
            "Aquí organizas el catálogo por categorías y marcas. Estos datos ayudan a "
            "clasificar productos, mejorar búsquedas y mantener el inventario ordenado."
        ),
        "receipt": (
            "Aquí editas la plantilla activa del recibo. Los cambios que guardes se "
            "reflejan en Ventas, vista previa, impresión y reimpresión."
        ),
        "personalization": (
            "Esta sección controla la apariencia visual global del ERP. El tema se aplica "
            "en tiempo real a ventanas, formularios, botones, tablas y módulos emergentes."
        ),
        "appearance_preview": (
            "Apariencia general es solo una vista de ejemplo del tema activo. Sirve para "
            "mostrar cómo se verán textos, campos y botones. No guarda contenido ni es un "
            "formulario funcional."
        ),
    }

    def __init__(self, parent, app):
        super().__init__(parent, padding=10, style="App.TFrame")
        self.app = app
        self.db = app.db
        self.repository = ConfigRepository(self.db)
        
        # Referencias a ventanas emergentes (para evitar duplicados)
        self._taxonomy_window = None
        self._receipt_window = None
        self._personalization_window = None
        self._help_window = None

        # Variables de descuentos
        self.disc_id = tk.StringVar(value="")
        self.disc_nombre = tk.StringVar()
        self.disc_porcentaje = tk.StringVar()
        self.disc_tipo = tk.StringVar(value="Docena")
        
        # Variables de empresa
        self.company_name_var = tk.StringVar()
        self.company_rtn_var = tk.StringVar()
        self.company_tel_var = tk.StringVar()
        self.company_email_var = tk.StringVar()
        self.company_logo_var = tk.StringVar()
        self.theme_var = tk.StringVar(value=getattr(self.app, "current_theme", "light"))
        self._last_preview_path = None

        self._build_ui()
        self.load_discounts()

    def _parent(self):
        """Retorna la ventana padre para los diálogos."""
        return self.winfo_toplevel()

    def _show_help_window(self, key, owner=None):
        """Muestra una ventana pequeña de ayuda sobre la pantalla actual."""
        parent_window = owner if owner is not None else self._parent()
        if self._help_window is not None and self._help_window.winfo_exists():
            self._help_window.destroy()

        self._help_window = tk.Toplevel(parent_window)
        self._help_window.title("Ayuda rápida")
        self._help_window.transient(parent_window)
        self._help_window.resizable(False, False)
        self._help_window.configure(bg=PALETTE["blue_soft"])
        self._help_window.grab_set()

        shell = ttk.Frame(self._help_window, padding=18, style="App.TFrame")
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)

        header = ttk.Frame(shell, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="? Ayuda", style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(
            header,
            text="Cerrar",
            style="Secondary.TButton",
            command=self._help_window.destroy,
        ).grid(row=0, column=1, sticky="e")

        warning_card = ttk.LabelFrame(shell, text="Información", style="Card.TLabelframe")
        warning_card.grid(row=1, column=0, sticky="nsew")
        warning_card.columnconfigure(0, weight=1)

        ttk.Label(
            warning_card,
            text=self.HELP_TEXTS.get(key, "No hay ayuda disponible para esta sección."),
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=12)

        self._help_window.update_idletasks()
        width = 470
        height = 220
        parent_window.update_idletasks()
        x = parent_window.winfo_rootx() + max(0, (parent_window.winfo_width() - width) // 2)
        y = parent_window.winfo_rooty() + 90
        self._help_window.geometry(f"{width}x{height}+{x}+{y}")
        self._help_window.lift()
        self._help_window.focus_force()

    def _create_help_button(self, parent, help_key, column, *, owner=None, row=0, padx=(8, 0), pady=0):
        """Crea un botón pequeño de ayuda contextual."""
        ttk.Button(
            parent,
            text="?",
            width=3,
            style="Secondary.TButton",
            command=lambda: self._show_help_window(help_key, owner() if callable(owner) else owner),
        ).grid(row=row, column=column, sticky="e", padx=padx, pady=pady)

    def _build_ui(self):
        """Construye la interfaz de usuario."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Header con título y botones de acceso rápido
        header_frame = ttk.Frame(self, style="App.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.columnconfigure(0, weight=1)

        self._create_help_button(header_frame, "main", 1, owner=self._parent, row=0)

        # Botones de acceso rápido a ventanas emergentes
        buttons_frame = ttk.Frame(header_frame, style="App.TFrame")
        buttons_frame.grid(row=0, column=0, sticky="w")
        
        ttk.Button(
            buttons_frame,
            text="🏷️ Abrir Categorías y Marcas",
            style="Primary.TButton",
            command=self.open_taxonomy_window
        ).pack(side="left", padx=5)
        
        ttk.Button(
            buttons_frame,
            text="🧾 Abrir Plantilla de recibo",
            style="Primary.TButton",
            command=self.open_receipt_window
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons_frame,
            text="🎨 Personalización",
            style="Secondary.TButton",
            command=self.open_personalization_window
        ).pack(side="left", padx=5)

        # Notebook con UNA SOLA pestaña: Descuentos
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        disc_tab = ttk.Frame(self.notebook, padding=12, style="App.TFrame")
        self.notebook.add(disc_tab, text="💰 Descuentos")
        
        self.create_discount_tab(disc_tab)

        backup_tab = ttk.Frame(self.notebook, padding=12, style="App.TFrame")
        self.notebook.add(backup_tab, text="Respaldos")
        self.backup_panel = BackupSettingsPanel(backup_tab, self.app, self.app.backup_service)
        self.backup_panel.grid(row=0, column=0, sticky="nsew")
        backup_tab.columnconfigure(0, weight=1)
        backup_tab.rowconfigure(0, weight=1)

    # ========================================================================
    # VENTANAS EMERGENTES COMPLETAS
    # ========================================================================
    
    def open_taxonomy_window(self):
        """Abre Categorías y Marcas en una ventana independiente con TODO el contenido visible."""
        # Verificar si ya existe y traer al frente
        if self._taxonomy_window is not None and self._taxonomy_window.winfo_exists():
            self._taxonomy_window.lift()
            self._taxonomy_window.focus_force()
            return
        
        # Crear nueva ventana
        self._taxonomy_window = tk.Toplevel(self._parent())
        self._taxonomy_window.title("Gestión de Categorías y Marcas - TECH SYSTEMS ERP")
        
        # Configurar ventana maximizada (no fullscreen)
        self._taxonomy_window.state("zoomed")
        self._taxonomy_window.minsize(1000, 700)
        
        # Configurar cierre
        self._taxonomy_window.protocol("WM_DELETE_WINDOW", self._on_taxonomy_window_close)
        
        # Configurar estilo de la ventana
        self._taxonomy_window.configure(bg=PALETTE["blue_soft"])
        
        # Frame principal con padding
        main_frame = ttk.Frame(self._taxonomy_window, padding=20, style="App.TFrame")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header con título y botón cerrar
        header = ttk.Frame(main_frame, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header.columnconfigure(0, weight=1)
        
        ttk.Label(header, text="📦 Gestión de Categorías y Marcas", 
                 style="Subheader.TLabel", font=('Segoe UI', 18, 'bold')).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Organiza tus productos por categorías y marcas para una mejor gestión de inventario",
            style="Muted.TLabel",
            font=('Segoe UI', 11)
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        ttk.Button(
            header,
            text="✕ Cerrar",
            style="Danger.TButton",
            command=self._on_taxonomy_window_close
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))
        self._create_help_button(header, "taxonomy", 2, owner=lambda: self._taxonomy_window, row=0, padx=(8, 0))

        # Frame contenedor con scroll para TODO el contenido (sin pestañas internas)
        canvas_container = ttk.Frame(main_frame, style="App.TFrame")
        canvas_container.grid(row=1, column=0, sticky="nsew")
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.rowconfigure(0, weight=1)
        
        canvas = tk.Canvas(canvas_container, highlightthickness=0, bg=PALETTE["blue_soft"])
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="App.TFrame")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(1, width=e.width))
        
        # Contenido: CatalogTaxonomyFrame COMPLETO (sin cortes)
        content_frame = ttk.Frame(scrollable_frame, padding=10)
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1)
        
        taxonomy_frame = CatalogTaxonomyFrame(content_frame, self.app)
        taxonomy_frame.grid(row=0, column=0, sticky="nsew")
        
        # Guardar referencias para limpiar bindings al cerrar
        self._taxonomy_window._mousewheel_binding = _on_mousewheel
        self._taxonomy_window._canvas = canvas
    
    def _on_taxonomy_window_close(self):
        """Cierra la ventana de Categorías y Marcas."""
        if self._taxonomy_window:
            # Limpiar binding de mousewheel
            if hasattr(self._taxonomy_window, '_mousewheel_binding'):
                self._taxonomy_window.unbind_all("<MouseWheel>")
            self._taxonomy_window.destroy()
            self._taxonomy_window = None
    
    def open_receipt_window(self):
        """Abre Plantilla de recibo en una ventana independiente con TODO el contenido visible."""
        # Verificar si ya existe y traer al frente
        if self._receipt_window is not None and self._receipt_window.winfo_exists():
            self._receipt_window.lift()
            self._receipt_window.focus_force()
            return
        
        # Crear nueva ventana
        self._receipt_window = tk.Toplevel(self._parent())
        self._receipt_window.title("Editor de Plantilla de Recibo - TECH SYSTEMS ERP")
        
        # Configurar ventana maximizada (no fullscreen)
        self._receipt_window.state("zoomed")
        self._receipt_window.minsize(1200, 800)
        
        # Configurar cierre
        self._receipt_window.protocol("WM_DELETE_WINDOW", self._on_receipt_window_close)
        
        # Configurar estilo de la ventana
        self._receipt_window.configure(bg=PALETTE["blue_soft"])
        
        # Construir TODO el contenido de la plantilla en la nueva ventana
        self._build_receipt_window_content(self._receipt_window)
    
    def _build_receipt_window_content(self, window):
        """Construye TODO el contenido de la plantilla de recibo en la ventana emergente."""
        # Frame principal con padding
        main_container = ttk.Frame(window, padding=20, style="App.TFrame")
        main_container.pack(fill="both", expand=True)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)

        # Header con título y botón cerrar
        header = ttk.Frame(main_container, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="📄 Editor visual del recibo", 
                 style="Subheader.TLabel", font=('Segoe UI', 18, 'bold')).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Edita el recibo como lo verá el cliente. Ventas y Reimpresión usarán esta misma plantilla activa.",
            style="Muted.TLabel",
            font=('Segoe UI', 11)
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        ttk.Button(
            header,
            text="✕ Cerrar",
            style="Danger.TButton",
            command=self._on_receipt_window_close
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))
        self._create_help_button(header, "receipt", 2, owner=lambda: self._receipt_window, row=0, padx=(8, 0))

        # Layout principal con dos columnas (50% cada una)
        body = ttk.Frame(main_container, style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # ========== COLUMNA IZQUIERDA: EDICIÓN COMPLETA ==========
        editor_card = ttk.LabelFrame(body, text="✏️ Edición visual", style="Card.TLabelframe")
        editor_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        editor_card.columnconfigure(0, weight=1)
        editor_card.rowconfigure(1, weight=1)

        # Barra de estado
        status_bar = ttk.Frame(editor_card, style="Surface.TFrame")
        status_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 5))
        status_bar.columnconfigure(0, weight=1)

        ttk.Label(
            status_bar,
            text="Las etiquetas del recibo y la estructura fiscal son fijas. Solo se edita la información del negocio.",
            style="Muted.TLabel",
            wraplength=520,
        ).grid(row=0, column=0, sticky="w")

        # Área de formularios con scroll (para que TODO sea visible)
        form_canvas = tk.Canvas(editor_card, highlightthickness=0, bg=PALETTE["surface_alt"])
        form_canvas.grid(row=1, column=0, sticky="nsew", padx=8, pady=(5, 5))
        
        form_scroll = ttk.Scrollbar(editor_card, orient="vertical", command=form_canvas.yview)
        form_scroll.grid(row=1, column=1, sticky="ns", pady=5)
        form_canvas.configure(yscrollcommand=form_scroll.set)
        
        form_area = ttk.Frame(form_canvas, style="App.TFrame")
        form_canvas.create_window((0, 0), window=form_area, anchor="nw", width=form_canvas.winfo_width())
        form_area.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.bind("<Configure>", lambda e: form_canvas.itemconfig(1, width=e.width))

        # Datos del negocio
        business_card = ttk.LabelFrame(form_area, text="🏢 Datos del negocio", style="Card.TLabelframe")
        business_card.grid(row=0, column=0, sticky="ew", pady=(0, 15), padx=5)
        business_card.columnconfigure(1, weight=1)

        business_fields = [
            ("Nombre negocio", self.company_name_var),
            ("RTN", self.company_rtn_var),
            ("Teléfono", self.company_tel_var),
            ("Email", self.company_email_var),
            ("Logo URL", self.company_logo_var),
        ]
        for row, (label_text, variable) in enumerate(business_fields):
            ttk.Label(business_card, text=label_text, style="FormLabel.TLabel", font=('Segoe UI', 10)).grid(
                row=row, column=0, sticky="w", padx=10, pady=8
            )
            ttk.Entry(business_card, textvariable=variable, font=('Segoe UI', 10), width=35).grid(
                row=row, column=1, sticky="ew", padx=10, pady=8
            )

        ttk.Label(business_card, text="Dirección", style="FormLabel.TLabel", font=('Segoe UI', 10)).grid(
            row=len(business_fields), column=0, sticky="nw", padx=10, pady=8
        )
        self.company_address_text = tk.Text(business_card, height=4, wrap=tk.WORD, 
                                            relief="solid", borderwidth=1, font=('Segoe UI', 10), width=35)
        self.company_address_text.grid(row=len(business_fields), column=1, sticky="ew", padx=10, pady=8)
        self.company_address_text.insert("1.0", self.db.get_config("empresa_direccion", "") or "")

        info_card = ttk.LabelFrame(form_area, text="ℹ️ Estructura fija del recibo", style="Card.TLabelframe")
        info_card.grid(row=1, column=0, sticky="ew", pady=(0, 5), padx=5)
        info_card.columnconfigure(0, weight=1)

        ttk.Label(
            info_card,
            text=(
                "El recibo usa etiquetas internas fijas y un resumen fiscal estándar. "
                "Ya no se configuran textos visibles, observaciones fijas ni plantillas manuales."
            ),
            style="Muted.TLabel",
            wraplength=520,
            font=('Segoe UI', 9)
        ).grid(row=0, column=0, sticky="w", padx=10, pady=10)

        # ========== COLUMNA DERECHA: VISTA PREVIA COMPLETA ==========
        preview_card = ttk.LabelFrame(body, text="👁️ Vista previa en tiempo real", style="Card.TLabelframe")
        preview_card.grid(row=0, column=1, sticky="nsew")
        preview_card.columnconfigure(0, weight=1)
        preview_card.rowconfigure(1, weight=1)

        ttk.Label(
            preview_card,
            text="Así se verá el recibo en Ventas y en la reimpresión",
            style="Muted.TLabel",
            font=('Segoe UI', 10)
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 5))

        # Frame contenedor para preview con scroll
        preview_container = ttk.Frame(preview_card, style="Surface.TFrame")
        preview_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        preview_container.columnconfigure(0, weight=1)
        preview_container.rowconfigure(0, weight=1)

        preview_canvas = tk.Canvas(
            preview_container,
            highlightthickness=0,
            background=PALETTE["surface_alt"],
        )
        preview_canvas.grid(row=0, column=0, sticky="nsew")
        preview_scroll_y = ttk.Scrollbar(preview_container, orient="vertical", command=preview_canvas.yview)
        preview_scroll_y.grid(row=0, column=1, sticky="ns")
        preview_canvas.configure(yscrollcommand=preview_scroll_y.set)

        self.preview_inner = ttk.Frame(preview_canvas, style="Surface.TFrame", padding=8)
        self.preview_window_id = preview_canvas.create_window((0, 0), window=self.preview_inner, anchor="nw")
        self.preview_inner.bind(
            "<Configure>",
            lambda _event: preview_canvas.configure(scrollregion=preview_canvas.bbox("all"))
        )
        preview_canvas.bind(
            "<Configure>",
            lambda event: preview_canvas.itemconfigure(self.preview_window_id, width=event.width)
        )

        self.preview_card_shell = ttk.Frame(self.preview_inner, style="Surface.TFrame", padding=12)
        self.preview_card_shell.grid(row=0, column=0, sticky="nsew")
        self.preview_card_shell.columnconfigure(0, weight=1)

        self.preview_receipt_frame = tk.Frame(
            self.preview_card_shell,
            bg=PALETTE["white"],
            bd=1,
            relief="solid",
            padx=20,
            pady=20,
        )
        self.preview_receipt_frame.grid(row=0, column=0, sticky="nsew")
        self.preview_receipt_frame.grid_columnconfigure(0, weight=1)

        # Botones de acción
        btn_frame = ttk.Frame(main_container, style="App.TFrame")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        
        ttk.Button(btn_frame, text="🌐 Vista previa en navegador", style="Secondary.TButton", 
                  command=self.preview_receipt).pack(side="left", padx=(0, 10))
        ttk.Button(btn_frame, text="💾 Guardar cambios", style="Primary.TButton", command=self.save_receipt_template).pack(
            side="right"
        )

        self._hydrate_receipt_editor_widgets()

        # Bindings para actualización en tiempo real
        self._bind_receipt_preview_updates()
        
        # Inicializar preview
        self.refresh_receipt_preview()
    
    def _on_receipt_window_close(self):
        """Cierra la ventana de Plantilla de recibo."""
        if self._receipt_window:
            self._receipt_window.destroy()
            self._receipt_window = None

    def open_personalization_window(self):
        """Abre la ventana de personalización del sistema."""
        if self._personalization_window is not None and self._personalization_window.winfo_exists():
            self._personalization_window.lift()
            self._personalization_window.focus_force()
            return

        self.theme_var.set(getattr(self.app, "current_theme", self.db.get_config("ui_theme", "light") or "light"))
        self._personalization_window = tk.Toplevel(self._parent())
        self._personalization_window.title("Personalización del Sistema - TECH SYSTEMS ERP")
        self._personalization_window.state("zoomed")
        self._personalization_window.minsize(960, 640)
        self._personalization_window.protocol("WM_DELETE_WINDOW", self._on_personalization_window_close)

        self._build_personalization_window_content(self._personalization_window)

    def _build_personalization_window_content(self, window):
        main = ttk.Frame(window, padding=20, style="App.TFrame")
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        header = ttk.Frame(main, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="🎨 Personalización", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Elige cómo se verá todo el sistema. El cambio se aplica en tiempo real y queda guardado para la próxima sesión.",
            style="Muted.TLabel",
            wraplength=860,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(
            header,
            text="✕ Cerrar",
            style="Danger.TButton",
            command=self._on_personalization_window_close,
        ).grid(row=0, column=1, rowspan=2, sticky="e")
        self._create_help_button(header, "personalization", 2, owner=lambda: self._personalization_window, row=0, padx=(8, 0))

        body = ttk.Frame(main, style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        selector_card = ttk.LabelFrame(body, text="Tema", style="Card.TLabelframe")
        selector_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        selector_card.columnconfigure(0, weight=1)

        ttk.Label(
            selector_card,
            text="Selecciona un tema visual global para ventanas, formularios, tablas, botones y módulos emergentes.",
            style="Muted.TLabel",
            wraplength=520,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 10))

        options_frame = ttk.Frame(selector_card, style="Surface.TFrame", padding=12)
        options_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        options_frame.columnconfigure(0, weight=1)

        for idx, (theme_key, theme_label) in enumerate(get_available_themes()):
            ttk.Radiobutton(
                options_frame,
                text=theme_label,
                value=theme_key,
                variable=self.theme_var,
                command=self._apply_selected_theme,
            ).grid(row=idx, column=0, sticky="w", pady=6)

        ttk.Label(
            selector_card,
            text="Los cambios se guardan automáticamente y se aplican sin reiniciar el sistema.",
            style="Muted.TLabel",
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 12))

        preview_card = ttk.LabelFrame(body, text="Vista del estilo", style="Card.TLabelframe")
        preview_card.grid(row=0, column=1, sticky="nsew")
        preview_card.columnconfigure(0, weight=1)

        preview_shell = ttk.Frame(preview_card, style="Surface.TFrame", padding=16)
        preview_shell.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        preview_shell.columnconfigure(0, weight=1)

        preview_header = ttk.Frame(preview_shell, style="Surface.TFrame")
        preview_header.grid(row=0, column=0, sticky="ew")
        preview_header.columnconfigure(0, weight=1)
        ttk.Label(preview_header, text="Apariencia general", style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
        self._create_help_button(
            preview_header,
            "appearance_preview",
            1,
            owner=lambda: self._personalization_window,
            row=0,
            padx=(6, 0),
        )
        ttk.Label(
            preview_shell,
            text="El sistema mantendrá una línea visual consistente en dashboard, configuraciones, POS y ventanas emergentes.",
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=1, column=0, sticky="w", pady=(6, 12))
        ttk.Entry(preview_shell).grid(row=2, column=0, sticky="ew")
        ttk.Button(preview_shell, text="Botón principal", style="Primary.TButton").grid(row=3, column=0, sticky="w", pady=(12, 6))
        ttk.Button(preview_shell, text="Acción secundaria", style="Secondary.TButton").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Button(preview_shell, text="Guardar", style="Success.TButton").grid(row=5, column=0, sticky="w", pady=6)

    def _apply_selected_theme(self):
        """Aplica y persiste el tema seleccionado desde Configuración."""
        selected_theme = self.theme_var.get().strip().lower() or "light"
        try:
            if hasattr(self.app, "apply_ui_theme"):
                self.app.apply_ui_theme(selected_theme, persist=True)
            else:
                self.db.set_config("ui_theme", selected_theme)
            if self._personalization_window and self._personalization_window.winfo_exists():
                self._personalization_window.lift()
        except Exception as exc:
            messagebox.showerror(
                "Error",
                f"No se pudo aplicar el tema seleccionado.\n\n{exc}",
                parent=self._parent(),
            )

    def _on_personalization_window_close(self):
        if self._personalization_window:
            self._personalization_window.destroy()
            self._personalization_window = None

    def focus_backup_tab(self):
        if hasattr(self, "backup_panel"):
            self.notebook.select(self.backup_panel.master)
            self.backup_panel.refresh_all()
            self.backup_panel.focus_primary_action()

    # ========================================================================
    # DESCUENTOS (funcionalidad original - SIN CAMBIOS)
    # ========================================================================
    
    def create_discount_tab(self, parent):
        """Crea la pestaña de gestión de descuentos."""
        parent.grid_columnconfigure(0, weight=2)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(parent, text="Listado de descuentos", style="Card.TLabelframe")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)

        form_frame = ttk.LabelFrame(parent, text="Formulario", style="Card.TLabelframe")
        form_frame.grid(row=0, column=1, sticky="nsew")
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(
            list_frame,
            text="Descuentos para ventas por tipo de cliente, producto o volumen.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.disc_tree = ttk.Treeview(
            list_frame,
            columns=("ID", "Nombre", "Tipo", "Porcentaje"),
            show="headings",
            height=14,
        )
        
        for col, width, anchor in (
            ("ID", 60, "center"),
            ("Nombre", 240, "w"),
            ("Tipo", 130, "center"),
            ("Porcentaje", 120, "center"),
        ):
            self.disc_tree.heading(col, text=col)
            self.disc_tree.column(col, width=width, anchor=anchor)

        y_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.disc_tree.yview)
        self.disc_tree.configure(yscrollcommand=y_scroll.set)

        self.disc_tree.grid(row=1, column=0, sticky="nsew")
        y_scroll.grid(row=1, column=1, sticky="ns")
        self.disc_tree.bind("<<TreeviewSelect>>", self.select_discount)

        btn_frame = ttk.Frame(list_frame, style="Surface.TFrame")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(btn_frame, text="➕ Nuevo", style="Secondary.TButton", command=self.start_new_discount).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="🗑️ Eliminar", style="Danger.TButton", command=self.delete_discount).pack(side="left")

        fields = [
            ("Nombre", self.disc_nombre),
            ("Porcentaje (%)", self.disc_porcentaje),
        ]
        row = 0
        for label, var in fields:
            ttk.Label(form_frame, text=label, style="FormLabel.TLabel").grid(
                row=row, column=0, sticky="w", padx=4, pady=7
            )
            entry = ttk.Entry(form_frame, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", padx=4, pady=7)
            if row == 0:
                self.disc_nombre_entry = entry
            row += 1

        ttk.Label(form_frame, text="Tipo", style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="w", padx=4, pady=7
        )
        ttk.Combobox(
            form_frame,
            textvariable=self.disc_tipo,
            values=["Docena", "Mayorista", "Producto"],
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", padx=4, pady=7)
        row += 1

        ttk.Button(form_frame, text="💾 Guardar descuento", style="Primary.TButton", command=self.save_discount).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(16, 0)
        )

    def load_discounts(self):
        """Carga la lista de descuentos desde la base de datos."""
        for item in self.disc_tree.get_children():
            self.disc_tree.delete(item)

        discounts = self.repository.list_discounts()
        for disc in discounts:
            self.disc_tree.insert("", "end", values=(
                disc[0], disc[1], disc[2], f"{int(disc[3] * 100)}%"
            ))

    def select_discount(self, _event):
        """Selecciona un descuento del árbol."""
        selected_item = self.disc_tree.focus()
        if not selected_item:
            return

        values = self.disc_tree.item(selected_item, "values")
        self.disc_id.set(values[0])
        self.disc_nombre.set(values[1])
        self.disc_tipo.set(values[2])
        self.disc_porcentaje.set(values[3].strip("%"))

    def reset_discount_form(self):
        """Limpia el formulario de descuentos."""
        self.disc_id.set("")
        self.disc_nombre.set("")
        self.disc_porcentaje.set("")
        self.disc_tipo.set("Docena")

    def start_new_discount(self):
        self.reset_discount_form()
        self.disc_tree.selection_remove(self.disc_tree.selection())
        self.disc_tree.focus("")
        self.disc_nombre_entry.focus_set()

    def save_discount(self):
        """Guarda un descuento (nuevo o actualizado)."""
        nombre = self.disc_nombre.get().strip()
        porcentaje = self.disc_porcentaje.get().strip()
        tipo = self.disc_tipo.get().strip()

        if not all([nombre, porcentaje, tipo]):
            messagebox.showerror("Error", "Complete todos los campos.", parent=self._parent())
            return

        try:
            pct = float(porcentaje) / 100.0
            if pct <= 0 or pct >= 1:
                messagebox.showerror("Error", "El porcentaje debe estar entre 1 y 99.", parent=self._parent())
                return
        except ValueError:
            messagebox.showerror("Error", "El porcentaje debe ser numerico.", parent=self._parent())
            return

        try:
            self.repository.save_discount(self.disc_id.get() or None, nombre, tipo, pct)
        except RepositoryError as exc:
            messagebox.showerror("Error", f"No se pudo guardar el descuento.\n\n{exc}", parent=self._parent())
            return

        messagebox.showinfo(
            "Éxito",
            "Descuento actualizado." if self.disc_id.get() else "Descuento agregado.",
            parent=self._parent(),
        )

        self.load_discounts()
        self.reset_discount_form()

    def delete_discount(self):
        """Elimina un descuento seleccionado."""
        selected_item = self.disc_tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Seleccione un descuento primero.", parent=self._parent())
            return

        disc_id = self.disc_tree.item(selected_item, "values")[0]
        if messagebox.askyesno("Confirmar", f"Eliminar el descuento ID {disc_id}?", parent=self._parent()):
            try:
                self.repository.delete_discount(int(disc_id))
            except RepositoryError as exc:
                messagebox.showerror("Error", f"No se pudo eliminar el descuento.\n\n{exc}", parent=self._parent())
                return
            messagebox.showinfo("Éxito", "Descuento eliminado.", parent=self._parent())
            self.load_discounts()
            self.reset_discount_form()

    # ========================================================================
    # MÉTODOS DE SOPORTE PARA PLANTILLA (se mantienen igual)
    # ========================================================================
    
    def _load_receipt_settings(self):
        """Carga todas las configuraciones del recibo."""
        render_settings = load_receipt_render_settings(self.db.get_config)
        company = render_settings["empresa"]
        self.company_name_var.set(company["nombre"])
        self.company_rtn_var.set(company["rtn"])
        self.company_tel_var.set(company["tel"])
        self.company_email_var.set(company["email"])
        self.company_logo_var.set(company["logo_url"])
        return {
            "company_address": company["direccion"],
        }

    def _set_text_widget_value(self, widget, value):
        """Sincroniza el contenido de un Text con la configuración persistida."""
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value or "")

    def _hydrate_receipt_editor_widgets(self):
        """Recarga la UI del editor usando siempre la última configuración guardada."""
        settings = self._load_receipt_settings()

        if hasattr(self, "company_address_text"):
            self._set_text_widget_value(self.company_address_text, settings["company_address"])

    def _bind_receipt_preview_updates(self):
        """Vincula todas las variables para actualizar el preview."""
        for variable in (
            self.company_name_var,
            self.company_rtn_var,
            self.company_tel_var,
            self.company_email_var,
            self.company_logo_var,
        ):
            variable.trace_add("write", self._on_receipt_settings_changed)

        self.company_address_text.bind("<KeyRelease>", self._on_receipt_text_changed)

    def _on_receipt_settings_changed(self, *_args):
        """Callback cuando cambian las configuraciones."""
        self.refresh_receipt_preview()

    def _on_receipt_text_changed(self, _event=None):
        """Callback cuando cambian los textos."""
        self.refresh_receipt_preview()

    def _preview_company(self):
        """Devuelve los datos de la empresa para la vista previa."""
        return {
            "nombre": self.company_name_var.get().strip() or "TECH SYSTEMS ERP",
            "rtn": self.company_rtn_var.get().strip() or "08011990000000",
            "tel": self.company_tel_var.get().strip() or "2233-4455",
            "direccion": self.company_address_text.get("1.0", tk.END).strip() 
            or "Tegucigalpa, Honduras",
            "email": self.company_email_var.get().strip() or "info@techsystems.hn",
            "logo_url": self.company_logo_var.get().strip(),
        }

    def _preview_number_to_words(self, number):
        """Convierte números a letras para la vista previa."""
        try:
            num = int(number)
            if num == 0:
                return "CERO"
            return str(num)
        except:
            return str(number)

    def _preview_items(self):
        """Devuelve items de ejemplo para la vista previa."""
        return [
            {
                "producto_id": 4,
                "nombre": "Producto de ejemplo",
                "cantidad": 2,
                "precio_unitario": 15.50,
                "descuento_porcentaje": 0,
                "tax_rate": 0.15,
                "tax_exempt": False,
            },
        ]

    def refresh_receipt_preview(self):
        """Actualiza la vista previa visual usando la misma fuente central de recibos."""
        try:
            view_model = build_receipt_view_model(
                venta_id="439",
                fecha="2025-10-14 13:05:41",
                items=self._preview_items(),
                metodo_pago="EFECTIVO",
                mode="ticket",
                empresa=self._preview_company(),
                number_to_words=self._preview_number_to_words,
                tax_included=True,
                amount_received=20.0,
            )
            self._render_visual_receipt_preview(view_model)
        except Exception as e:
            self._render_preview_error(e)

    def _render_preview_error(self, error):
        for child in self.preview_receipt_frame.winfo_children():
            child.destroy()
        tk.Label(
            self.preview_receipt_frame,
            text=f"Error al generar la vista previa: {error}",
            bg=PALETTE["white"],
            fg=PALETTE["danger"],
            justify="left",
            wraplength=360,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w")

    def _render_visual_receipt_preview(self, view_model):
        for child in self.preview_receipt_frame.winfo_children():
            child.destroy()

        company = view_model["company"]
        labels = view_model["labels"]
        row = 0

        def add_label(text, *, font=("Courier New", 10), bold=False, anchor="center", fg=None, pady=(0, 0)):
            nonlocal row
            label_font = font
            if bold:
                label_font = (font[0], font[1], "bold")
            tk.Label(
                self.preview_receipt_frame,
                text=text,
                bg=PALETTE["white"],
                fg=fg or PALETTE["black"],
                font=label_font,
                justify="center" if anchor == "center" else "left",
                anchor=anchor,
            ).grid(row=row, column=0, sticky="ew" if anchor == "center" else "w", pady=pady)
            row += 1

        add_label(company["nombre"], font=("Courier New", 11), bold=True, pady=(0, 2))
        add_label(f"R.T.N.: {company['rtn']}", pady=(0, 1))
        add_label(f"Tel: {company['tel']}", pady=(0, 1))
        add_label(company["direccion"], pady=(0, 1))
        add_label(f"Email: {company['email']}", pady=(0, 8))
        add_label(labels["DOC_TITLE"], font=("Courier New", 12), bold=True, pady=(0, 4))
        add_label(f"No. 0000-0001-{str(view_model['venta_id']).zfill(3)}", pady=(0, 1))
        add_label(f"Fecha: {view_model['fecha']}", pady=(0, 10))

        table = ttk.Treeview(
            self.preview_receipt_frame,
            columns=("cant", "codigo", "producto", "precio", "subtotal"),
            show="headings",
            height=max(1, len(view_model["items"])),
        )
        for key, title, width, anchor in (
            ("cant", "Cant.", 52, "center"),
            ("codigo", "Código", 82, "center"),
            ("producto", "Producto", 170, "w"),
            ("precio", "P.Unit", 84, "e"),
            ("subtotal", "Subtotal", 84, "e"),
        ):
            table.heading(key, text=title)
            table.column(key, width=width, anchor=anchor, stretch=key == "producto")
        for item in view_model["items"]:
            qty = item["cantidad"]
            qty_text = str(int(qty)) if float(qty).is_integer() else f"{qty:g}"
            table.insert(
                "",
                "end",
                values=(
                    qty_text,
                    item["codigo"],
                    item["producto"],
                    f"L {item['precio_unitario']:.2f}",
                    f"L {item['subtotal']:.2f}",
                ),
            )
        table.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        add_label(view_model["monto_letras"], bold=True, anchor="w", pady=(0, 6))
        add_label(labels["ORDER_EXEMPT_LABEL"], anchor="w")
        add_label(labels["EXEMPT_REGISTER_LABEL"], anchor="w")
        add_label(labels["DISCOUNTS_LABEL"], anchor="w", pady=(0, 6))

        taxes_title = tk.Label(
            self.preview_receipt_frame,
            text="Concepto                           Total",
            bg=PALETTE["white"],
            fg=PALETTE["black"],
            font=("Courier New", 10, "bold"),
            anchor="w",
        )
        taxes_title.grid(row=row, column=0, sticky="w", pady=(0, 2))
        row += 1

        for label, value in view_model["summary_rows"]:
            add_label(f"{label:<22} L {value:>7.2f}", anchor="w")

        for label, value in view_model["payment_rows"]:
            add_label(f"{label}:    L {value:.2f}", anchor="w")
        if view_model["observaciones"]:
            add_label(f"{labels['LABEL_OBSERVACIONES']}: {view_model['observaciones']}", anchor="w", pady=(0, 8))
        add_label(labels["COPY_LABEL"], pady=(2, 0))
        add_label(labels["THANK_YOU_MESSAGE"], pady=(0, 0))

    def preview_receipt(self):
        """Abre una vista previa real en el navegador."""
        try:
            html_preview = build_receipt_html(
                venta_id="439",
                fecha="2025-10-14 15:24:00",
                total=31.00,
                monto_pagado=35.00,
                vuelto=4.00,
                items=self._preview_items(),
                cliente=None,
                metodo_pago="EFECTIVO",
                mode="ticket",
                empresa=self._preview_company(),
                number_to_words=self._preview_number_to_words,
            )
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", 
                                            delete=False, encoding="utf-8") as handle:
                handle.write(html_preview)
                self._last_preview_path = handle.name
            webbrowser.open(f"file://{self._last_preview_path}")
            messagebox.showinfo(
                "Vista previa",
                "La vista previa real se abrió en el navegador usando la misma plantilla activa de Ventas.",
                parent=self._parent(),
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar la vista previa: {e}", 
                                parent=self._parent())

    def save_receipt_template(self):
        """Guarda únicamente la información editable del negocio."""
        try:
            self.db.set_config("empresa_nombre", self.company_name_var.get().strip())
            self.db.set_config("empresa_rtn", self.company_rtn_var.get().strip())
            self.db.set_config("empresa_tel", self.company_tel_var.get().strip())
            self.db.set_config("empresa_email", self.company_email_var.get().strip())
            self.db.set_config("empresa_logo_url", self.company_logo_var.get().strip())
            self.db.set_config("empresa_direccion", self.company_address_text.get("1.0", tk.END).strip())
            
            messagebox.showinfo(
                "Éxito", 
                "La información del negocio quedó guardada y sincronizada con Ventas.",
                parent=self._parent()
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar la plantilla.\n\n{exc}", 
                                parent=self._parent())

