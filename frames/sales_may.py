"""
frames/wholesale_sales.py
Sistema de Ventas Mayoristas Profesional - Versión Corregida
"""

from tkinter import ttk, messagebox, Toplevel, filedialog, StringVar, IntVar
import tkinter as tk
from datetime import datetime
import random
import os
import json
from receipt_builder import build_receipt_html


class WholesaleSalesFrame(ttk.Frame):
    """Frame de ventas mayoristas con gestión profesional completa."""

    def __init__(self, parent, app):
        super().__init__(parent, padding="10")
        self.app = app
        self.db = app.db
        
        # Variables de estado
        self.cart = {}
        self.current_step = 1
        self.cliente_data = {}
        self.venta_id = None
        self.total_venta = 0.0
        self.venta_en_progreso = False
        self.discount_data = {}
        
        # Configurar estilos
        self.setup_styles()
        
        # Crear interfaz
        self.create_main_interface()
        
        # Cargar descuentos
        self.load_discounts()
        
    def setup_styles(self):
        """Configura estilos personalizados."""
        style = ttk.Style()
        style.configure("Success.TButton", foreground="#28a745", font=("Arial", 10, "bold"))
        style.configure("Danger.TButton", foreground="#dc3545", font=("Arial", 10, "bold"))
        style.configure("Primary.TButton", foreground="#007bff", font=("Arial", 10, "bold"))
        
    def create_main_interface(self):
        """Crea interfaz principal con 4 pasos."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ttk.Frame(self, relief="raised", padding="15")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(
            header,
            text="🏢 SISTEMA DE VENTAS MAYORISTAS",
            font=("Arial", 18, "bold"),
            foreground="#2c3e50"
        ).pack(side="left")
        
        self.step_label = ttk.Label(
            header,
            text="Paso 1/4: Selección de Productos",
            font=("Arial", 12),
            foreground="#3498db"
        )
        self.step_label.pack(side="right")
        
        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        
        # Crear tabs
        self.create_product_tab()
        self.create_client_tab()
        self.create_preview_tab()
        self.create_confirm_tab()
        
        # Deshabilitar tabs
        for i in range(1, 4):
            self.notebook.tab(i, state="disabled")
        
        # Footer
        footer = ttk.Frame(self, padding="10")
        footer.grid(row=2, column=0, sticky="ew")
        
        self.btn_back = ttk.Button(
            footer,
            text="⬅ Anterior",
            command=self.previous_step,
            state="disabled"
        )
        self.btn_back.pack(side="left", padx=5)
        
        ttk.Button(
            footer,
            text="❌ Cancelar Venta",
            command=self.cancel_sale,
            style="Danger.TButton"
        ).pack(side="left", padx=5)
        
        self.btn_next = ttk.Button(
            footer,
            text="Siguiente ➡",
            command=self.next_step,
            style="Primary.TButton"
        )
        self.btn_next.pack(side="right", padx=5)

    def create_product_tab(self):
        """Tab 1: Selección de productos con descuentos."""
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text="📦 Productos")
        
        # Configurar grid
        tab.grid_columnconfigure(0, weight=2)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Panel de búsqueda
        search_frame = ttk.LabelFrame(tab, text="🔍 Búsqueda de Productos", padding="10")
        search_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11))
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<KeyRelease>", self.filter_products)
        
        ttk.Button(search_frame, text="🔄", command=self.load_products, width=3).pack(side="left")
        
        # Lista de productos
        products_frame = ttk.LabelFrame(tab, text="📋 Catálogo", padding="10")
        products_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        # Scrollbars
        scroll_y = ttk.Scrollbar(products_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(products_frame, orient="horizontal")
        
        self.products_tree = ttk.Treeview(
            products_frame,
            columns=("ID", "Producto", "Stock", "Estado", "Precio"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=12
        )
        
        scroll_y.config(command=self.products_tree.yview)
        scroll_x.config(command=self.products_tree.xview)
        
        # Configurar columnas
        self.products_tree.heading("ID", text="ID")
        self.products_tree.heading("Producto", text="Producto")
        self.products_tree.heading("Stock", text="Stock")
        self.products_tree.heading("Estado", text="Estado")
        self.products_tree.heading("Precio", text="Precio")
        
        self.products_tree.column("ID", width=50, anchor="center")
        self.products_tree.column("Producto", width=250)
        self.products_tree.column("Stock", width=70, anchor="center")
        self.products_tree.column("Estado", width=100, anchor="center")
        self.products_tree.column("Precio", width=90, anchor="center")
        
        self.products_tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        
        products_frame.grid_rowconfigure(0, weight=1)
        products_frame.grid_columnconfigure(0, weight=1)
        
        # Tags de colores
        self.products_tree.tag_configure("critical", background="#ffebee", foreground="#c62828")
        self.products_tree.tag_configure("low", background="#fff3e0", foreground="#e65100")
        self.products_tree.tag_configure("normal", background="#e8f5e9", foreground="#2e7d32")
        self.products_tree.tag_configure("good", background="#ffffff", foreground="#424242")
        
        self.products_tree.bind("<<TreeviewSelect>>", self.on_product_select)
        self.products_tree.bind("<Double-1>", lambda e: self.quick_add())
        
        # Panel derecho
        right_panel = ttk.Frame(tab)
        right_panel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))
        
        # Detalle del producto
        detail_frame = ttk.LabelFrame(right_panel, text="📊 Detalle", padding="10")
        detail_frame.pack(fill="x", pady=(0, 10))
        
        self.detail_text = tk.Text(
            detail_frame,
            height=6,
            width=30,
            font=("Arial", 9),
            wrap=tk.WORD,
            background="#f8f9fa"
        )
        self.detail_text.pack(fill="both", expand=True)
        self.detail_text.insert("1.0", "Seleccione un producto...")
        self.detail_text.config(state="disabled")
        
        # Agregar al carrito
        add_frame = ttk.LabelFrame(right_panel, text="➕ Agregar", padding="10")
        add_frame.pack(fill="x", pady=(0, 10))
        
        qty_frame = ttk.Frame(add_frame)
        qty_frame.pack(fill="x", pady=5)
        
        ttk.Label(qty_frame, text="Cantidad:", font=("Arial", 10, "bold")).pack(side="left")
        self.qty_var = tk.IntVar(value=1)
        ttk.Spinbox(qty_frame, from_=1, to=10000, textvariable=self.qty_var, width=10).pack(side="left", padx=5)
        
        # Selector de descuento
        discount_frame = ttk.Frame(add_frame)
        discount_frame.pack(fill="x", pady=5)
        
        ttk.Label(discount_frame, text="Descuento:", font=("Arial", 9)).pack(side="left")
        self.discount_var = tk.StringVar(value="Sin descuento")
        self.discount_combo = ttk.Combobox(
            discount_frame,
            textvariable=self.discount_var,
            state="readonly",
            width=15,
            font=("Arial", 9)
        )
        self.discount_combo.pack(side="left", padx=5)
        
        ttk.Button(
            add_frame,
            text="✅ Agregar",
            command=self.add_to_cart,
            style="Success.TButton"
        ).pack(fill="x", pady=5)
        
        ttk.Button(
            add_frame,
            text="⚡ Rápido (Doble Clic)",
            command=self.quick_add,
            style="Primary.TButton"
        ).pack(fill="x")
        
        # Carrito
        cart_frame = ttk.LabelFrame(right_panel, text="🛒 Carrito", padding="10")
        cart_frame.pack(fill="both", expand=True)
        
        self.cart_tree = ttk.Treeview(
            cart_frame,
            columns=("Producto", "Cant", "Desc", "Total"),
            show="headings",
            height=6
        )
        
        self.cart_tree.heading("Producto", text="Producto")
        self.cart_tree.heading("Cant", text="Cant.")
        self.cart_tree.heading("Desc", text="Desc.")
        self.cart_tree.heading("Total", text="Total")
        
        self.cart_tree.column("Producto", width=120)
        self.cart_tree.column("Cant", width=50, anchor="center")
        self.cart_tree.column("Desc", width=50, anchor="center")
        self.cart_tree.column("Total", width=70, anchor="center")
        
        self.cart_tree.pack(fill="both", expand=True, pady=(0, 5))
        
        # Botones del carrito
        cart_btns = ttk.Frame(cart_frame)
        cart_btns.pack(fill="x")
        
        ttk.Button(cart_btns, text="❌", command=self.remove_from_cart, width=3).pack(side="left", padx=2)
        ttk.Button(cart_btns, text="✏️", command=self.edit_cart_item, width=3).pack(side="left", padx=2)
        ttk.Button(cart_btns, text="🗑", command=self.clear_cart, width=3).pack(side="left", padx=2)
        
        self.cart_total_label = ttk.Label(
            cart_frame,
            text="Total: L 0.00",
            font=("Arial", 12, "bold"),
            foreground="#28a745"
        )
        self.cart_total_label.pack(pady=(10, 0))
        
        # Cargar productos
        self.load_products()

    def create_client_tab(self):
        """Tab 2: Datos del cliente (integración con clients.py)."""
        tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(tab, text="👤 Cliente")
        
        tab.grid_columnconfigure(0, weight=1)
        
        ttk.Label(
            tab,
            text="📝 Información del Cliente",
            font=("Arial", 16, "bold"),
            foreground="#2c3e50"
        ).grid(row=0, column=0, pady=(0, 20))
        
        # Selector de cliente existente
        client_frame = ttk.LabelFrame(tab, text="Seleccionar Cliente", padding="15")
        client_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        
        ttk.Label(client_frame, text="Cliente:").pack(side="left", padx=5)
        
        self.client_var = tk.StringVar()
        self.client_combo = ttk.Combobox(
            client_frame,
            textvariable=self.client_var,
            state="readonly",
            font=("Arial", 10),
            width=40
        )
        self.client_combo.pack(side="left", fill="x", expand=True, padx=5)
        self.client_combo.bind("<<ComboboxSelected>>", self.load_selected_client)
        
        ttk.Button(
            client_frame,
            text="🔄",
            command=self.refresh_clients,
            width=3
        ).pack(side="left", padx=2)
        
        ttk.Button(
            client_frame,
            text="➕ Nuevo Cliente",
            command=self.open_new_client_form,
            style="Primary.TButton"
        ).pack(side="left", padx=5)
        
        # Información del cliente seleccionado
        info_frame = ttk.LabelFrame(tab, text="Datos del Cliente", padding="15")
        info_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 15))
        
        tab.grid_rowconfigure(2, weight=1)
        
        self.client_info_text = tk.Text(
            info_frame,
            height=12,
            font=("Arial", 10),
            wrap=tk.WORD,
            background="#f8f9fa"
        )
        self.client_info_text.pack(fill="both", expand=True)
        self.client_info_text.insert("1.0", "Seleccione un cliente o agregue uno nuevo...")
        self.client_info_text.config(state="disabled")
        
        # Cargar clientes
        self.refresh_clients()

    def create_preview_tab(self):
        """Tab 3: Vista previa de documentos."""
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text="📄 Documentos")
        
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        ttk.Label(
            tab,
            text="📋 Vista Previa de Documentos",
            font=("Arial", 16, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Recibo
        receipt_frame = ttk.LabelFrame(tab, text="🧾 Recibo", padding="10")
        receipt_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        receipt_btns = ttk.Frame(receipt_frame)
        receipt_btns.pack(fill="x", pady=(0, 5))
        
        ttk.Button(receipt_btns, text="✏️ Editar", command=self.edit_receipt).pack(side="left", padx=2)
        ttk.Button(receipt_btns, text="🔄 Regenerar", command=self.regenerate_receipt).pack(side="left", padx=2)
        
        self.receipt_text = tk.Text(
            receipt_frame,
            font=("Courier New", 9),
            wrap=tk.WORD,
            background="#ffffff"
        )
        self.receipt_text.pack(fill="both", expand=True)
        
        # Constancia
        constancia_frame = ttk.LabelFrame(tab, text="📜 Constancia", padding="10")
        constancia_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        
        constancia_btns = ttk.Frame(constancia_frame)
        constancia_btns.pack(fill="x", pady=(0, 5))
        
        ttk.Button(constancia_btns, text="✏️ Editar", command=self.edit_constancia).pack(side="left", padx=2)
        ttk.Button(constancia_btns, text="🔄 Regenerar", command=self.regenerate_constancia).pack(side="left", padx=2)
        
        self.constancia_text = tk.Text(
            constancia_frame,
            font=("Arial", 10),
            wrap=tk.WORD,
            background="#ffffff"
        )
        self.constancia_text.pack(fill="both", expand=True)

    def create_confirm_tab(self):
        """Tab 4: Confirmación final."""
        tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(tab, text="✅ Confirmar")
        
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        ttk.Label(
            tab,
            text="🎉 Confirmación de Venta",
            font=("Arial", 16, "bold"),
            foreground="#28a745"
        ).grid(row=0, column=0, pady=(0, 20))
        
        summary_frame = ttk.LabelFrame(tab, text="📊 Resumen", padding="20")
        summary_frame.grid(row=1, column=0, sticky="nsew")
        
        self.summary_text = tk.Text(
            summary_frame,
            font=("Arial", 11),
            height=15,
            background="#f8f9fa"
        )
        self.summary_text.pack(fill="both", expand=True)
        
        actions = ttk.Frame(tab)
        actions.grid(row=2, column=0, pady=(20, 0))
        
        ttk.Button(
            actions,
            text="✅ PROCESAR VENTA",
            command=self.process_sale,
            style="Success.TButton"
        ).pack(side="left", padx=10, ipadx=20, ipady=10)
        
        ttk.Button(
            actions,
            text="❌ Cancelar",
            command=self.cancel_sale,
            style="Danger.TButton"
        ).pack(side="left", padx=10, ipadx=20, ipady=10)

    # ============ MÉTODOS DE DESCUENTOS ============
    
    def load_discounts(self):
        """Carga descuentos desde la base de datos."""
        try:
            discounts = self.db.fetch(
                "SELECT id, nombre, porcentaje FROM Descuentos ORDER BY nombre"
            )
            
            discount_options = ["Sin descuento"]
            self.discount_data = {0: {"id": 0, "nombre": "Sin descuento", "porcentaje": 0.0}}
            
            for disc in discounts:
                disc_id, nombre, porcentaje = disc
                pct_int = int(porcentaje * 100) if (porcentaje * 100).is_integer() else round(porcentaje * 100, 1)
                display_text = f"{nombre} - {pct_int}%"
                discount_options.append(display_text)
                self.discount_data[len(discount_options) - 1] = {
                    "id": disc_id,
                    "nombre": nombre,
                    "porcentaje": porcentaje
                }
            
            self.discount_combo["values"] = discount_options
            self.discount_combo.set("Sin descuento")
            
        except Exception as e:
            print(f"Error cargando descuentos: {e}")

    # ============ MÉTODOS DE PRODUCTOS ============
    
    def load_products(self):
        """Carga productos con indicadores de stock."""
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        
        try:
            products = self.db.fetch(
                "SELECT id, nombre, stock, precio, descripcion FROM Productos WHERE stock >= 0 ORDER BY nombre"
            )
            
            for prod in products:
                prod_id, nombre, stock, precio, desc = prod
                
                if stock == 0:
                    estado = "❌ SIN STOCK"
                    tag = "critical"
                elif stock < 10:
                    estado = "⚠️ MUY BAJO"
                    tag = "critical"
                elif stock < 50:
                    estado = "⚡ BAJO"
                    tag = "low"
                elif stock < 100:
                    estado = "✅ NORMAL"
                    tag = "normal"
                else:
                    estado = "✅ DISPONIBLE"
                    tag = "good"
                
                self.products_tree.insert(
                    "",
                    "end",
                    values=(prod_id, nombre, stock, estado, f"L {precio:.2f}"),
                    tags=(tag, json.dumps({"id": prod_id, "nombre": nombre, "stock": stock, "precio": precio, "desc": desc}))
                )
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar productos: {e}")

    def filter_products(self, event=None):
        """Filtra productos en tiempo real."""
        search_term = self.search_var.get().lower()
        
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        
        try:
            products = self.db.fetch(
                "SELECT id, nombre, stock, precio, descripcion FROM Productos WHERE stock >= 0 ORDER BY nombre"
            )
            
            for prod in products:
                prod_id, nombre, stock, precio, desc = prod
                
                if search_term in nombre.lower() or search_term in str(prod_id):
                    if stock == 0:
                        estado = "❌ SIN STOCK"
                        tag = "critical"
                    elif stock < 10:
                        estado = "⚠️ MUY BAJO"
                        tag = "critical"
                    elif stock < 50:
                        estado = "⚡ BAJO"
                        tag = "low"
                    elif stock < 100:
                        estado = "✅ NORMAL"
                        tag = "normal"
                    else:
                        estado = "✅ DISPONIBLE"
                        tag = "good"
                    
                    self.products_tree.insert(
                        "",
                        "end",
                        values=(prod_id, nombre, stock, estado, f"L {precio:.2f}"),
                        tags=(tag, json.dumps({"id": prod_id, "nombre": nombre, "stock": stock, "precio": precio, "desc": desc}))
                    )
        except Exception as e:
            pass

    def on_product_select(self, event=None):
        """Muestra detalle del producto seleccionado."""
        selected = self.products_tree.focus()
        if not selected:
            return
        
        tags = self.products_tree.item(selected, "tags")
        if len(tags) < 2:
            return
        
        try:
            data = json.loads(tags[1])
            
            self.detail_text.config(state="normal")
            self.detail_text.delete("1.0", tk.END)
            
            detail = f"🏷️ {data['nombre']}\n\n"
            detail += f"ID: {data['id']}\n"
            detail += f"Stock: {data['stock']} unidades\n"
            detail += f"Precio: L {data['precio']:.2f}\n\n"
            detail += f"Descripción:\n{data['desc'] or 'N/A'}"
            
            self.detail_text.insert("1.0", detail)
            self.detail_text.config(state="disabled")
        except:
            pass

    def add_to_cart(self):
        """Agrega producto al carrito con descuento."""
        selected = self.products_tree.focus()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto")
            return
        
        tags = self.products_tree.item(selected, "tags")
        if len(tags) < 2:
            return
        
        try:
            data = json.loads(tags[1])
            quantity = self.qty_var.get()
            
            if data['stock'] == 0:
                messagebox.showerror("Sin Stock", "Este producto no tiene stock disponible")
                return
            
            current_qty = self.cart.get(data['id'], {}).get('cantidad', 0)
            if (current_qty + quantity) > data['stock']:
                messagebox.showerror(
                    "Stock Insuficiente",
                    f"Stock disponible: {data['stock']}\nEn carrito: {current_qty}\nTotal solicitado: {current_qty + quantity}"
                )
                return
            
            # Obtener descuento seleccionado
            discount_idx = self.discount_combo.current()
            discount_info = self.discount_data.get(discount_idx, {"porcentaje": 0.0, "nombre": "Sin descuento"})
            
            if data['id'] in self.cart:
                self.cart[data['id']]['cantidad'] += quantity
                self.cart[data['id']]['descuento_pct'] = discount_info['porcentaje']
                self.cart[data['id']]['descuento_nombre'] = discount_info['nombre']
            else:
                self.cart[data['id']] = {
                    'id': data['id'],
                    'nombre': data['nombre'],
                    'precio': data['precio'],
                    'cantidad': quantity,
                    'stock': data['stock'],
                    'descuento_pct': discount_info['porcentaje'],
                    'descuento_nombre': discount_info['nombre']
                }
            
            self.update_cart_display()
            self.venta_en_progreso = True
            
            messagebox.showinfo("Agregado", f"{data['nombre']}\nCantidad: {quantity}\nDescuento: {discount_info['nombre']}")
            self.qty_var.set(1)
            self.discount_combo.set("Sin descuento")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al agregar: {e}")

    def quick_add(self):
        """Agrega 1 unidad rápidamente."""
        selected = self.products_tree.focus()
        if not selected:
            return
        
        tags = self.products_tree.item(selected, "tags")
        if len(tags) < 2:
            return
        
        try:
            data = json.loads(tags[1])
            
            if data['stock'] == 0:
                messagebox.showerror("Sin Stock", "Producto sin stock")
                return
            
            current_qty = self.cart.get(data['id'], {}).get('cantidad', 0)
            if (current_qty + 1) > data['stock']:
                messagebox.showerror("Stock Insuficiente", f"Ya tiene {current_qty} en el carrito")
                return
            
            if data['id'] in self.cart:
                self.cart[data['id']]['cantidad'] += 1
            else:
                self.cart[data['id']] = {
                    'id': data['id'],
                    'nombre': data['nombre'],
                    'precio': data['precio'],
                    'cantidad': 1,
                    'stock': data['stock'],
                    'descuento_pct': 0.0,
                    'descuento_nombre': 'Sin descuento'
                }
            
            self.update_cart_display()
            self.venta_en_progreso = True
            self.show_mini_notif(f"✅ +1 {data['nombre']}")
            
        except:
            pass

    def update_cart_display(self):
        """Actualiza visualización del carrito."""
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        total = 0.0
        for prod_id, data in self.cart.items():
            subtotal = data['precio'] * data['cantidad']
            descuento = subtotal * data['descuento_pct']
            total_item = subtotal - descuento
            total += total_item
            
            desc_text = f"{int(data['descuento_pct']*100)}%" if data['descuento_pct'] > 0 else "-"
            
            self.cart_tree.insert(
                "",
                "end",
                iid=str(prod_id),
                values=(
                    data['nombre'][:15],
                    data['cantidad'],
                    desc_text,
                    f"L {total_item:.2f}"
                )
            )
        
        self.total_venta = total
        self.cart_total_label.config(text=f"Total: L {total:,.2f}")

    def edit_cart_item(self):
        """Edita cantidad y descuento de producto en carrito."""
        selected = self.cart_tree.focus()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto del carrito")
            return
        
        try:
            prod_id = int(selected)
            if prod_id not in self.cart:
                return
            
            item = self.cart[prod_id]
            
            # Ventana de edición
            edit_win = Toplevel(self.app)
            edit_win.title("Editar Producto")
            edit_win.geometry("400x300")
            edit_win.transient(self.app)
            edit_win.grab_set()
            
            frame = ttk.Frame(edit_win, padding="20")
            frame.pack(fill="both", expand=True)
            
            ttk.Label(
                frame,
                text=f"Editando: {item['nombre']}",
                font=("Arial", 12, "bold")
            ).pack(pady=(0, 20))
            
            # Cantidad
            qty_frame = ttk.Frame(frame)
            qty_frame.pack(fill="x", pady=10)
            
            ttk.Label(qty_frame, text="Cantidad:").pack(side="left", padx=5)
            qty_var = tk.IntVar(value=item['cantidad'])
            ttk.Spinbox(
                qty_frame,
                from_=1,
                to=item['stock'],
                textvariable=qty_var,
                width=10
            ).pack(side="left", padx=5)
            
            ttk.Label(qty_frame, text=f"(Stock: {item['stock']})").pack(side="left", padx=5)
            
            # Descuento
            disc_frame = ttk.Frame(frame)
            disc_frame.pack(fill="x", pady=10)
            
            ttk.Label(disc_frame, text="Descuento:").pack(side="left", padx=5)
            disc_var = tk.StringVar(value=item['descuento_nombre'])
            disc_combo = ttk.Combobox(
                disc_frame,
                textvariable=disc_var,
                state="readonly",
                values=[v['nombre'] + f" - {int(v['porcentaje']*100)}%" if v['porcentaje'] > 0 else v['nombre'] 
                        for v in self.discount_data.values()],
                width=25
            )
            disc_combo.pack(side="left", padx=5)
            
            # Buscar índice actual
            for idx, disc_info in self.discount_data.items():
                if disc_info['nombre'] == item['descuento_nombre']:
                    disc_combo.current(idx)
                    break
            
            def save_changes():
                new_qty = qty_var.get()
                if new_qty <= 0 or new_qty > item['stock']:
                    messagebox.showerror("Error", f"Cantidad debe estar entre 1 y {item['stock']}")
                    return
                
                # Obtener descuento seleccionado
                disc_idx = disc_combo.current()
                if disc_idx >= 0:
                    disc_info = self.discount_data.get(disc_idx, {"porcentaje": 0.0, "nombre": "Sin descuento"})
                    
                    self.cart[prod_id]['cantidad'] = new_qty
                    self.cart[prod_id]['descuento_pct'] = disc_info['porcentaje']
                    self.cart[prod_id]['descuento_nombre'] = disc_info['nombre']
                    
                    self.update_cart_display()
                    edit_win.destroy()
                    messagebox.showinfo("Actualizado", "Producto actualizado correctamente")
            
            ttk.Button(
                frame,
                text="💾 Guardar Cambios",
                command=save_changes,
                style="Success.TButton"
            ).pack(pady=20)
            
            ttk.Button(
                frame,
                text="Cancelar",
                command=edit_win.destroy
            ).pack()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al editar: {e}")

    def remove_from_cart(self):
        """Elimina producto del carrito."""
        selected = self.cart_tree.focus()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto")
            return
        
        try:
            prod_id = int(selected)
            if prod_id in self.cart:
                nombre = self.cart[prod_id]['nombre']
                if messagebox.askyesno("Confirmar", f"¿Eliminar {nombre}?"):
                    del self.cart[prod_id]
                    self.update_cart_display()
                    
                    if not self.cart:
                        self.venta_en_progreso = False
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def clear_cart(self):
        """Limpia el carrito completo."""
        if not self.cart:
            return
        
        if messagebox.askyesno("Confirmar", "¿Vaciar el carrito completo?"):
            self.cart = {}
            self.update_cart_display()
            self.venta_en_progreso = False
            messagebox.showinfo("Carrito Vaciado", "Todos los productos fueron eliminados")

    # ============ MÉTODOS DE CLIENTE ============
    
    def refresh_clients(self):
        """Recarga lista de clientes activos."""
        try:
            clients = self.db.fetch(
                "SELECT id, nombre, apellido FROM Clientes WHERE activo = 1 ORDER BY apellido, nombre"
            )
            
            client_list = [f"{c[2]}, {c[1]} (ID: {c[0]})" for c in clients]
            
            if not client_list:
                client_list = ["No hay clientes registrados"]
            
            self.client_combo['values'] = client_list
            
            if len(client_list) > 0 and client_list[0] != "No hay clientes registrados":
                self.client_combo.current(0)
                self.load_selected_client()
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar clientes: {e}")

    def load_selected_client(self, event=None):
        """Carga datos del cliente seleccionado."""
        selected = self.client_var.get()
        if not selected or selected == "No hay clientes registrados":
            return
        
        try:
            client_id = int(selected.split("ID: ")[1].rstrip(")"))
            
            client = self.db.fetch(
                "SELECT nombre, apellido, dni, telefono, email, direccion FROM Clientes WHERE id = ?",
                (client_id,)
            )
            
            if client:
                c = client[0]
                self.cliente_data = {
                    'id': client_id,
                    'nombre': c[0],
                    'apellido': c[1],
                    'dni': c[2] or '',
                    'telefono': c[3] or '',
                    'email': c[4] or '',
                    'direccion': c[5] or ''
                }
                
                # Mostrar información
                self.client_info_text.config(state="normal")
                self.client_info_text.delete("1.0", tk.END)
                
                info = f"✅ CLIENTE SELECCIONADO\n\n"
                info += f"Nombre Completo:\n{c[0]} {c[1]}\n\n"
                info += f"DNI/RTN: {c[2] or 'N/A'}\n"
                info += f"Teléfono: {c[3] or 'N/A'}\n"
                info += f"Email: {c[4] or 'N/A'}\n\n"
                info += f"Dirección:\n{c[5] or 'N/A'}"
                
                self.client_info_text.insert("1.0", info)
                self.client_info_text.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar cliente: {e}")

    def open_new_client_form(self):
        """Abre formulario para nuevo cliente."""
        if self.venta_en_progreso:
            if not messagebox.askyesno(
                "Venta en Progreso",
                "Tiene una venta en progreso.\n\n¿Desea pausar para agregar un cliente?\n\nLos productos en el carrito se mantendrán."
            ):
                return
        
        # Ventana de nuevo cliente
        client_win = Toplevel(self.app)
        client_win.title("Nuevo Cliente")
        client_win.geometry("600x500")
        client_win.transient(self.app)
        client_win.grab_set()
        
        main_frame = ttk.Frame(client_win, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(
            main_frame,
            text="➕ Agregar Nuevo Cliente",
            font=("Arial", 16, "bold"),
            foreground="#3498db"
        ).pack(pady=(0, 20))
        
        # Formulario
        form_frame = ttk.LabelFrame(main_frame, text="Datos del Cliente", padding="15")
        form_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        fields = [
            ("nombre", "Nombre *:", True),
            ("apellido", "Apellido *:", True),
            ("dni", "DNI / RTN:", False),
            ("telefono", "Teléfono:", False),
            ("email", "Email:", False),
            ("direccion", "Dirección:", False)
        ]
        
        entries = {}
        
        for idx, (field, label, required) in enumerate(fields):
            row = idx // 2
            col = (idx % 2) * 2
            
            ttk.Label(
                form_frame,
                text=label,
                font=("Arial", 10, "bold" if required else "normal")
            ).grid(row=row, column=col, sticky="w", padx=10, pady=8)
            
            if field == "direccion":
                entry = tk.Text(form_frame, height=3, width=50, font=("Arial", 10))
                entry.grid(row=row, column=col+1, columnspan=3, sticky="ew", padx=10, pady=8)
            else:
                entry = ttk.Entry(form_frame, font=("Arial", 10), width=30)
                entry.grid(row=row, column=col+1, sticky="ew", padx=10, pady=8)
            
            entries[field] = entry
        
        form_frame.grid_columnconfigure(1, weight=1)
        form_frame.grid_columnconfigure(3, weight=1)
        
        # Barra de progreso para sincronización
        progress_frame = ttk.Frame(main_frame)
        
        progress_label = ttk.Label(progress_frame, text="", font=("Arial", 10))
        progress_label.pack()
        
        progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', length=300)
        progress_bar.pack(pady=5)
        
        def save_client():
            nombre = entries['nombre'].get().strip()
            apellido = entries['apellido'].get().strip()
            
            if not nombre or not apellido:
                messagebox.showerror("Error", "Nombre y Apellido son obligatorios")
                return
            
            # Mostrar barra de progreso
            progress_frame.pack(fill="x", pady=10)
            progress_label.config(text="🔄 Sincronizando cliente...")
            progress_bar.start(10)
            client_win.update()
            
            try:
                from datetime import datetime
                
                self.db.execute(
                    """INSERT INTO Clientes (nombre, apellido, dni, telefono, email, direccion, fecha_registro, activo)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        nombre,
                        apellido,
                        entries['dni'].get().strip() or None,
                        entries['telefono'].get().strip() or None,
                        entries['email'].get().strip() or None,
                        entries['direccion'].get("1.0", tk.END).strip() or None,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                )
                
                result = self.db.fetch("SELECT last_insert_rowid()")
                new_client_id = result[0][0]
                
                # Simular sincronización
                self.app.after(1000, lambda: finalize_sync(new_client_id, nombre, apellido))
                
            except Exception as e:
                progress_bar.stop()
                progress_frame.pack_forget()
                messagebox.showerror("Error", f"Error al guardar cliente: {e}")
        
        def finalize_sync(client_id, nombre, apellido):
            progress_bar.stop()
            progress_label.config(text="✅ Cliente sincronizado correctamente")
            
            self.app.after(500, lambda: complete_client(client_id, nombre, apellido))
        
        def complete_client(client_id, nombre, apellido):
            # Guardar en cliente_data
            self.cliente_data = {
                'id': client_id,
                'nombre': nombre,
                'apellido': apellido,
                'dni': entries['dni'].get().strip(),
                'telefono': entries['telefono'].get().strip(),
                'email': entries['email'].get().strip(),
                'direccion': entries['direccion'].get("1.0", tk.END).strip()
            }
            
            client_win.destroy()
            
            # Refrescar lista
            self.refresh_clients()
            
            # Seleccionar nuevo cliente
            for idx, val in enumerate(self.client_combo['values']):
                if f"ID: {client_id}" in val:
                    self.client_combo.current(idx)
                    self.load_selected_client()
                    break
            
            messagebox.showinfo(
                "Cliente Agregado",
                f"✅ {nombre} {apellido}\n\nCliente registrado exitosamente"
            )
        
        # Botones
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(
            btn_frame,
            text="💾 Guardar Cliente",
            command=save_client,
            style="Success.TButton"
        ).pack(side="left", padx=5, ipadx=10)
        
        ttk.Button(
            btn_frame,
            text="Cancelar",
            command=client_win.destroy
        ).pack(side="left", padx=5)

    # ============ MÉTODOS DE DOCUMENTOS ============
    
    def generate_documents(self):
        """Genera recibo y constancia."""
        self.venta_id = f"VM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
        
        # Generar contenido
        receipt = self.generate_receipt()
        constancia = self.generate_constancia()
        
        self.receipt_text.delete("1.0", tk.END)
        self.receipt_text.insert("1.0", receipt)
        
        self.constancia_text.delete("1.0", tk.END)
        self.constancia_text.insert("1.0", constancia)

    def generate_receipt(self):
        """Genera recibo con formato específico."""
        lines = []
        
        # Encabezado
        lines.append("PODEGA Y COMERCIAL RIVERA")
        lines.append("R.T.N.: 12011972000081")
        lines.append("Tel: 2774-1192 / 9967-7300")
        lines.append("Bo. La Mercedes, Colonia la Ermita, 1ra Calle, 14-62,")
        lines.append("frente a Farmacia Santa, La Paz, Honduras")
        lines.append("Email: freddyrivera2015@gmail.com")
        lines.append("")
        lines.append("FACTURA")
        lines.append(f"No. 0000-0001-{self.venta_id.split('-')[-1]}")
        lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Cliente
        if self.cliente_data:
            lines.append("DATOS DEL CLIENTE:")
            lines.append(f"Nombre: {self.cliente_data['nombre']} {self.cliente_data['apellido']}")
            if self.cliente_data.get('dni'):
                lines.append(f"DNI/RTN: {self.cliente_data['dni']}")
            if self.cliente_data.get('telefono'):
                lines.append(f"Tel: {self.cliente_data['telefono']}")
            if self.cliente_data.get('direccion'):
                lines.append(f"Dir: {self.cliente_data['direccion']}")
            lines.append("")
        
        # Productos
        lines.append(f"{'Cant.':<8}{'Código':<15}{'Producto':<25}{'P.Unit':>10}{'Subtotal':>12}")
        lines.append("-" * 70)
        
        subtotal_total = 0.0
        for prod_id, data in self.cart.items():
            codigo = str(prod_id).zfill(8)
            nombre = data['nombre'][:23]
            cant = data['cantidad']
            precio = data['precio']
            desc_pct = data['descuento_pct']
            
            subtotal = (cant * precio) * (1 - desc_pct)
            subtotal_total += subtotal
            
            lines.append(f"{cant:<8}{codigo:<15}{nombre:<25}L{precio:>9.2f}L{subtotal:>10.2f}")
        
        lines.append("")
        lines.append(f"{'TOTAL:':>58}L{self.total_venta:>10.2f}")
        
        # Convertir a palabras
        total_entero = int(self.total_venta)
        total_centavos = int(round((self.total_venta - total_entero) * 100))
        lines.append(f"{self.numero_a_palabras(total_entero).upper()} LEMPIRAS CON {total_centavos:02d}/100")
        lines.append("")
        
        lines.append("Orden de Compra Exenta:")
        lines.append("Constancia Registro Exento:")
        lines.append("Desc. y Rebajas Otorgados:")
        lines.append("")
        
        # Impuestos
        impuesto = subtotal_total * 0.15
        total_con_imp = subtotal_total + impuesto
        
        lines.append(f"{'Concepto':<30}{'Total':>15}")
        lines.append(f"{'Sub Total':<30}L{subtotal_total:>13.2f}")
        lines.append(f"{'Exento':<30}L{0.00:>13.2f}")
        lines.append(f"{'Gravado 15%':<30}L{subtotal_total:>13.2f}")
        lines.append(f"{'Gravado 18%':<30}L{0.00:>13.2f}")
        lines.append(f"{'Impuesto 15%':<30}L{impuesto:>13.2f}")
        lines.append(f"{'Impuesto 18%':<30}L{0.00:>13.2f}")
        lines.append(f"{'TOTAL:':<30}L{total_con_imp:>13.2f}")
        lines.append("")
        
        lines.append(f"Monto Recibido: L{self.total_venta:.2f}")
        lines.append(f"Vuelto: L0.00")
        lines.append("")
        lines.append("Observaciones:")
        lines.append("")
        lines.append("Original - Cliente")
        lines.append("Gracias por su compra")
        
        return "\n".join(lines)

    def generate_constancia(self):
        """Genera constancia de compra."""
        content = f"""
CONSTANCIA DE COMPRA MAYORISTA

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Por medio de la presente, PODEGA Y COMERCIAL RIVERA,
con R.T.N. 12011972000081, HACE CONSTAR que:

DATOS DEL CLIENTE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nombre: {self.cliente_data['nombre']} {self.cliente_data['apellido']}
DNI/RTN: {self.cliente_data.get('dni', 'N/A')}
Teléfono: {self.cliente_data.get('telefono', 'N/A')}
Email: {self.cliente_data.get('email', 'N/A')}
Dirección: {self.cliente_data.get('direccion', 'N/A')}

DETALLES DE LA COMPRA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fecha: {datetime.now().strftime('%d de %B de %Y')}
Factura: {self.venta_id}
Tipo: VENTA MAYORISTA

PRODUCTOS:

"""
        for prod_id, data in self.cart.items():
            subtotal = data['cantidad'] * data['precio'] * (1 - data['descuento_pct'])
            content += f"  • {data['nombre']}\n"
            content += f"    {data['cantidad']} unidades x L{data['precio']:.2f}"
            if data['descuento_pct'] > 0:
                content += f" (Desc: {int(data['descuento_pct']*100)}%)"
            content += f" = L{subtotal:.2f}\n\n"
        
        content += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MONTO TOTAL: L{self.total_venta:,.2f}

Esta constancia se emite para los fines que el
interesado estime conveniente.

Observaciones:
_________________________________________________
_________________________________________________
_________________________________________________


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Firma Autorizada              Sello de la Empresa


__________________            __________________


La Paz, Honduras
{datetime.now().strftime('%d de %B de %Y')}
"""
        return content

    def numero_a_palabras(self, n):
        """Convierte número a palabras."""
        if n == 0:
            return "cero"
        
        unidades = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
        decenas = ["", "diez", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
        centenas = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]
        
        if n < 10:
            return unidades[n]
        elif n < 100:
            return f"{decenas[n//10]} y {unidades[n%10]}" if n % 10 != 0 else decenas[n//10]
        elif n < 1000:
            return f"{centenas[n//100]} {self.numero_a_palabras(n%100)}" if n % 100 != 0 else centenas[n//100]
        elif n < 1000000:
            miles = n // 1000
            resto = n % 1000
            palabra_miles = "mil" if miles == 1 else f"{self.numero_a_palabras(miles)} mil"
            return f"{palabra_miles} {self.numero_a_palabras(resto)}" if resto != 0 else palabra_miles
        
        return str(n)

    def edit_receipt(self):
        """Permite editar recibo."""
        self.receipt_text.config(state="normal")
        messagebox.showinfo("Modo Edición", "Puede editar el recibo libremente")

    def edit_constancia(self):
        """Permite editar constancia."""
        self.constancia_text.config(state="normal")
        messagebox.showinfo("Modo Edición", "Puede editar la constancia libremente")

    def regenerate_receipt(self):
        """Regenera recibo."""
        receipt = self.generate_receipt()
        self.receipt_text.config(state="normal")
        self.receipt_text.delete("1.0", tk.END)
        self.receipt_text.insert("1.0", receipt)
        messagebox.showinfo("Regenerado", "Recibo regenerado correctamente")

    def regenerate_constancia(self):
        """Regenera constancia."""
        constancia = self.generate_constancia()
        self.constancia_text.config(state="normal")
        self.constancia_text.delete("1.0", tk.END)
        self.constancia_text.insert("1.0", constancia)
        messagebox.showinfo("Regenerado", "Constancia regenerada correctamente")

    # ============ NAVEGACIÓN ============
    
    def next_step(self):
        """Avanza al siguiente paso."""
        if self.current_step == 1:
            if not self.cart:
                messagebox.showwarning("Carrito Vacío", "Agregue productos al carrito")
                return
            self.notebook.tab(1, state="normal")
            self.notebook.select(1)
            self.current_step = 2
            self.step_label.config(text="Paso 2/4: Datos del Cliente")
            self.btn_back.config(state="normal")
            
        elif self.current_step == 2:
            if not self.cliente_data:
                messagebox.showerror("Error", "Debe seleccionar un cliente")
                return
            self.generate_documents()
            self.notebook.tab(2, state="normal")
            self.notebook.select(2)
            self.current_step = 3
            self.step_label.config(text="Paso 3/4: Revisión de Documentos")
            
        elif self.current_step == 3:
            self.generate_summary()
            self.notebook.tab(3, state="normal")
            self.notebook.select(3)
            self.current_step = 4
            self.step_label.config(text="Paso 4/4: Confirmación")
            self.btn_next.config(text="✅ Finalizar", style="Success.TButton")
            
        elif self.current_step == 4:
            self.process_sale()

    def previous_step(self):
        """Retrocede al paso anterior."""
        if self.current_step > 1:
            self.current_step -= 1
            self.notebook.select(self.current_step - 1)
            
            if self.current_step == 1:
                self.btn_back.config(state="disabled")
                self.step_label.config(text="Paso 1/4: Selección de Productos")
            elif self.current_step == 2:
                self.step_label.config(text="Paso 2/4: Datos del Cliente")
            elif self.current_step == 3:
                self.step_label.config(text="Paso 3/4: Revisión de Documentos")
            
            self.btn_next.config(text="Siguiente ➡", style="Primary.TButton")

    def generate_summary(self):
        """Genera resumen final."""
        self.summary_text.delete("1.0", tk.END)
        
        summary = f"""
╔════════════════════════════════════════════════╗
║       🎉 RESUMEN DE VENTA MAYORISTA 🎉         ║
╚════════════════════════════════════════════════╝

📋 INFORMACIÓN GENERAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ID: {self.venta_id}
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

👤 CLIENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{self.cliente_data['nombre']} {self.cliente_data['apellido']}
DNI: {self.cliente_data.get('dni', 'N/A')}
Tel: {self.cliente_data.get('telefono', 'N/A')}

📦 PRODUCTOS ({len(self.cart)} items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        for prod_id, data in self.cart.items():
            subtotal = data['cantidad'] * data['precio'] * (1 - data['descuento_pct'])
            summary += f"• {data['nombre']}\n"
            summary += f"  {data['cantidad']} x L{data['precio']:.2f}"
            if data['descuento_pct'] > 0:
                summary += f" (-{int(data['descuento_pct']*100)}%)"
            summary += f" = L{subtotal:,.2f}\n\n"
        
        summary += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 TOTAL: L{self.total_venta:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Se generarán 2 documentos:
  ✅ Recibo de Venta (HTML/PDF)
  ✅ Constancia de Compra (HTML/PDF)

⚠️  IMPORTANTE:
  • Se actualizará el inventario
  • Se registrará en el sistema
  • Los documentos se guardarán automáticamente

Presione "PROCESAR VENTA" para finalizar.
"""
        
        self.summary_text.insert("1.0", summary)
        self.summary_text.config(state="disabled")

    # ============ PROCESAMIENTO DE VENTA ============
    
    def process_sale(self):
        """Procesa la venta con animación."""
        if not messagebox.askyesno(
            "Confirmar Venta",
            "¿Procesar esta venta?\n\nEsta acción:\n• Actualizará el inventario\n• Registrará la venta\n• Generará los documentos\n\n¡No se puede deshacer!"
        ):
            return
        
        self.show_processing_animation()

    def show_processing_animation(self):
        """Muestra animación de procesamiento."""
        process_win = Toplevel(self.app)
        process_win.title("Procesando Venta")
        process_win.geometry("600x400")
        process_win.transient(self.app)
        process_win.grab_set()
        process_win.resizable(False, False)
        
        # Centrar
        process_win.update_idletasks()
        x = (process_win.winfo_screenwidth() // 2) - 300
        y = (process_win.winfo_screenheight() // 2) - 200
        process_win.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(process_win, padding="30")
        frame.pack(fill="both", expand=True)
        
        ttk.Label(
            frame,
            text="⏳ Procesando Venta...",
            font=("Arial", 18, "bold"),
            foreground="#3498db"
        ).pack(pady=(0, 30))
        
        progress = ttk.Progressbar(frame, mode='determinate', length=500)
        progress.pack(pady=20)
        
        status_label = ttk.Label(frame, text="Iniciando...", font=("Arial", 11))
        status_label.pack(pady=10)
        
        steps = [
            ("Validando información...", 15),
            ("Registrando venta...", 30),
            ("Actualizando inventario...", 50),
            ("Generando recibo...", 70),
            ("Generando constancia...", 85),
            ("Guardando documentos...", 95),
            ("Finalizando...", 100)
        ]
        
        def process_steps(index=0):
            if index < len(steps):
                text, value = steps[index]
                status_label.config(text=f"✓ {text}")
                progress['value'] = value
                
                if index == 1:
                    # Registrar venta
                    try:
                        self.db.execute(
                            """INSERT INTO Ventas (id, fecha, total, monto_pagado, vuelto, usuario_id, id_cliente, tipo_recibo)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                self.venta_id,
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                self.total_venta,
                                self.total_venta,
                                0.0,
                                self.app.current_user[0] if hasattr(self.app, 'current_user') else 1,
                                self.cliente_data['id'],
                                'PDF_MAYORISTA'
                            )
                        )
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al registrar: {e}")
                        process_win.destroy()
                        return
                
                elif index == 2:
                    # Actualizar inventario
                    try:
                        for prod_id, data in self.cart.items():
                            subtotal = data['cantidad'] * data['precio'] * (1 - data['descuento_pct'])
                            descuento = data['cantidad'] * data['precio'] * data['descuento_pct']
                            
                            self.db.execute(
                                """INSERT INTO DetalleVenta (venta_id, producto_id, nombre_producto, cantidad, precio_unitario, descuento, subtotal)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (self.venta_id, prod_id, data['nombre'], data['cantidad'], data['precio'], descuento, subtotal)
                            )
                            
                            self.db.execute(
                                "UPDATE Productos SET stock = stock - ? WHERE id = ?",
                                (data['cantidad'], prod_id)
                            )
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al actualizar inventario: {e}")
                        process_win.destroy()
                        return
                
                elif index == 3:
                    # Generar recibo (builder compartido)
                    receipt_html = self.generate_receipt_html_document()
                    self.receipt_path = self.save_html_document(
                        receipt_html,
                        f"Recibo_{self.venta_id}.html"
                    )
                
                elif index == 4:
                    # Generar constancia
                    self.constancia_path = self.save_document(
                        self.constancia_text.get("1.0", tk.END),
                        f"Constancia_{self.venta_id}.html"
                    )
                
                process_win.after(500, lambda: process_steps(index + 1))
            else:
                process_win.destroy()
                self.show_completion()
        
        process_steps()

    def generate_receipt_html_document(self):
        """Genera HTML de recibo reutilizando builder comun."""
        cliente = {
            "nombre": self.cliente_data.get("nombre", ""),
            "apellido": self.cliente_data.get("apellido", ""),
            "dni": self.cliente_data.get("dni", ""),
            "telefono": self.cliente_data.get("telefono", ""),
            "direccion": self.cliente_data.get("direccion", ""),
        }
        items = []
        for prod_id, data in self.cart.items():
            items.append(
                {
                    "producto_id": prod_id,
                    "nombre": data["nombre"],
                    "cantidad": data["cantidad"],
                    "precio_unitario": data["precio"],
                    "descuento_porcentaje": data.get("descuento_pct", 0),
                }
            )

        return build_receipt_html(
            venta_id=self.venta_id,
            fecha=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total=float(self.total_venta or 0),
            monto_pagado=float(self.total_venta or 0),
            vuelto=0.0,
            items=items,
            cliente=cliente,
            mode='letter',
            number_to_words=self.numero_a_palabras,
        )

    def save_html_document(self, html_content, filename):
        """Guarda HTML ya renderizado en la carpeta configurada."""
        save_path = self.db.get_config("recibo_save_path", "")

        if not save_path or not os.path.isdir(save_path):
            local_appdata = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
            save_path = os.path.join(local_appdata, "ERP-Facturacion", "Recibos")
            os.makedirs(save_path, exist_ok=True)
            self.db.set_config("recibo_save_path", save_path)

        file_path = os.path.join(save_path, filename)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return file_path
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar {filename}: {e}")
            return None

    def save_document(self, content, filename):
        """Guarda documento como HTML."""
        save_path = self.db.get_config("recibo_save_path", "")
        
        if not save_path or not os.path.isdir(save_path):
            local_appdata = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
            save_path = os.path.join(local_appdata, "ERP-Facturacion", "Recibos")
            os.makedirs(save_path, exist_ok=True)
            self.db.set_config("recibo_save_path", save_path)
        
        file_path = os.path.join(save_path, filename)
        
        try:
            html = self.convert_to_html(content, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return file_path
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar {filename}: {e}")
            return None

    def convert_to_html(self, text, title):
        """Convierte texto a HTML para impresión."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        @page {{ size: letter; margin: 2cm; }}
        body {{
            font-family: 'Courier New', monospace;
            font-size: 11px;
            line-height: 1.3;
            color: #000;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .document {{
            border: 2px solid #000;
            padding: 20px;
            background: #fff;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
            margin: 0;
        }}
        @media print {{
            .no-print {{ display: none; }}
            .document {{ border: none; }}
        }}
    </style>
</head>
<body>
    <div class="document">
        <pre>{text}</pre>
    </div>
    <div class="no-print" style="text-align: center; margin-top: 20px;">
        <button onclick="window.print()" style="padding: 10px 30px; font-size: 14px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
            🖨️ Imprimir / Guardar como PDF
        </button>
    </div>
</body>
</html>"""
        return html

    def show_completion(self):
        """Muestra diálogo de venta completada."""
        complete_win = Toplevel(self.app)
        complete_win.title("✅ Venta Completada")
        complete_win.geometry("700x500")
        complete_win.transient(self.app)
        complete_win.grab_set()
        
        # Centrar
        complete_win.update_idletasks()
        x = (complete_win.winfo_screenwidth() // 2) - 350
        y = (complete_win.winfo_screenheight() // 2) - 250
        complete_win.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(complete_win, padding="30")
        frame.pack(fill="both", expand=True)
        
        # Animación de éxito
        canvas = tk.Canvas(frame, width=100, height=100, bg="white", highlightthickness=0)
        canvas.pack(pady=(0, 20))
        canvas.create_oval(10, 10, 90, 90, outline="#28a745", width=4)
        canvas.create_line(30, 50, 45, 65, fill="#28a745", width=4)
        canvas.create_line(45, 65, 70, 35, fill="#28a745", width=4)
        
        ttk.Label(
            frame,
            text="¡VENTA PROCESADA EXITOSAMENTE!",
            font=("Arial", 18, "bold"),
            foreground="#28a745"
        ).pack()
        
        ttk.Label(
            frame,
            text=f"ID: {self.venta_id}",
            font=("Arial", 12)
        ).pack(pady=(5, 20))
        
        # Documentos
        info_frame = ttk.LabelFrame(frame, text="📄 Documentos", padding="20")
        info_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        if hasattr(self, 'receipt_path'):
            doc = ttk.Frame(info_frame)
            doc.pack(fill="x", pady=5)
            ttk.Label(doc, text="🧾 Recibo", font=("Arial", 10, "bold")).pack(side="left", padx=5)
            ttk.Button(doc, text="📂 Abrir", command=lambda: self.open_doc(self.receipt_path)).pack(side="right")
        
        if hasattr(self, 'constancia_path'):
            doc = ttk.Frame(info_frame)
            doc.pack(fill="x", pady=5)
            ttk.Label(doc, text="📜 Constancia", font=("Arial", 10, "bold")).pack(side="left", padx=5)
            ttk.Button(doc, text="📂 Abrir", command=lambda: self.open_doc(self.constancia_path)).pack(side="right")
        
        # Resumen
        summary = ttk.Frame(info_frame)
        summary.pack(fill="x", pady=(20, 0))
        
        ttk.Label(
            summary,
            text=f"Cliente: {self.cliente_data['nombre']} {self.cliente_data['apellido']}",
            font=("Arial", 10)
        ).pack(anchor="w")
        
        ttk.Label(
            summary,
            text=f"Productos: {len(self.cart)} items",
            font=("Arial", 10)
        ).pack(anchor="w")
        
        ttk.Label(
            summary,
            text=f"Total: L{self.total_venta:,.2f}",
            font=("Arial", 12, "bold"),
            foreground="#28a745"
        ).pack(anchor="w", pady=(5, 0))
        
        # Botones
        btns = ttk.Frame(frame)
        btns.pack(fill="x")
        
        ttk.Button(
            btns,
            text="🖨️ Abrir Ambos",
            command=self.open_all_docs,
            style="Success.TButton"
        ).pack(side="left", padx=5, ipadx=10)
        
        ttk.Button(
            btns,
            text="📂 Carpeta",
            command=self.open_folder,
            style="Primary.TButton"
        ).pack(side="left", padx=5, ipadx=10)
        
        ttk.Button(
            btns,
            text="🆕 Nueva Venta",
            command=lambda: self.new_sale(complete_win)
        ).pack(side="right", padx=5, ipadx=10)
        
        ttk.Button(
            btns,
            text="✅ Cerrar",
            command=complete_win.destroy
        ).pack(side="right", padx=5)

    def open_doc(self, path):
        """Abre documento en navegador."""
        if path and os.path.exists(path):
            import webbrowser
            webbrowser.open(f"file://{path}")
        else:
            messagebox.showerror("Error", "Archivo no encontrado")

    def open_all_docs(self):
        """Abre todos los documentos."""
        if hasattr(self, 'receipt_path'):
            self.open_doc(self.receipt_path)
        if hasattr(self, 'constancia_path'):
            self.open_doc(self.constancia_path)

    def open_folder(self):
        """Abre carpeta de documentos."""
        save_path = self.db.get_config("recibo_save_path", "")
        if save_path and os.path.isdir(save_path):
            import webbrowser
            webbrowser.open(save_path)

    def new_sale(self, window):
        """Inicia nueva venta."""
        window.destroy()
        self.reset_sale()

    def reset_sale(self):
        """Resetea el sistema."""
        self.cart = {}
        self.cliente_data = {}
        self.venta_id = None
        self.total_venta = 0.0
        self.current_step = 1
        self.venta_en_progreso = False
        
        self.update_cart_display()
        self.notebook.select(0)
        self.step_label.config(text="Paso 1/4: Selección de Productos")
        self.btn_back.config(state="disabled")
        self.btn_next.config(text="Siguiente ➡", style="Primary.TButton")
        
        for i in range(1, 4):
            self.notebook.tab(i, state="disabled")
        
        self.load_products()
        self.refresh_clients()

    def cancel_sale(self):
        """Cancela la venta."""
        if self.venta_en_progreso:
            if not messagebox.askyesno(
                "Cancelar Venta",
                "Tiene una venta en progreso.\n\n¿Está seguro de cancelar?\n\nSe perderán todos los datos."
            ):
                return
        
        self.reset_sale()
        messagebox.showinfo("Cancelado", "Venta cancelada correctamente")

    # ============ UTILIDADES ============
    
    def show_mini_notif(self, msg):
        """Muestra notificación temporal."""
        notif = Toplevel(self.app)
        notif.overrideredirect(True)
        notif.attributes('-topmost', True)
        
        notif.update_idletasks()
        x = notif.winfo_screenwidth() - 320
        y = 50
        notif.geometry(f"300x60+{x}+{y}")
        
        frame = ttk.Frame(notif, relief="raised", borderwidth=2, padding="10")
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text=msg, font=("Arial", 10)).pack()
        
        notif.after(2000, notif.destroy)

    def on_frame_switch(self):
        """Llamado cuando se intenta cambiar de frame."""
        if self.venta_en_progreso:
            if not messagebox.askyesno(
                "Venta en Progreso",
                "Tiene una venta en progreso.\n\n¿Seguro que desea salir?\n\nSe perderán los datos."
            ):
                return False
        return True