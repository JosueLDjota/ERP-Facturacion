"""
Sistema POS Profesional - Versión Microsoft Dynamics Style
Características:
- Ventana emergente para búsqueda de productos (MAXIMIZADA, sin contenido oculto)
- Diseño ultra profesional con métricas en tiempo real
- Modal de búsqueda que no se cierra al agregar
- Vista de recibo profesional integrada
- Scroll suave con mouse wheel
- Compatibilidad total con lógica de facturación existente
"""

import random
import tempfile
import webbrowser
import os
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from erp.data.repositories.sale_repository import SaleRepository
from erp.domain.services.invoice_calculator import calculate_invoice_totals
from erp.domain.services.receipt_service import ReceiptService
from erp.domain.use_cases.sales.create_pos_sale import CreatePOSSale
from erp.domain.use_cases.sales.load_pos_context import LoadPOSContext
from receipt_builder import build_receipt_view_model, load_receipt_render_settings
from .ui import FONTS, PALETTE, center_window, format_hnl, normalize_hnl_amount, parse_hnl


class ProductSearchModal:
    """Ventana emergente profesional para exploración de productos - VERSIÓN CORREGIDA (sin contenido oculto)"""

    PRICE_FILTERS = (
        "Todos",
        "Hasta L 100",
        "L 100 - L 500",
        "L 500 - L 1,000",
        "Más de L 1,000",
    )

    AVAILABILITY_FILTERS = ("Todos", "Disponibles", "Stock bajo", "Sin stock")

    def __init__(self, parent, callback, product_index, discount_options=None):
        self.parent = parent
        self.owner = parent.winfo_toplevel()
        self.callback = callback
        self.product_index = product_index
        self.discount_options = discount_options or ["Sin descuento"]
        self.selected_product = None
        self.product_lookup = {}

        # Crear ventana
        self.window = tk.Toplevel(self.owner)
        self.window.title("📦 Catálogo Comercial - Sistema POS Profesional")
        self.window.transient(self.owner)
        self.window.grab_set()
        self.window.resizable(True, True)
        
        # CONFIGURACIÓN CRÍTICA: Asegurar que la ventana se muestre completa
        self.window.update_idletasks()
        
        # Obtener dimensiones de la pantalla
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # Configurar ventana para ocupar toda la pantalla (sin bordes de título ocultos)
        try:
            # Intentar maximizar en Windows
            self.window.state("zoomed")
        except tk.TclError:
            try:
                # Alternativa para Linux
                self.window.attributes("-zoomed", True)
            except tk.TclError:
                # Respaldo: usar tamaño completo de pantalla
                self.window.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Establecer tamaño mínimo razonable
        self.window.minsize(1100, 700)
        
        self._setup_styles()
        self._build_ui()
        self._load_products()

        # Eventos de teclado
        self.window.bind("<Escape>", lambda e: self.window.destroy())
        self.window.bind("<Return>", lambda e: self._add_and_continue())

    def _setup_styles(self):
        """Configura estilos locales del explorador comercial."""
        style = ttk.Style()
        style.configure("CatalogHero.TFrame", background=PALETTE.get("white", "#ffffff"))
        style.configure("CatalogTitle.TLabel", font=("Segoe UI Semibold", 18), foreground=PALETTE.get("black", "#000000"), background=PALETTE.get("white", "#ffffff"))
        style.configure("CatalogMuted.TLabel", font=("Segoe UI", 9), foreground=PALETTE.get("gray_text", "#666666"), background=PALETTE.get("white", "#ffffff"))
        style.configure("CatalogImage.TFrame", background=PALETTE.get("blue_light", "#e3f2fd"))
        style.configure("CatalogPrice.TLabel", font=("Segoe UI Semibold", 20), foreground=PALETTE.get("blue_primary", "#007bff"), background=PALETTE.get("white", "#ffffff"))
        style.configure("CatalogBadge.TLabel", font=("Segoe UI Semibold", 9), foreground=PALETTE.get("blue_dark", "#0056b3"), background=PALETTE.get("blue_light", "#e3f2fd"), padding=(10, 4))
        style.configure("CatalogAction.TButton", font=("Segoe UI Semibold", 10), padding=(12, 10))
        style.map(
            "Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#0f172a")],
        )

    def _configure_scroll_region(self, event=None):
        """Configura la región de scroll para que TODO el contenido sea visible"""
        if hasattr(self, "scroll_canvas"):
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _resize_scrollable_content(self, event):
        """Ajusta el ancho del contenido cuando se redimensiona la ventana"""
        if hasattr(self, "scroll_window_id"):
            self.scroll_canvas.itemconfigure(self.scroll_window_id, width=event.width)

    def _bind_mousewheel(self, event=None):
        """Activa el scroll con rueda del mouse"""
        self.window.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event=None):
        """Desactiva el scroll con rueda del mouse"""
        self.window.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        """Maneja el evento de scroll con rueda del mouse"""
        if hasattr(self, "scroll_canvas"):
            # Normalizar delta para diferentes sistemas operativos
            if event.num == 4:  # Linux scroll up
                delta = -1
            elif event.num == 5:  # Linux scroll down
                delta = 1
            else:  # Windows/macOS
                delta = -1 * int(event.delta / 120) if event.delta else 0
            
            if delta:
                self.scroll_canvas.yview_scroll(delta, "units")

    def _build_ui(self):
        """Construye interfaz de catálogo tipo e-commerce/POS - CON SCROLL CORRECTO"""
        # Frame principal con Canvas para scroll
        shell = ttk.Frame(self.window)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(0, weight=1)

        canvas_bg = PALETTE.get("surface_alt", PALETTE.get("white", "#ffffff"))
        
        # Canvas con scrollbar
        self.scroll_canvas = tk.Canvas(shell, highlightthickness=0, bg=canvas_bg)
        page_scroll = ttk.Scrollbar(shell, orient="vertical", command=self.scroll_canvas.yview)
        
        self.scroll_canvas.configure(yscrollcommand=page_scroll.set)
        
        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")
        page_scroll.grid(row=0, column=1, sticky="ns")

        # Frame interno que contendrá TODO el contenido
        main_frame = ttk.Frame(self.scroll_canvas, padding="16")
        main_frame.columnconfigure(0, weight=2)  # Lista de productos
        main_frame.columnconfigure(1, weight=1)  # Detalle del producto
        main_frame.rowconfigure(2, weight=1)     # Área principal
        
        self.scroll_window_id = self.scroll_canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        # Eventos para scroll dinámico
        main_frame.bind("<Configure>", self._configure_scroll_region)
        self.scroll_canvas.bind("<Configure>", self._resize_scrollable_content)
        
        # Eventos para scroll con mouse
        self.window.bind("<Enter>", self._bind_mousewheel)
        self.window.bind("<Leave>", self._unbind_mousewheel)

        # ========== HEADER ==========
        header = ttk.Frame(main_frame, style="CatalogHero.TFrame", padding=(16, 16, 16, 12))
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        
        ttk.Label(header, text="📦 Catálogo de Productos", style="CatalogTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Explora, filtra, revisa el detalle y agrega productos al carrito sin salir del flujo de venta.",
            style="CatalogMuted.TLabel",
            wraplength=760,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(header, text="ESC para cerrar | Doble clic para agregar", style="CatalogBadge.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")

        # ========== FILTROS ==========
        filter_frame = ttk.LabelFrame(main_frame, text="🔍 Búsqueda y filtros avanzados", padding="12")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Configurar columnas para filtros
        for i in range(5):
            filter_frame.columnconfigure(i, weight=1)

        self.search_var = tk.StringVar()
        self.category_var = tk.StringVar(value="Todas")
        self.availability_var = tk.StringVar(value=self.AVAILABILITY_FILTERS[0])
        self.price_var = tk.StringVar(value=self.PRICE_FILTERS[0])

        # Buscador
        ttk.Label(filter_frame, text="🔎 Buscar producto", style="CatalogMuted.TLabel").grid(row=0, column=0, sticky="w")
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, font=("Segoe UI", 11))
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self._filter_products)
        self.search_entry.focus()

        # Categoría
        ttk.Label(filter_frame, text="📂 Categoría", style="CatalogMuted.TLabel").grid(row=0, column=1, sticky="w")
        self.category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var, state="readonly")
        self.category_combo.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.category_combo.bind("<<ComboboxSelected>>", self._filter_products)

        # Disponibilidad
        ttk.Label(filter_frame, text="📊 Disponibilidad", style="CatalogMuted.TLabel").grid(row=0, column=2, sticky="w")
        self.availability_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.availability_var,
            state="readonly",
            values=self.AVAILABILITY_FILTERS,
        )
        self.availability_combo.grid(row=1, column=2, sticky="ew", padx=(0, 8))
        self.availability_combo.bind("<<ComboboxSelected>>", self._filter_products)

        # Rango precio
        ttk.Label(filter_frame, text="💰 Rango de precio", style="CatalogMuted.TLabel").grid(row=0, column=3, sticky="w")
        self.price_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.price_var,
            state="readonly",
            values=self.PRICE_FILTERS,
        )
        self.price_combo.grid(row=1, column=3, sticky="ew", padx=(0, 8))
        self.price_combo.bind("<<ComboboxSelected>>", self._filter_products)

        # Botón limpiar filtros
        ttk.Button(
            filter_frame, 
            text="🗑️ Limpiar filtros", 
            style="CatalogAction.TButton", 
            command=self._reset_filters
        ).grid(row=1, column=4, sticky="ew")

        # ========== LISTA DE PRODUCTOS ==========
        list_frame = ttk.LabelFrame(main_frame, text="📋 Listado de productos", padding="10")
        list_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Treeview con columnas
        columns = ("Código", "Producto", "Categoría", "Precio", "Stock", "Estado")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=16,
            selectmode="browse"
        )
        
        # Configurar columnas
        self.tree.heading("Código", text="Código")
        self.tree.heading("Producto", text="Producto")
        self.tree.heading("Categoría", text="Categoría")
        self.tree.heading("Precio", text="Precio")
        self.tree.heading("Stock", text="Stock")
        self.tree.heading("Estado", text="Estado")

        self.tree.column("Código", width=90, anchor="center")
        self.tree.column("Producto", width=320, anchor="w")
        self.tree.column("Categoría", width=150, anchor="w")
        self.tree.column("Precio", width=110, anchor="e")
        self.tree.column("Stock", width=80, anchor="center")
        self.tree.column("Estado", width=120, anchor="center")

        # Scrollbar para la lista
        y_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        # Eventos del treeview
        self.tree.bind("<<TreeviewSelect>>", self._on_product_selected)
        self.tree.bind("<Double-1>", lambda e: self._add_and_continue())
        self.tree.bind("<Return>", lambda e: self._add_and_continue())

        # ========== PANEL DE DETALLE ==========
        detail_frame = ttk.LabelFrame(main_frame, text="📊 Detalle del producto", padding="14")
        detail_frame.grid(row=2, column=1, sticky="nsew")
        detail_frame.columnconfigure(0, weight=1)

        # Card de imagen/placeholder
        self.image_card = ttk.Frame(detail_frame, style="CatalogImage.TFrame", padding=(10, 18))
        self.image_card.grid(row=0, column=0, sticky="ew")
        self.image_card.columnconfigure(0, weight=1)
        
        self.image_label = ttk.Label(
            self.image_card, 
            text="🖼️\nSin imagen\nPreview comercial", 
            justify="center", 
            background=PALETTE.get("blue_light", "#e3f2fd"), 
            foreground=PALETTE.get("blue_dark", "#0056b3"), 
            font=("Segoe UI Semibold", 12)
        )
        self.image_label.grid(row=0, column=0, sticky="nsew")

        # Variables de detalle
        self.detail_name_var = tk.StringVar(value="Seleccione un producto")
        self.detail_price_var = tk.StringVar(value="L 0.00")
        self.detail_stock_var = tk.StringVar(value="Stock: 0")
        self.detail_category_var = tk.StringVar(value="Categoría: Sin categoría")
        self.detail_code_var = tk.StringVar(value="Código: -")
        self.detail_status_var = tk.StringVar(value="Disponible para explorar")
        self.detail_description_var = tk.StringVar(value="Aquí verás la descripción completa, disponibilidad y contexto comercial del producto.")

        # Mostrar información
        ttk.Label(detail_frame, textvariable=self.detail_name_var, style="CatalogTitle.TLabel", wraplength=380).grid(row=1, column=0, sticky="w", pady=(14, 0))
        ttk.Label(detail_frame, textvariable=self.detail_price_var, style="CatalogPrice.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(detail_frame, textvariable=self.detail_stock_var, style="CatalogMuted.TLabel").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Label(detail_frame, textvariable=self.detail_category_var, style="CatalogMuted.TLabel").grid(row=4, column=0, sticky="w")
        ttk.Label(detail_frame, textvariable=self.detail_code_var, style="CatalogMuted.TLabel").grid(row=5, column=0, sticky="w")
        ttk.Label(detail_frame, textvariable=self.detail_status_var, style="CatalogBadge.TLabel").grid(row=6, column=0, sticky="w", pady=(10, 0))
        ttk.Label(detail_frame, textvariable=self.detail_description_var, style="CatalogMuted.TLabel", wraplength=380, justify="left").grid(
            row=7, column=0, sticky="w", pady=(12, 0)
        )

        # ========== CONFIGURACIÓN DE AGREGADO ==========
        config_frame = ttk.LabelFrame(detail_frame, text="➕ Agregar al carrito", padding="10")
        config_frame.grid(row=8, column=0, sticky="ew", pady=(16, 0))
        config_frame.columnconfigure(1, weight=1)

        # Cantidad
        ttk.Label(config_frame, text="📦 Cantidad:").grid(row=0, column=0, sticky="w")
        self.qty_var = tk.IntVar(value=1)
        ttk.Spinbox(
            config_frame,
            from_=1,
            to=999,
            textvariable=self.qty_var,
            width=10,
            font=("Segoe UI", 10),
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # Descuento
        ttk.Label(config_frame, text="🏷️ Descuento:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.discount_combo = ttk.Combobox(
            config_frame,
            state="readonly",
            width=25,
            font=("Segoe UI", 10)
        )
        self.discount_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(10, 0))

        # Botones de acción
        btn_frame = ttk.Frame(detail_frame)
        btn_frame.grid(row=9, column=0, sticky="ew", pady=(16, 0))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ttk.Button(
            btn_frame,
            text="🔍 Ver detalle completo",
            command=self._open_detail_modal,
            style="CatalogAction.TButton"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            btn_frame,
            text="➕ Agregar y seguir",
            command=self._add_and_continue,
            style="CatalogAction.TButton"
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Button(
            detail_frame,
            text="✅ Agregar y cerrar",
            command=self._add_and_close,
            style="Success.TButton"
        ).grid(row=10, column=0, sticky="ew", pady=(8, 0))

        # Cargar descuentos
        self._load_discounts()
        
        # Sincronizar selección inicial
        self.window.after(100, self._sync_initial_selection)

    def _load_discounts(self):
        """Carga opciones de descuento"""
        self.discount_combo["values"] = self.discount_options
        self.discount_combo.set(self.discount_options[0] if self.discount_options else "Sin descuento")

    def _load_products(self):
        """Carga todos los productos"""
        self.all_products = []
        self.product_lookup = {}
        
        for prod_id, data in self.product_index.items():
            product = {
                "id": prod_id,
                "codigo": data.get("codigo_producto", str(prod_id)),
                "nombre": data["nombre"],
                "stock": data["stock"],
                "precio": data["precio"],
                "descripcion": data.get("descripcion", ""),
                "categoria_nombre": data.get("categoria_nombre", "") or "Sin categoría",
                "marca_nombre": data.get("marca_nombre", "") or "Sin marca",
            }
            self.all_products.append(product)
            self.product_lookup[str(prod_id)] = product
        
        # Obtener categorías únicas
        categories = sorted(set(prod["categoria_nombre"] for prod in self.all_products))
        self.category_combo["values"] = ["Todas", *categories]
        self.category_combo.set("Todas")
        
        self._filter_products()

    def _reset_filters(self):
        """Limpia todos los filtros"""
        self.search_var.set("")
        self.category_var.set("Todas")
        self.availability_var.set(self.AVAILABILITY_FILTERS[0])
        self.price_var.set(self.PRICE_FILTERS[0])
        self._filter_products()

    def _filter_products(self, event=None):
        """Filtra productos según criterios seleccionados"""
        search_text = self.search_var.get().lower().strip()
        selected_category = self.category_var.get()
        availability = self.availability_var.get()
        price_filter = self.price_var.get()

        # Limpiar tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Filtrar y mostrar
        for prod in self.all_products:
            # Filtro de búsqueda
            if search_text:
                haystack = f"{prod['nombre']} {prod['codigo']} {prod['categoria_nombre']} {prod['marca_nombre']}".lower()
                if search_text not in haystack:
                    continue

            # Filtro de categoría
            if selected_category != "Todas" and prod["categoria_nombre"] != selected_category:
                continue

            # Filtro de disponibilidad
            if availability == "Disponibles" and prod["stock"] <= 0:
                continue
            if availability == "Stock bajo" and not (0 < prod["stock"] < 10):
                continue
            if availability == "Sin stock" and prod["stock"] != 0:
                continue

            # Filtro de precio
            if price_filter == "Hasta L 100" and prod["precio"] > 100:
                continue
            if price_filter == "L 100 - L 500" and not (100 <= prod["precio"] <= 500):
                continue
            if price_filter == "L 500 - L 1,000" and not (500 <= prod["precio"] <= 1000):
                continue
            if price_filter == "Más de L 1,000" and prod["precio"] <= 1000:
                continue

            # Determinar estado y tag
            if prod["stock"] == 0:
                estado = "❌ Sin stock"
                tag = "critical"
            elif prod["stock"] < 5:
                estado = "⚠️ Crítico"
                tag = "critical"
            elif prod["stock"] < 10:
                estado = "⚠️ Bajo"
                tag = "warning"
            elif prod["stock"] < 50:
                estado = "✅ Normal"
                tag = "normal"
            else:
                estado = "✅ Disponible"
                tag = "good"

            # Insertar en tree
            self.tree.insert(
                "",
                "end",
                iid=str(prod["id"]),
                values=(
                    prod["codigo"],
                    prod["nombre"],
                    prod["categoria_nombre"],
                    f"L {prod['precio']:.2f}",
                    prod["stock"],
                    estado,
                ),
                tags=(tag,)
            )

        # Configurar tags de color
        self.tree.tag_configure("critical", background="#ffebee", foreground="#c62828")
        self.tree.tag_configure("warning", background="#fff3e0", foreground="#e65100")
        self.tree.tag_configure("normal", background="#e8f5e9", foreground="#2e7d32")
        self.tree.tag_configure("good", background="#ffffff", foreground="#424242")

        self._sync_initial_selection()

    def _sync_initial_selection(self):
        """Sincroniza la selección inicial"""
        children = self.tree.get_children()
        if not children:
            self.selected_product = None
            self._render_product_detail(None)
            return
        
        current = self.tree.selection()
        if current:
            self._on_product_selected()
            return
        
        self.tree.selection_set(children[0])
        self.tree.focus(children[0])
        self._on_product_selected()

    def _get_selected_product(self):
        """Obtiene el producto seleccionado"""
        selected = self.tree.selection()
        if not selected:
            return None
        return self.product_lookup.get(str(selected[0]))

    def _on_product_selected(self, event=None):
        """Maneja la selección de producto"""
        self.selected_product = self._get_selected_product()
        self._render_product_detail(self.selected_product)

    def _render_product_detail(self, product):
        """Renderiza el detalle del producto"""
        if not product:
            self.detail_name_var.set("Seleccione un producto")
            self.detail_price_var.set("L 0.00")
            self.detail_stock_var.set("Stock: 0")
            self.detail_category_var.set("Categoría: Sin categoría")
            self.detail_code_var.set("Código: -")
            self.detail_status_var.set("Disponible para explorar")
            self.detail_description_var.set("Aquí verás la descripción completa, disponibilidad y contexto comercial del producto.")
            self.image_label.configure(text="🖼️\nSin imagen\nPreview comercial")
            return

        # Determinar estado
        if product["stock"] == 0:
            status = "❌ Sin stock"
        elif product["stock"] < 10:
            status = "⚠️ Stock bajo"
        else:
            status = "✅ Disponible"
        
        # Actualizar variables
        self.detail_name_var.set(product["nombre"])
        self.detail_price_var.set(format_hnl(product["precio"]))
        self.detail_stock_var.set(f"📦 Stock: {product['stock']} unidades")
        self.detail_category_var.set(f"📂 Categoría: {product['categoria_nombre']} | 🏷️ Marca: {product['marca_nombre']}")
        self.detail_code_var.set(f"🔢 Código: {product['codigo']}")
        self.detail_status_var.set(status)
        self.detail_description_var.set(product["descripcion"] or "Sin descripción registrada.")
        
        # Placeholder de imagen
        self.image_label.configure(text=f"{product['nombre'][:2].upper()}\n{product['categoria_nombre']}")

    def _open_detail_modal(self):
        """Abre modal con detalle completo"""
        product = self.selected_product or self._get_selected_product()
        if not product:
            return
        
        modal = tk.Toplevel(self.window)
        modal.title(f"📋 Detalle completo - {product['nombre']}")
        modal.transient(self.window)
        modal.grab_set()
        modal.geometry("650x550")
        modal.resizable(False, False)
        
        # Centrar
        modal.update_idletasks()
        x = (modal.winfo_screenwidth() // 2) - 325
        y = (modal.winfo_screenheight() // 2) - 275
        modal.geometry(f"+{x}+{y}")
        
        wrapper = ttk.Frame(modal, padding=20)
        wrapper.pack(fill="both", expand=True)
        wrapper.columnconfigure(0, weight=1)
        
        # Header
        ttk.Label(wrapper, text=product["nombre"], style="CatalogTitle.TLabel", wraplength=560).grid(row=0, column=0, sticky="w")
        ttk.Label(wrapper, text=format_hnl(product["precio"]), style="CatalogPrice.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        
        # Separador
        ttk.Separator(wrapper, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(15, 15))
        
        # Información
        info = ttk.Frame(wrapper)
        info.grid(row=3, column=0, sticky="ew")
        info.columnconfigure(0, weight=1)
        info.columnconfigure(1, weight=1)
        
        ttk.Label(info, text=f"Código:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        ttk.Label(info, text=product["codigo"]).grid(row=0, column=1, sticky="w", pady=5)
        
        ttk.Label(info, text=f"Categoría:", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(info, text=product["categoria_nombre"]).grid(row=1, column=1, sticky="w", pady=5)
        
        ttk.Label(info, text=f"Marca:", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=5)
        ttk.Label(info, text=product["marca_nombre"]).grid(row=2, column=1, sticky="w", pady=5)
        
        ttk.Label(info, text=f"Stock:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=5)
        ttk.Label(info, text=f"{product['stock']} unidades").grid(row=3, column=1, sticky="w", pady=5)
        
        ttk.Label(info, text=f"Estado:", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", pady=5)
        status_text = "Disponible" if product["stock"] > 0 else "Agotado"
        ttk.Label(info, text=status_text, foreground="#28a745" if product["stock"] > 0 else "#dc3545").grid(row=4, column=1, sticky="w", pady=5)
        
        # Descripción
        ttk.Label(wrapper, text="📝 Descripción:", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(15, 5))
        desc_frame = ttk.Frame(wrapper, relief="solid", borderwidth=1)
        desc_frame.grid(row=5, column=0, sticky="ew", pady=(0, 15))
        desc_frame.columnconfigure(0, weight=1)
        
        desc_text = tk.Text(desc_frame, height=6, wrap=tk.WORD, font=("Segoe UI", 10), padx=10, pady=10)
        desc_text.insert("1.0", product["descripcion"] or "Sin descripción registrada.")
        desc_text.config(state="disabled")
        desc_text.grid(row=0, column=0, sticky="nsew")
        
        # Botón
        ttk.Button(
            wrapper,
            text="➕ Agregar al carrito",
            style="Success.TButton",
            command=lambda: [self._add_and_continue(), modal.destroy()]
        ).grid(row=6, column=0, sticky="ew", pady=(10, 0))

    def _add_selected(self):
        """Agrega el producto seleccionado"""
        product = self.selected_product or self._get_selected_product()
        if not product:
            messagebox.showwarning("Advertencia", "Seleccione un producto", parent=self.window)
            return False

        if product["stock"] == 0:
            messagebox.showerror("Sin stock", "Este producto no tiene inventario disponible", parent=self.window)
            return False

        # Obtener descuento
        discount_idx = self.discount_combo.current()
        discount_pct = 0.0
        discount_name = "Sin descuento"

        if discount_idx > 0:
            try:
                disc_text = self.discount_combo.get()
                discount_name = disc_text.split(" - ")[0]
                discount_pct = float(disc_text.split(" - ")[1].replace("%", "")) / 100
            except Exception:
                pass

        # Llamar callback
        self.callback(
            product["id"],
            self.qty_var.get(),
            discount_pct,
            discount_name,
        )
        return True

    def _add_and_continue(self):
        """Agrega producto y mantiene ventana abierta"""
        if self._add_selected():
            self.qty_var.set(1)
            self.discount_combo.set("Sin descuento")
            self._show_notification("✅ Producto agregado al carrito")

    def _add_and_close(self):
        """Agrega producto y cierra ventana"""
        if self._add_selected():
            self.window.destroy()

    def _show_notification(self, message):
        """Muestra notificación temporal"""
        notif = tk.Toplevel(self.window)
        notif.overrideredirect(True)
        notif.attributes('-topmost', True)
        
        x = self.window.winfo_pointerx() - 150
        y = self.window.winfo_pointery() - 50
        notif.geometry(f"300x40+{x}+{y}")

        frame = ttk.Frame(notif, relief="solid", borderwidth=1, padding="10")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=message, font=("Segoe UI", 10)).pack()
        
        notif.after(1500, notif.destroy)


class UnifiedPOSFrame(ttk.Frame):
    """Vista profesional de POS con modal de búsqueda"""
    
    def __init__(self, parent, app, initial_sale_mode="NORMAL", workspace_variant="retail"):
        super().__init__(parent, padding="12")
        self.app = app
        self.db = app.db
        self.workspace_variant = workspace_variant
        
        # Repositorios y casos de uso
        self.sale_repository = SaleRepository(self.db)
        self.receipt_service = ReceiptService(self.db.get_config)
        self.load_pos_context_use_case = LoadPOSContext(self.sale_repository)
        self.create_pos_sale_use_case = CreatePOSSale(self.sale_repository, self.receipt_service)
        
        # Variables de estado
        self.cart = {}
        self.product_index = {}
        self.discount_data = {}
        self.discount_by_type = {}
        self.client_data = {}
        self.selected_client_id = None
        self.selected_client_is_wholesale = False
        self.pending_sale = None
        self.preview_window = None
        self.summary_window = None
        self.checkout_mode = tk.StringVar(value="cart")
        self.processing_job = None
        self.last_receipt_html = ""
        self.last_sale_result = None
        
        # Variables de control
        self.sale_mode_var = tk.StringVar(value=initial_sale_mode)
        self.search_var = tk.StringVar()
        self.discount_var = tk.StringVar(value="Sin descuento")
        self.client_var = tk.StringVar(value="Cliente General")
        self.payment_method_var = tk.StringVar(value="EFECTIVO")
        self.total_var = tk.DoubleVar(value=0.0)
        self.total_display_var = tk.StringVar(value=format_hnl(0))
        self.monto_pagado_var = tk.StringVar(value="0.00")
        self.vuelto_var = tk.DoubleVar(value=0.0)
        self.vuelto_display_var = tk.StringVar(value=format_hnl(0))
        self.status_var = tk.StringVar(value="✅ Sistema listo")
        self.cart_items_var = tk.StringVar(value="0 productos")
        self.selected_cart_name_var = tk.StringVar(value="Seleccione un producto")
        
        # Configurar estilos profesionales
        self._configure_styles()
        
        # Construir interfaz
        self._build_ui()
        
        # Cargar datos
        self.load_pos_context()
        self.update_cart_display()
        
        # Atajos de teclado
        self.master.bind("<F1>", lambda e: self.open_product_search())
        self.master.bind("<F2>", lambda e: self.open_payment_modal())
        self.master.bind("<F3>", lambda e: self.clear_cart())

    def _parent_window(self):
        return self.winfo_toplevel()

    def _show_info(self, title, text, parent=None):
        messagebox.showinfo(title, text, parent=parent or self._parent_window())

    def _show_warning(self, title, text, parent=None):
        messagebox.showwarning(title, text, parent=parent or self._parent_window())

    def _show_error(self, title, text, parent=None):
        messagebox.showerror(title, text, parent=parent or self._parent_window())

    def _ask_yes_no(self, title, text, parent=None):
        return messagebox.askyesno(title, text, parent=parent or self._parent_window())
    
    def _configure_styles(self):
        """Configura estilos profesionales tipo Microsoft Dynamics"""
        style = ttk.Style()
        
        # Estilos base
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=PALETTE.get("black", "#0f172a"))
        style.configure("Subheader.TLabel", font=("Segoe UI", 11), foreground=PALETTE.get("gray_text", "#475569"))
        style.configure("Metric.TLabel", font=("Segoe UI", 10, "bold"), foreground=PALETTE.get("blue_dark", "#1E2A44"))
        style.configure("MetricValue.TLabel", font=("Segoe UI", 24, "bold"), foreground=PALETTE.get("blue_dark", "#1E2A44"))
        style.configure("Card.TLabelframe", relief="solid", borderwidth=1, padding=10)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground=PALETTE.get("blue_dark", "#1E2A44"))
        
        # Botones
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        
    def _build_ui(self):
        """Construye interfaz profesional"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header profesional
        header = ttk.Frame(self, padding="15")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(1, weight=1)
        
        # Título y estado
        title_frame = ttk.Frame(header)
        title_frame.grid(row=0, column=0, sticky="w")
        
        ttk.Label(
            title_frame,
            text="🏪 PUNTO DE VENTA PROFESIONAL",
            style="Header.TLabel"
        ).pack(anchor="w")
        
        ttk.Label(
            title_frame,
            textvariable=self.status_var,
            style="Subheader.TLabel"
        ).pack(anchor="w", pady=(5, 0))
        
        # Métricas rápidas
        metrics = ttk.Frame(header)
        metrics.grid(row=0, column=2, sticky="e")
        
        self._create_metric_card(metrics, "Total carrito", self.total_display_var, 0)
        self._create_metric_card(metrics, "Items", self.cart_items_var, 1)
        
        # Contenedor principal de etapas
        self.stage_container = ttk.Frame(self)
        self.stage_container.grid(row=1, column=0, sticky="nsew")
        self.stage_container.grid_columnconfigure(0, weight=1)
        self.stage_container.grid_rowconfigure(0, weight=1)

        # Vista principal del POS
        self.sales_stage = ttk.Frame(self.stage_container)
        self.sales_stage.grid(row=0, column=0, sticky="nsew")
        self.sales_stage.grid_columnconfigure(0, weight=1)
        self.sales_stage.grid_rowconfigure(0, weight=1)
        self.sales_stage.grid_rowconfigure(1, weight=0)

        # Panel principal con dos columnas
        main_panel = ttk.Frame(self.sales_stage)
        main_panel.grid(row=0, column=0, sticky="nsew")
        main_panel.grid_columnconfigure(0, weight=2)
        main_panel.grid_columnconfigure(1, weight=1)
        main_panel.grid_rowconfigure(0, weight=1)
        
        # Panel izquierdo - Carrito
        left_panel = ttk.LabelFrame(main_panel, text="🛒 CARRITO DE COMPRAS", style="Card.TLabelframe")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_panel.grid_rowconfigure(0, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)
        
        self._build_cart_ui(left_panel)
        
        # Panel derecho - Acciones
        right_panel = ttk.Frame(main_panel)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        
        self._build_actions_ui(right_panel)
        
        # Botones de acción rápida
        quick_actions = ttk.Frame(self.sales_stage)
        quick_actions.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        
        ttk.Button(
            quick_actions,
            text="🔍 Buscar producto (F1)",
            command=self.open_product_search,
            style="Primary.TButton"
        ).pack(side="left", padx=5)
        
        ttk.Button(
            quick_actions,
            text="💳 Cobrar (F2)",
            command=self.open_payment_modal,
            style="Success.TButton"
        ).pack(side="left", padx=5)
        
        ttk.Button(
            quick_actions,
            text="🗑 Limpiar carrito (F3)",
            command=self.clear_cart,
            style="Danger.TButton"
        ).pack(side="left", padx=5)

        # Vista workflow de pago/confirmación/éxito
        self.checkout_stage = ttk.Frame(self.stage_container, padding=(0, 6, 0, 0))
        self.checkout_stage.grid(row=0, column=0, sticky="nsew")
        self.checkout_stage.grid_columnconfigure(0, weight=1)
        self.checkout_stage.grid_rowconfigure(1, weight=1)

        self.workflow_title_var = tk.StringVar(value="Workflow de Venta")
        self.workflow_subtitle_var = tk.StringVar(value="Completa el cobro y confirma la venta sin perder visibilidad.")
        self.workflow_status_var = tk.StringVar(value="Paso 1 de 4")
        self.workflow_step_labels = ("Productos", "Pago", "Confirmación", "Recibo")

        workflow_header = ttk.Frame(self.checkout_stage, padding=(6, 0, 6, 12))
        workflow_header.grid(row=0, column=0, sticky="ew")
        workflow_header.columnconfigure(0, weight=1)
        ttk.Label(workflow_header, textvariable=self.workflow_title_var, style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(workflow_header, textvariable=self.workflow_subtitle_var, style="Subheader.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(workflow_header, textvariable=self.workflow_status_var, style="Metric.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")

        self.progress_holder = ttk.Frame(self.checkout_stage)
        self.progress_holder.grid(row=1, column=0, sticky="nsew")
        self.progress_holder.grid_columnconfigure(0, weight=1)
        self.progress_holder.grid_rowconfigure(1, weight=1)

        self.step_indicator_frame = ttk.Frame(self.progress_holder)
        self.step_indicator_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for idx in range(4):
            self.step_indicator_frame.columnconfigure(idx, weight=1)
        self.step_indicator_labels = []
        for idx, label in enumerate(self.workflow_step_labels):
            var = tk.StringVar(value=f"{idx + 1}. {label}")
            widget = ttk.Label(self.step_indicator_frame, textvariable=var, style="Subheader.TLabel", anchor="center")
            widget.grid(row=0, column=idx, sticky="ew", padx=4)
            self.step_indicator_labels.append((var, widget))

        self.workflow_progress = ttk.Progressbar(self.progress_holder, mode="determinate", maximum=100)
        self.workflow_progress.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        workflow_body_shell = ttk.Frame(self.progress_holder)
        workflow_body_shell.grid(row=1, column=0, sticky="nsew")
        workflow_body_shell.grid_columnconfigure(0, weight=1)
        workflow_body_shell.grid_rowconfigure(0, weight=1)

        self.workflow_canvas = tk.Canvas(
            workflow_body_shell,
            highlightthickness=0,
            bg=PALETTE.get("surface_alt", PALETTE.get("white", "#ffffff")),
        )
        self.workflow_scrollbar = ttk.Scrollbar(workflow_body_shell, orient="vertical", command=self.workflow_canvas.yview)
        self.workflow_canvas.configure(yscrollcommand=self.workflow_scrollbar.set)
        self.workflow_canvas.grid(row=0, column=0, sticky="nsew")
        self.workflow_scrollbar.grid(row=0, column=1, sticky="ns")

        self.workflow_content = ttk.Frame(self.workflow_canvas, padding=10)
        self.workflow_content.columnconfigure(0, weight=1)
        self.workflow_content_id = self.workflow_canvas.create_window((0, 0), window=self.workflow_content, anchor="nw")
        self.workflow_content.bind(
            "<Configure>",
            lambda e: self.workflow_canvas.configure(scrollregion=self.workflow_canvas.bbox("all")),
        )
        self.workflow_canvas.bind(
            "<Configure>",
            lambda e: self.workflow_canvas.itemconfigure(self.workflow_content_id, width=e.width),
        )
        self.workflow_canvas.bind("<MouseWheel>", self._on_workflow_mousewheel)
        self.checkout_stage.grid_remove()
    
    def _create_metric_card(self, parent, label, variable, column):
        """Crea tarjeta de métrica"""
        card = ttk.Frame(parent, relief="solid", borderwidth=1, padding="10")
        card.grid(row=0, column=column, padx=5)
        
        ttk.Label(card, text=label, style="Metric.TLabel").pack()
        ttk.Label(card, textvariable=variable, style="MetricValue.TLabel").pack()

    def _on_workflow_mousewheel(self, event):
        delta = -1 * int(event.delta / 120) if event.delta else 0
        if delta:
            self.workflow_canvas.yview_scroll(delta, "units")

    def _show_sales_stage(self):
        self.checkout_stage.grid_remove()
        self.sales_stage.grid()
        self.checkout_mode.set("cart")
        self.workflow_progress.stop()

    def _show_checkout_stage(self):
        self.sales_stage.grid_remove()
        self.checkout_stage.grid()

    def _set_workflow_step(self, current_step: int, title: str, subtitle: str):
        step_names = self.workflow_step_labels
        self.workflow_title_var.set(title)
        self.workflow_subtitle_var.set(subtitle)
        self.workflow_status_var.set(f"Paso {current_step} de {len(step_names)}")
        self.workflow_progress.configure(mode="determinate", value=(current_step / len(step_names)) * 100)
        for idx, (var, widget) in enumerate(self.step_indicator_labels, start=1):
            prefix = "✓" if idx < current_step else "●" if idx == current_step else str(idx)
            var.set(f"{prefix} {step_names[idx - 1]}")
            widget.configure(style="Metric.TLabel" if idx <= current_step else "Subheader.TLabel")

    def _clear_workflow_content(self):
        for child in self.workflow_content.winfo_children():
            child.destroy()
        self.workflow_canvas.yview_moveto(0)

    def _render_workflow_payment_step(self):
        self.checkout_mode.set("payment")
        self._show_checkout_stage()
        self._set_workflow_step(
            2,
            "Cobro de la venta",
            "Revisa el resumen, completa los datos de pago y avanza a la confirmación.",
        )
        self._clear_workflow_content()
        self.pending_sale = self._build_sale_snapshot()

        shell = ttk.Frame(self.workflow_content)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=3)
        shell.columnconfigure(1, weight=2)

        sale_card = ttk.LabelFrame(shell, text="Resumen de productos", style="Card.TLabelframe")
        sale_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sale_card.columnconfigure(0, weight=1)
        sale_card.rowconfigure(0, weight=1)

        columns = ("producto", "cantidad", "precio", "desc", "subtotal")
        tree = ttk.Treeview(sale_card, columns=columns, show="headings", height=12)
        for col, text, width, anchor in (
            ("producto", "Producto", 260, "w"),
            ("cantidad", "Cant.", 70, "center"),
            ("precio", "Precio", 90, "e"),
            ("desc", "Desc.", 70, "center"),
            ("subtotal", "Subtotal", 110, "e"),
        ):
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor)
        y_scroll = ttk.Scrollbar(sale_card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=y_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")

        for item in self.pending_sale["cart_snapshot"].values():
            pct = float(item.get("descuento_porcentaje", 0))
            subtotal = float(item["precio_unitario"]) * int(item["cantidad"]) * (1 - pct)
            tree.insert("", "end", values=(item["nombre"], int(item["cantidad"]), format_hnl(item["precio_unitario"]), f"{int(round(pct * 100))}%" if pct else "-", format_hnl(subtotal)))

        summary = ttk.LabelFrame(shell, text="Cobro y totales", style="Card.TLabelframe")
        summary.grid(row=0, column=1, sticky="nsew")
        summary.columnconfigure(1, weight=1)

        client_text = self.client_var.get() or "Cliente General"
        ttk.Label(summary, text="Cliente").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(summary, text=client_text, style="Metric.TLabel").grid(row=0, column=1, sticky="w", pady=(0, 8))

        ttk.Label(summary, text="Modo de venta").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(summary, text="Mayorista" if self.sale_mode_var.get() == "ESPECIAL" else "Normal", style="Metric.TLabel").grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(summary, text="Subtotal / Total").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Label(summary, text=self.total_display_var.get(), style="MetricValue.TLabel").grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(summary, text="Método de pago").grid(row=3, column=0, sticky="w", pady=(12, 4))
        payment_combo = ttk.Combobox(
            summary,
            textvariable=self.payment_method_var,
            values=("EFECTIVO", "TARJETA", "TRANSFERENCIA", "CREDITO"),
            state="readonly",
        )
        payment_combo.grid(row=3, column=1, sticky="ew", pady=(12, 4))

        ttk.Label(summary, text="Monto recibido").grid(row=4, column=0, sticky="w", pady=4)
        amount_entry = ttk.Entry(summary, textvariable=self.monto_pagado_var, font=("Segoe UI", 12))
        amount_entry.grid(row=4, column=1, sticky="ew", pady=4)
        amount_entry.bind("<KeyRelease>", self.calculate_change)

        ttk.Label(summary, text="Vuelto").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Label(summary, textvariable=self.vuelto_display_var, style="MetricValue.TLabel").grid(row=5, column=1, sticky="w", pady=4)

        preview_model = self._build_preview_model(self.pending_sale)
        summary_rows = preview_model["summary_rows"]
        ttk.Separator(summary, orient="horizontal").grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)
        for idx, (label, value) in enumerate(summary_rows, start=7):
            ttk.Label(summary, text=label).grid(row=idx, column=0, sticky="w", pady=2)
            ttk.Label(summary, text=format_hnl(value)).grid(row=idx, column=1, sticky="e", pady=2)

        actions = ttk.Frame(self.workflow_content)
        actions.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(actions, text="← Volver al carrito", style="Danger.TButton", command=self._show_sales_stage).pack(side="left")
        ttk.Button(actions, text="Cancelar venta", command=self._close_preview_window).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Continuar a confirmación →", style="Success.TButton", command=self._go_to_confirmation_step).pack(side="right")

    def _go_to_confirmation_step(self):
        total = self.total_var.get()
        pagado = self._parse_float(self.monto_pagado_var.get())
        if total <= 0:
            self._show_warning("Advertencia", "Total inválido")
            return
        if pagado < total:
            self._show_warning("Pago incompleto", f"Faltan L {total - pagado:,.2f}")
            return
        self.pending_sale = self._build_sale_snapshot()
        self._render_confirmation_step()

    def _render_confirmation_step(self):
        self.checkout_mode.set("confirmation")
        self._show_checkout_stage()
        self._set_workflow_step(
            3,
            "Confirmación final",
            "Verifica el recibo, los totales y confirma la venta cuando todo esté correcto.",
        )
        self._clear_workflow_content()

        shell = ttk.Frame(self.workflow_content)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=3)
        shell.columnconfigure(1, weight=2)

        sale_card = ttk.LabelFrame(shell, text="Resumen de compra", style="Card.TLabelframe")
        sale_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sale_card.columnconfigure(0, weight=1)
        sale_card.rowconfigure(0, weight=1)

        columns = ("producto", "cantidad", "precio", "desc", "subtotal")
        tree = ttk.Treeview(sale_card, columns=columns, show="headings", height=12)
        for col, text, width, anchor in (
            ("producto", "Producto", 260, "w"),
            ("cantidad", "Cant.", 70, "center"),
            ("precio", "Precio", 90, "e"),
            ("desc", "Desc.", 70, "center"),
            ("subtotal", "Subtotal", 110, "e"),
        ):
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor)
        y_scroll = ttk.Scrollbar(sale_card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=y_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")

        for item in self.pending_sale["cart_snapshot"].values():
            pct = float(item.get("descuento_porcentaje", 0))
            subtotal = float(item["precio_unitario"]) * int(item["cantidad"]) * (1 - pct)
            tree.insert("", "end", values=(item["nombre"], int(item["cantidad"]), format_hnl(item["precio_unitario"]), f"{int(round(pct * 100))}%" if pct else "-", format_hnl(subtotal)))

        meta = ttk.Frame(sale_card)
        meta.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(meta, text=f"Cliente: {self.client_var.get()}", style="Metric.TLabel").pack(anchor="w")
        ttk.Label(meta, text=f"Método: {self.payment_method_var.get()} | Recibido: {format_hnl(self.pending_sale['pagado'])} | Vuelto: {format_hnl(self.pending_sale['vuelto'])}").pack(anchor="w", pady=(4, 0))

        preview_card = ttk.LabelFrame(shell, text="Vista previa del recibo", style="Card.TLabelframe")
        preview_card.grid(row=0, column=1, sticky="nsew")
        preview_card.columnconfigure(0, weight=1)
        preview_card.rowconfigure(0, weight=1)
        preview_frame = ttk.Frame(preview_card)
        preview_frame.grid(row=0, column=0, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        self._render_receipt_preview(preview_frame, self.pending_sale)

        actions = ttk.Frame(self.workflow_content)
        actions.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(actions, text="← Volver a pago", style="Danger.TButton", command=self._render_workflow_payment_step).pack(side="left")
        ttk.Button(actions, text="Cancelar", command=self._close_preview_window).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Procesar venta", style="Success.TButton", command=self._start_processing_sale).pack(side="right")

    def _start_processing_sale(self):
        self.checkout_mode.set("processing")
        self._show_checkout_stage()
        self._set_workflow_step(
            4,
            "Procesando venta",
            "Estamos guardando la venta, actualizando inventario y generando el recibo.",
        )
        self._clear_workflow_content()
        self.workflow_progress.configure(mode="indeterminate")
        self.workflow_progress.start(12)

        card = ttk.LabelFrame(self.workflow_content, text="Procesando", style="Card.TLabelframe", padding=24)
        card.grid(row=0, column=0, sticky="ew")
        ttk.Label(card, text="Procesando venta...", style="Header.TLabel").pack(anchor="center")
        ttk.Label(card, text="Por favor espera mientras guardamos la transacción.", style="Subheader.TLabel").pack(anchor="center", pady=(8, 12))
        progress = ttk.Progressbar(card, mode="indeterminate")
        progress.pack(fill="x")
        progress.start(10)
        self.processing_job = self.after(350, lambda p=progress: self._complete_sale_processing(p))

    def _render_success_step(self, result):
        self.checkout_mode.set("success")
        self._show_checkout_stage()
        self._set_workflow_step(
            4,
            "Venta completada",
            "La venta se guardó correctamente y el recibo ya está disponible.",
        )
        self.workflow_progress.configure(mode="determinate", value=100)
        self._clear_workflow_content()

        card = ttk.LabelFrame(self.workflow_content, text="Éxito", style="Card.TLabelframe", padding=24)
        card.grid(row=0, column=0, sticky="ew")
        ttk.Label(card, text="✓ Venta autoguardada correctamente", style="Header.TLabel").pack(anchor="center")
        ttk.Label(card, text=f"Venta #{result.sale_id} | Total {format_hnl(result.total)}", style="Subheader.TLabel").pack(anchor="center", pady=(8, 6))
        ttk.Label(card, text="Inventario actualizado, recibo generado y flujo completado con éxito.", style="Subheader.TLabel").pack(anchor="center")

        actions = ttk.Frame(self.workflow_content)
        actions.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        ttk.Button(actions, text="Abrir recibo otra vez", command=lambda: self.last_receipt_html and self.print_receipt(self.last_receipt_html)).pack(side="left")
        ttk.Button(actions, text="Nueva venta", style="Success.TButton", command=self._finish_checkout_success).pack(side="right")

    def _finish_checkout_success(self):
        self.pending_sale = None
        self.last_sale_result = None
        self._show_sales_stage()
    
    def _build_cart_ui(self, parent):
        """Construye interfaz del carrito"""
        # Treeview profesional
        columns = ("Producto", "Cantidad", "Precio", "Descuento", "Subtotal")
        self.cart_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=12
        )
        
        # Configurar columnas
        self.cart_tree.heading("Producto", text="Producto")
        self.cart_tree.heading("Cantidad", text="Cant.")
        self.cart_tree.heading("Precio", text="Precio Unit.")
        self.cart_tree.heading("Descuento", text="Desc.")
        self.cart_tree.heading("Subtotal", text="Subtotal")
        
        self.cart_tree.column("Producto", width=220, anchor="w")
        self.cart_tree.column("Cantidad", width=80, anchor="center")
        self.cart_tree.column("Precio", width=100, anchor="e")
        self.cart_tree.column("Descuento", width=80, anchor="center")
        self.cart_tree.column("Subtotal", width=120, anchor="e")
        
        # Scrollbar
        y_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=y_scroll.set)
        
        self.cart_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        
        # Eventos
        self.cart_tree.bind("<<TreeviewSelect>>", self.on_cart_select)
        
        # Editor de cantidad
        editor_frame = ttk.LabelFrame(parent, text="✏️ Editar producto", padding="10")
        editor_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        ttk.Label(editor_frame, text="Producto:").grid(row=0, column=0, sticky="w")
        ttk.Label(editor_frame, textvariable=self.selected_cart_name_var).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(editor_frame, text="Cantidad:").grid(row=1, column=0, sticky="w", pady=5)
        self.qty_editor = ttk.Spinbox(editor_frame, from_=1, to=999, width=10)
        self.qty_editor.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.qty_editor.bind("<KeyRelease>", self.update_cart_item_quantity)
        
        ttk.Button(
            editor_frame,
            text="Actualizar",
            command=self.update_cart_item
        ).grid(row=1, column=2, padx=5)
        
        ttk.Button(
            editor_frame,
            text="Eliminar",
            command=self.remove_from_cart
        ).grid(row=1, column=3, padx=5)
    
    def _build_actions_ui(self, parent):
        """Construye panel de acciones"""
        # Selector de cliente
        client_frame = ttk.LabelFrame(parent, text="👤 Cliente", padding="10")
        client_frame.pack(fill="x", pady=(0, 10))
        
        self.client_combo = ttk.Combobox(
            client_frame,
            textvariable=self.client_var,
            state="readonly",
            font=("Segoe UI", 10)
        )
        self.client_combo.pack(fill="x")
        self.client_combo.bind("<<ComboboxSelected>>", self.on_client_select)
        
        ttk.Button(
            client_frame,
            text="🔄 Refrescar clientes",
            command=self.load_clients
        ).pack(fill="x", pady=(5, 0))
        
        # Selector de modo
        mode_frame = ttk.LabelFrame(parent, text="⚙️ Modo de venta", padding="10")
        mode_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Radiobutton(
            mode_frame,
            text="Normal",
            value="NORMAL",
            variable=self.sale_mode_var,
            command=self.on_sale_mode_change
        ).pack(anchor="w")
        
        ttk.Radiobutton(
            mode_frame,
            text="Especial (Mayorista)",
            value="ESPECIAL",
            variable=self.sale_mode_var,
            command=self.on_sale_mode_change
        ).pack(anchor="w", pady=(5, 0))
        
        # Panel de cobro
        payment_frame = ttk.LabelFrame(parent, text="💰 Cobro", padding="10")
        payment_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(payment_frame, text="Método de pago:").pack(anchor="w")
        self.payment_combo = ttk.Combobox(
            payment_frame,
            textvariable=self.payment_method_var,
            values=("EFECTIVO", "TARJETA", "TRANSFERENCIA", "CREDITO"),
            state="readonly"
        )
        self.payment_combo.pack(fill="x", pady=(5, 10))
        
        ttk.Label(payment_frame, text="Monto recibido:").pack(anchor="w")
        self.monto_entry = ttk.Entry(payment_frame, textvariable=self.monto_pagado_var, font=("Segoe UI", 11))
        self.monto_entry.pack(fill="x", pady=(5, 5))
        self.monto_entry.bind("<KeyRelease>", self.calculate_change)
        
        ttk.Label(payment_frame, text="Cambio:").pack(anchor="w")
        ttk.Label(
            payment_frame,
            textvariable=self.vuelto_display_var,
            font=("Segoe UI", 16, "bold"),
            foreground=PALETTE.get("success", "#28a745")
        ).pack(anchor="w", pady=(5, 0))
        
        # Botón finalizar
        ttk.Button(
            payment_frame,
            text="✅ FINALIZAR VENTA",
            command=self.open_payment_modal,
            style="Success.TButton"
        ).pack(fill="x", pady=(10, 0))
    
    def open_product_search(self):
        """Abre ventana modal de búsqueda de productos"""
        if not self.product_index:
            self._show_warning("Advertencia", "No hay productos cargados")
            return

        discount_options = ["Sin descuento"]
        for index in sorted(self.discount_data.keys()):
            discount = self.discount_data[index]
            if not discount.get("porcentaje"):
                continue
            discount_options.append(f"{discount['nombre']} - {int(round(discount['porcentaje'] * 100))}%")

        ProductSearchModal(
            self,
            self.add_product_from_modal,
            self.product_index,
            discount_options=discount_options,
        )
    
    def add_product_from_modal(self, product_id, quantity, discount_pct, discount_name):
        """Agrega producto desde el modal"""
        if product_id not in self.product_index:
            return
        
        product = self.product_index[product_id]
        
        # Verificar stock
        current_qty = self.cart.get(product_id, {}).get("cantidad", 0)
        if current_qty + quantity > product["stock"]:
            self._show_error(
                "Stock insuficiente",
                f"Solo hay {product['stock']} unidades disponibles"
            )
            return
        
        # Agregar al carrito
        if product_id in self.cart:
            self.cart[product_id]["cantidad"] += quantity
            if discount_pct > 0:
                self.cart[product_id]["descuento_porcentaje"] = discount_pct
                self.cart[product_id]["manual"] = True
                self.cart[product_id]["manual_label"] = discount_name
        else:
            self.cart[product_id] = {
                "producto_id": product_id,
                "nombre": product["nombre"],
                "cantidad": quantity,
                "precio_unitario": product["precio"],
                "descuento_porcentaje": discount_pct,
                "manual": discount_pct > 0,
                "manual_label": discount_name if discount_pct > 0 else "",
                "auto_label": ""
            }
        
        self.update_cart_display()
        self.status_var.set(f"✅ {quantity}x {product['nombre']} agregado al carrito")
        
        # Actualizar vista previa si está abierta
        if hasattr(self, 'preview_window') and self.preview_window:
            self.refresh_preview()
    
    def update_cart_display(self):
        """Actualiza visualización del carrito"""
        # Limpiar tree
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        total = 0.0
        for prod_id, item in self.cart.items():
            qty = item["cantidad"]
            price = item["precio_unitario"]
            pct = item.get("descuento_porcentaje", 0)
            subtotal = price * qty * (1 - pct)
            total += subtotal
            
            # Formatear descuento
            if pct > 0:
                desc_text = f"{int(pct*100)}%"
                if item.get("manual"):
                    desc_text += " (M)"
            else:
                desc_text = "-"
            
            self.cart_tree.insert(
                "",
                "end",
                iid=str(prod_id),
                values=(
                    item["nombre"],
                    qty,
                    f"L {price:.2f}",
                    desc_text,
                    f"L {subtotal:.2f}"
                )
            )
        
        # Actualizar totales
        self.total_var.set(total)
        self.total_display_var.set(f"L {total:,.2f}")
        
        # Actualizar contador
        if self.cart:
            units = sum(item["cantidad"] for item in self.cart.values())
            self.cart_items_var.set(f"{units} unidades")
        else:
            self.cart_items_var.set("0 productos")
        
        self.calculate_change()
    
    def on_cart_select(self, event):
        """Selecciona producto del carrito"""
        selected = self.cart_tree.selection()
        if selected:
            prod_id = int(selected[0])
            item = self.cart.get(prod_id)
            if item:
                self.selected_cart_name_var.set(item["nombre"])
                self.qty_editor.delete(0, tk.END)
                self.qty_editor.insert(0, str(item["cantidad"]))
                self.qty_editor.product_id = prod_id
    
    def update_cart_item_quantity(self, event=None):
        """Actualiza cantidad del item seleccionado"""
        if hasattr(self.qty_editor, 'product_id'):
            try:
                new_qty = int(self.qty_editor.get())
                if new_qty > 0:
                    self.update_cart_item()
            except:
                pass
    
    def update_cart_item(self):
        """Actualiza el item del carrito"""
        if not hasattr(self.qty_editor, 'product_id'):
            self._show_warning("Advertencia", "Seleccione un producto del carrito")
            return
        
        prod_id = self.qty_editor.product_id
        if prod_id not in self.cart:
            return
        
        try:
            new_qty = int(self.qty_editor.get())
            if new_qty <= 0:
                self.remove_from_cart()
                return
            
            product = self.product_index.get(prod_id)
            if product and new_qty > product["stock"]:
                self._show_error("Stock insuficiente", f"Solo hay {product['stock']} unidades")
                return
            
            self.cart[prod_id]["cantidad"] = new_qty
            self.update_cart_display()
            self.status_var.set(f"Cantidad actualizada")
            
        except ValueError:
            self._show_error("Error", "Cantidad inválida")
    
    def remove_from_cart(self):
        """Elimina producto del carrito"""
        selected = self.cart_tree.selection()
        if not selected:
            self._show_warning("Advertencia", "Seleccione un producto")
            return
        
        prod_id = int(selected[0])
        if prod_id in self.cart:
            del self.cart[prod_id]
            self.update_cart_display()
            self.status_var.set("Producto eliminado")
            
            if not self.cart:
                self.selected_cart_name_var.set("Seleccione un producto")
    
    def clear_cart(self):
        """Limpia todo el carrito"""
        if self.cart:
            if self._ask_yes_no("Confirmar", "¿Limpiar todo el carrito?"):
                self.cart.clear()
                self.update_cart_display()
                self.status_var.set("Carrito vaciado")
    
    def calculate_change(self, event=None):
        """Calcula el vuelto"""
        try:
            total = self.total_var.get()
            pagado = self._parse_float(self.monto_pagado_var.get())
            vuelto = max(0, pagado - total)
            self.vuelto_var.set(vuelto)
            self.vuelto_display_var.set(f"L {vuelto:,.2f}")
            
            if pagado >= total:
                self.status_var.set("✅ Pago completo - Listo para finalizar")
            else:
                faltante = total - pagado
                self.status_var.set(f"⚠️ Faltan L {faltante:,.2f}")
        except:
            pass

    def _get_receipt_client(self, client_id):
        if not client_id:
            return None
        try:
            return self.sale_repository.get_client_detail(int(client_id))
        except Exception:
            return None

    def _build_sale_snapshot(self):
        return {
            "venta_id": f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": self.total_var.get(),
            "pagado": self._parse_float(self.monto_pagado_var.get()),
            "vuelto": self.vuelto_var.get(),
            "cliente_id": self.selected_client_id,
            "metodo_pago": self.payment_method_var.get(),
            "modo": self.sale_mode_var.get(),
            "cart_snapshot": {pid: dict(item) for pid, item in self.cart.items()},
            "tax_included": True,
        }

    def _build_preview_model(self, snapshot=None):
        snapshot = snapshot or self.pending_sale or self._build_sale_snapshot()
        render_settings = load_receipt_render_settings(self.db.get_config)
        return build_receipt_view_model(
            venta_id=snapshot["venta_id"],
            fecha=snapshot["fecha"],
            items=self.receipt_service.build_receipt_items(snapshot["cart_snapshot"]),
            cliente=self._get_receipt_client(snapshot.get("cliente_id")),
            metodo_pago=snapshot.get("metodo_pago") or "NO_DEFINIDO",
            mode="ticket",
            empresa=render_settings["empresa"],
            number_to_words=self.number_to_words,
            tax_included=snapshot.get("tax_included", True),
            labels=render_settings["labels"],
            observaciones=render_settings["observaciones"],
            amount_received=snapshot.get("pagado"),
        )

    def _render_receipt_preview(self, parent, snapshot=None):
        for child in parent.winfo_children():
            child.destroy()
        model = self._build_preview_model(snapshot)
        wrapper = ttk.Frame(parent)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.columnconfigure(0, weight=1)

        company = model["company"]
        labels = model["labels"]
        ttk.Label(wrapper, text=company["nombre"], style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(wrapper, text=f"R.T.N.: {company['rtn']}", style="Subheader.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(wrapper, text=f"Fecha: {model['fecha']} | Factura: {model['venta_id']}", style="Subheader.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 10))

        cols = ("cantidad", "codigo", "producto", "precio", "subtotal")
        tree = ttk.Treeview(wrapper, columns=cols, show="headings", height=8)
        headings = {"cantidad": "Cant.", "codigo": "Código", "producto": "Producto", "precio": "P. Unit.", "subtotal": "Subtotal"}
        widths = {"cantidad": 60, "codigo": 100, "producto": 210, "precio": 90, "subtotal": 100}
        for col in cols:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor="w" if col in {"codigo", "producto"} else "center" if col == "cantidad" else "e")
        for item in model["items"]:
            tree.insert("", "end", values=(int(item["cantidad"]), item["codigo"], item["producto"], format_hnl(item["precio_unitario"]), format_hnl(item["subtotal"])))
        tree.grid(row=3, column=0, sticky="ew")

        summary = ttk.LabelFrame(wrapper, text=labels["SUMMARY_HEADER"], padding=8)
        summary.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        for idx, (label, value) in enumerate(model["summary_rows"]):
            ttk.Label(summary, text=label).grid(row=idx, column=0, sticky="w")
            ttk.Label(summary, text=format_hnl(value)).grid(row=idx, column=1, sticky="e", padx=(24, 0))

        ttk.Label(wrapper, text=model["monto_letras"], style="Subheader.TLabel", wraplength=420).grid(row=5, column=0, sticky="w", pady=(10, 0))
        ttk.Label(wrapper, text=f"{labels['LABEL_OBSERVACIONES']} {model['observaciones']}", style="Subheader.TLabel", wraplength=420).grid(row=6, column=0, sticky="w", pady=(4, 0))

    def _open_checkout_summary(self):
        self.pending_sale = self._build_sale_snapshot()
        self._render_confirmation_step()

    def open_payment_modal(self):
        """Abre el paso interno de cobro"""
        if not self.cart:
            self._show_warning("Advertencia", "El carrito está vacío")
            return
        
        if self.total_var.get() <= 0:
            self._show_warning("Advertencia", "Total inválido")
            return

        self._render_workflow_payment_step()
    
    def _complete_sale_processing(self, progress_widget=None):
        if progress_widget and progress_widget.winfo_exists():
            progress_widget.stop()
        try:
            sale_snapshot = self.pending_sale or self._build_sale_snapshot()
            
            result = self.create_pos_sale_use_case.execute(
                sale_snapshot,
                usuario_id=self.app.current_user[0] if hasattr(self.app, 'current_user') else 1,
                preview_mode="ticket",
                number_to_words=self.number_to_words
            )

            self.workflow_progress.stop()
            self.cart.clear()
            self.update_cart_display()
            self.monto_pagado_var.set("0.00")
            self.last_receipt_html = result.receipt_html or ""
            self.last_sale_result = result

            notification_manager = getattr(self.app, "notification_manager", None)
            if notification_manager and hasattr(notification_manager, "notify_sale_success"):
                client_name = self.client_var.get().strip()
                if client_name == "Cliente General":
                    client_name = None
                notification_manager.notify_sale_success(
                    result.sale_id,
                    result.total,
                    cliente=client_name,
                )

            if result.receipt_html:
                self.print_receipt(result.receipt_html)

            self.load_products()
            self._render_success_step(result)
        except Exception as e:
            self.workflow_progress.stop()
            self._show_error("Error", f"No se pudo procesar la venta: {e}")
            self._render_confirmation_step()

    def process_sale(self):
        """Mantiene compatibilidad con atajos y consumidores internos."""
        self._start_processing_sale()
    
    def number_to_words(self, n):
        """Convierte número a palabras"""
        if n == 0:
            return "cero"
        unidades = ["", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
        decenas = ["", "diez", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
        centenas = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]
        
        if n < 10:
            return unidades[n]
        if n < 100:
            return f"{decenas[n // 10]} y {unidades[n % 10]}".strip() if n % 10 else decenas[n // 10]
        if n < 1000:
            return f"{centenas[n // 100]} {self.number_to_words(n % 100)}".strip() if n % 100 else centenas[n // 100]
        if n < 1000000:
            miles = n // 1000
            resto = n % 1000
            prefix = "mil" if miles == 1 else f"{self.number_to_words(miles)} mil"
            return f"{prefix} {self.number_to_words(resto)}".strip() if resto else prefix
        return str(n)
    
    def print_receipt(self, html_content):
        """Imprime recibo"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html_content)
            temp_path = f.name
        webbrowser.open(f"file://{temp_path}")
    
    def load_pos_context(self, load_products=True, load_clients=True, load_discounts=True):
        """Carga contexto del POS"""
        context = self.load_pos_context_use_case.execute(
            load_products=load_products,
            load_clients=load_clients,
            load_discounts=load_discounts
        )
        
        if load_products:
            self.product_index.clear()
            for prod in context.products:
                self.product_index[int(prod["id"])] = {
                    "id": int(prod["id"]),
                    "nombre": prod["nombre"],
                    "descripcion": prod.get("descripcion", ""),
                    "precio": float(prod.get("precio", 0)),
                    "stock": int(prod.get("stock", 0)),
                    "codigo_producto": str(prod.get("codigo_producto", "")),
                    "categoria_nombre": str(prod.get("categoria_nombre", "") or "Sin categoría"),
                    "marca_nombre": str(prod.get("marca_nombre", "") or "Sin marca"),
                }
        
        if load_clients:
            self.client_data = {"Cliente General": {"id": None, "mayorista": False}}
            client_list = ["Cliente General"]
            for client in context.clients:
                label = f"{client['apellido']}, {client['nombre']}"
                if client.get("mayorista"):
                    label += " (Mayorista)"
                client_list.append(label)
                self.client_data[label] = {
                    "id": client["id"],
                    "mayorista": bool(client.get("mayorista", False))
                }
            self.client_combo['values'] = client_list
            self.client_combo.current(0)

        if load_discounts:
            self.discount_data.clear()
            self.discount_by_type.clear()
            for idx, discount in enumerate(context.discounts, start=1):
                discount_record = {
                    "id": int(discount.get("id", idx)),
                    "nombre": str(discount.get("nombre", "Descuento")),
                    "tipo": str(discount.get("tipo", "")),
                    "porcentaje": float(discount.get("porcentaje", 0)),
                }
                self.discount_data[idx] = discount_record
                discount_type = discount_record["tipo"].strip().upper() or "GENERAL"
                self.discount_by_type.setdefault(discount_type, []).append(discount_record)
    
    def load_clients(self):
        """Recarga clientes"""
        self.load_pos_context(load_products=False, load_clients=True, load_discounts=False)
    
    def load_products(self):
        """Recarga productos"""
        self.load_pos_context(load_products=True, load_clients=False, load_discounts=False)
    
    def on_client_select(self, event):
        """Selecciona cliente"""
        selected = self.client_var.get()
        if selected in self.client_data:
            self.selected_client_id = self.client_data[selected]["id"]
            self.selected_client_is_wholesale = self.client_data[selected]["mayorista"]
            self.on_sale_mode_change()
    
    def on_sale_mode_change(self):
        """Cambia modo de venta"""
        wholesale = self.sale_mode_var.get() == "ESPECIAL" or self.selected_client_is_wholesale
        
        # Recalcular descuentos
        for prod_id in self.cart:
            item = self.cart[prod_id]
            if not item.get("manual"):
                qty = item["cantidad"]
                if wholesale and qty >= 12:
                    item["descuento_porcentaje"] = 0.15  # 15% mayorista
                    item["auto_label"] = "Mayorista"
                elif qty >= 12:
                    item["descuento_porcentaje"] = 0.10  # 10% por docena
                    item["auto_label"] = "Docena"
                else:
                    item["descuento_porcentaje"] = 0.0
                    item["auto_label"] = ""
        
        self.update_cart_display()
        self.status_var.set(f"Modo: {'Mayorista' if wholesale else 'Normal'}")
    
    def refresh_preview(self):
        """Refresca vista previa"""
        if not self.cart:
            self._close_preview_window()
            return
        if self.checkout_mode.get() == "payment":
            self._render_workflow_payment_step()
        elif self.checkout_mode.get() == "confirmation":
            self.pending_sale = self._build_sale_snapshot()
            self._render_confirmation_step()

    def _close_preview_window(self):
        """Sale del workflow interno y vuelve al carrito sin destruir el estado base del POS."""
        if self.processing_job:
            try:
                self.after_cancel(self.processing_job)
            except Exception:
                pass
            self.processing_job = None
        self.workflow_progress.stop()
        for attr in ("preview_window", "summary_window"):
            window = getattr(self, attr, None)
            if window and window.winfo_exists():
                window.destroy()
            setattr(self, attr, None)
        self.pending_sale = None
        self._show_sales_stage()
    
    def _parse_float(self, value):
        """Parsea valor a float"""
        try:
            return float(str(value).replace("L", "").replace(",", "").strip())
        except:
            return 0.0


class SalesFrame(UnifiedPOSFrame):
    """POS para ventas normales"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app, initial_sale_mode="NORMAL", workspace_variant="retail")


class WholesaleSalesFrame(UnifiedPOSFrame):
    """POS para ventas mayoristas"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app, initial_sale_mode="ESPECIAL", workspace_variant="wholesale")
