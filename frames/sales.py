"""
frames/sales.py
POS con catalogo, carrito y resumen en un solo panel principal.
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
from .ui import FONTS, PALETTE, center_window, format_hnl, normalize_hnl_amount, parse_hnl


class UnifiedPOSFrame(ttk.Frame):
    """Vista unica de POS con modos Normal y Especial."""

    def __init__(self, parent, app):
        super().__init__(parent, padding="8")
        self.app = app
        self.db = app.db
        self.sale_repository = SaleRepository(self.db)
        self.receipt_service = ReceiptService()
        self.load_pos_context_use_case = LoadPOSContext(self.sale_repository)
        self.create_pos_sale_use_case = CreatePOSSale(self.sale_repository, self.receipt_service)

        self.cart = {}
        self.product_index = {}
        self.discount_data = {}
        self.discount_by_type = {}
        self.client_data = {}
        self.selected_product_id = None
        self.selected_client_id = None
        self.selected_client_is_wholesale = False
        self.pending_sale = None
        self.preview_visible = False
        self.preview_window = None
        self.preview_text = None
        self.summary_window = None
        self.payment_window = None
        self.payment_modal_status_var = tk.StringVar(value="")

        self.sale_mode_var = tk.StringVar(value="NORMAL")
        self.search_var = tk.StringVar()
        self.discount_var = tk.StringVar(value="Sin descuento")
        self.client_var = tk.StringVar(value="Cliente General")
        self.payment_method_var = tk.StringVar(value="EFECTIVO")
        self.total_var = tk.DoubleVar(value=0.0)
        self.total_display_var = tk.StringVar(value=format_hnl(0))
        self.monto_pagado_var = tk.StringVar(value="0.00")
        self.vuelto_var = tk.DoubleVar(value=0.0)
        self.vuelto_display_var = tk.StringVar(value=format_hnl(0))
        self.status_var = tk.StringVar(value="Agregue productos al carrito.")
        self.preview_mode_var = tk.StringVar(value="ticket")
        self.preview_label_var = tk.StringVar(value="Vista previa disponible")
        self.cart_items_var = tk.StringVar(value="0 productos")
        self.selected_cart_name_var = tk.StringVar(value="Seleccione un producto del carrito.")
        self.selected_cart_discount_var = tk.StringVar(value="Descuento: 0%")
        self.selected_cart_subtotal_var = tk.StringVar(value="Subtotal: L 0.00")
        self.cart_hint_var = tk.StringVar(value="Seleccione un producto para editar la cantidad.")
        self.cart_editor_var = tk.StringVar(value="1")

        self._configure_styles()
        self._build_ui()
        self.load_pos_context()
        self.update_cart_display()

        self.app.bind("<F1>", lambda e: self.focus_search(), add="+")
        self.app.bind("<F2>", lambda e: self.open_payment_modal(), add="+")
        self.app.bind("<F3>", lambda e: self.apply_discount_to_all(), add="+")
        self.app.bind("<F4>", lambda e: self.remove_all_discounts(), add="+")

    def destroy(self):
        try:
            self.app.unbind("<F1>")
            self.app.unbind("<F2>")
            self.app.unbind("<F3>")
            self.app.unbind("<F4>")
        except Exception:
            pass
        self._close_payment_window()
        self._close_preview_window()
        self._close_summary_window()
        super().destroy()

    def _configure_styles(self):
        style = ttk.Style()
        style.configure(
            "POSCard.TLabelframe",
            padding=12,
            background=PALETTE["white"],
            bordercolor=PALETTE["gray_border"],
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "POSCard.TLabelframe.Label",
            background=PALETTE["white"],
            foreground=PALETTE["blue_dark"],
            font=FONTS["subheader"],
        )
        style.configure("POSSection.TLabel", font=("Segoe UI", 11, "bold"), foreground=PALETTE["blue_dark"], background=PALETTE["white"])
        style.configure("POSMuted.TLabel", foreground=PALETTE["gray_text"], background=PALETTE["white"], font=FONTS["small"])

        style.configure(
            "POSPrimary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 8),
            relief="flat",
            borderwidth=0,
            background=PALETTE["blue_primary"],
            foreground=PALETTE["white"],
        )
        style.map("POSPrimary.TButton", background=[("active", PALETTE["blue_dark"])])

        style.configure(
            "POSDanger.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 8),
            relief="flat",
            borderwidth=0,
            background=PALETTE["danger"],
            foreground=PALETTE["white"],
        )
        style.map("POSDanger.TButton", background=[("active", "#8F1C13")])

        style.configure(
            "POSSuccess.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 10),
            relief="flat",
            borderwidth=0,
            background=PALETTE["success"],
            foreground=PALETTE["white"],
        )
        style.map("POSSuccess.TButton", background=[("active", "#055A3B")])

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        header.grid_columnconfigure(1, weight=1)

        ttk.Label(header, text="Punto de venta (POS)", style="Header.TLabel").grid(row=0, column=0, sticky="w")

        mode_frame = ttk.LabelFrame(header, text="Modo de venta", padding=8)
        mode_frame.grid(row=0, column=1, sticky="e")
        for text, value in (("Normal", "NORMAL"), ("Especial (Mayorista)", "ESPECIAL")):
            ttk.Radiobutton(mode_frame, text=text, value=value, variable=self.sale_mode_var, command=self.on_sale_mode_change).pack(side="left", padx=8)

        self.pos_canvas = tk.Canvas(self, highlightthickness=0, bg=PALETTE["blue_soft"])
        self.pos_canvas.grid(row=1, column=0, sticky="nsew")
        pos_scroll = ttk.Scrollbar(self, orient="vertical", command=self.pos_canvas.yview)
        pos_scroll.grid(row=1, column=1, sticky="ns")
        self.pos_canvas.configure(yscrollcommand=pos_scroll.set)
        self.pos_canvas.bind(
            "<Enter>",
            lambda _e: self.pos_canvas.bind_all(
                "<MouseWheel>",
                lambda ev: self.pos_canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units"),
            ),
        )
        self.pos_canvas.bind("<Leave>", lambda _e: self.pos_canvas.unbind_all("<MouseWheel>"))

        body = ttk.Frame(self.pos_canvas, style="App.TFrame", padding=(0, 2, 0, 0))
        self.pos_canvas_window = self.pos_canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _e: self.pos_canvas.configure(scrollregion=self.pos_canvas.bbox("all")))
        self.pos_canvas.bind("<Configure>", lambda e: self.pos_canvas.itemconfig(self.pos_canvas_window, width=e.width))

        body.grid_columnconfigure(0, weight=5)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        self.catalog_frame = ttk.LabelFrame(body, text="Catalogo de productos", style="POSCard.TLabelframe")
        self.catalog_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        right_panel = ttk.Frame(body, style="App.TFrame")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(0, weight=1, minsize=360)
        right_panel.grid_rowconfigure(1, weight=1, minsize=280)
        right_panel.grid_columnconfigure(0, weight=1)

        self.cart_frame = ttk.LabelFrame(right_panel, text="Carrito de compras", style="POSCard.TLabelframe")
        self.cart_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        self.checkout_frame = ttk.LabelFrame(right_panel, text="Cobro / pago", style="POSCard.TLabelframe")
        self.checkout_frame.grid(row=1, column=0, sticky="nsew")

        self._build_catalog_ui()
        self._build_cart_ui()
        self._build_checkout_ui()

    def _create_scrollable_section(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(parent, highlightthickness=0, bg=PALETTE["white"])
        canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=y_scroll.set)
        canvas.bind(
            "<Enter>",
            lambda _e: canvas.bind_all(
                "<MouseWheel>",
                lambda ev: canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units"),
            ),
        )
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        content = ttk.Frame(canvas, style="Surface.TFrame")
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
        return content

    def _build_catalog_ui(self):
        search_frame = ttk.Frame(self.catalog_frame)
        search_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(search_frame, text="Buscar:").pack(side="left", padx=(0, 6))
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_products())
        ttk.Button(search_frame, text="F1", width=3, command=self.focus_search).pack(side="left", padx=6)
        ttk.Button(search_frame, text="Refrescar", style="POSPrimary.TButton", command=self.load_products).pack(side="left")

        tree_frame = ttk.Frame(self.catalog_frame)
        tree_frame.pack(fill="both", expand=True)
        self.products_tree = ttk.Treeview(tree_frame, columns=("Producto", "Stock", "Precio"), show="headings", height=12)
        for col, text, width, anchor in (("Producto", "Producto", 260, "w"), ("Stock", "Stock", 80, "center"), ("Precio", "Precio", 110, "center")):
            self.products_tree.heading(col, text=text)
            self.products_tree.column(col, width=width, anchor=anchor)
        y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.products_tree.yview)
        x_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.products_tree.xview)
        self.products_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.products_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.products_tree.bind("<<TreeviewSelect>>", self.on_product_select)
        self.products_tree.bind("<Double-1>", lambda e: self.add_selected_product())

        detail_frame = ttk.LabelFrame(self.catalog_frame, text="Detalle", padding=8)
        detail_frame.pack(fill="x", pady=(8, 0))
        self.detail_text = tk.Text(detail_frame, height=7, wrap=tk.WORD, font=("Segoe UI", 9), relief="solid", borderwidth=1)
        self.detail_text.pack(fill="both", expand=True)
        self.detail_text.insert("1.0", "Seleccione un producto del catalogo.")
        self.detail_text.config(state="disabled")

        add_frame = ttk.Frame(self.catalog_frame)
        add_frame.pack(fill="x", pady=(8, 0))
        qty_box = ttk.Frame(add_frame)
        qty_box.pack(fill="x", pady=(0, 6))
        ttk.Label(qty_box, text="Cantidad:").pack(side="left")
        self.qty_var = tk.IntVar(value=1)
        self.qty_spin = ttk.Spinbox(qty_box, from_=1, to=10000, textvariable=self.qty_var, width=8)
        self.qty_spin.pack(side="left", padx=6)
        ttk.Label(qty_box, text="Descuento:").pack(side="left", padx=(14, 4))
        self.discount_combo = ttk.Combobox(qty_box, textvariable=self.discount_var, state="readonly", width=22)
        self.discount_combo.pack(side="left", fill="x", expand=True)
        self.discount_combo.bind("<<ComboboxSelected>>", self.apply_selected_discount)
        ttk.Button(add_frame, text="Agregar al carrito", style="POSPrimary.TButton", command=self.add_selected_product).pack(fill="x")

    def _build_cart_ui(self):
        cart_panel = self._create_scrollable_section(self.cart_frame)

        header = ttk.Frame(cart_panel)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(header, textvariable=self.cart_items_var, style="POSSection.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="La cantidad se actualiza al instante.", style="POSMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.cart_tree = ttk.Treeview(
            cart_panel,
            columns=("Producto", "Cant", "PrecioU", "Desc", "Subtotal"),
            show="headings",
            height=16,
        )
        for col, text, width, anchor in (
            ("Producto", "Producto", 220, "w"),
            ("Cant", "Cant.", 70, "center"),
            ("PrecioU", "P. Unit. (HNL)", 120, "e"),
            ("Desc", "Desc.", 70, "center"),
            ("Subtotal", "Subtotal (HNL)", 140, "e"),
        ):
            self.cart_tree.heading(col, text=text)
            self.cart_tree.column(col, width=width, anchor=anchor)
        cart_scroll = ttk.Scrollbar(cart_panel, orient="vertical", command=self.cart_tree.yview)
        cart_x_scroll = ttk.Scrollbar(cart_panel, orient="horizontal", command=self.cart_tree.xview)
        self.cart_tree.configure(yscrollcommand=cart_scroll.set, xscrollcommand=cart_x_scroll.set)
        self.cart_tree.grid(row=1, column=0, sticky="nsew")
        cart_scroll.grid(row=1, column=1, sticky="ns")
        cart_x_scroll.grid(row=2, column=0, sticky="ew")
        cart_panel.grid_rowconfigure(1, weight=1)
        cart_panel.grid_columnconfigure(0, weight=1)
        self.cart_tree.bind("<<TreeviewSelect>>", self.on_cart_select)

        actions = ttk.Frame(cart_panel)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Button(actions, text="-1", width=4, style="POSPrimary.TButton", command=self.decrease_selected_quantity).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="+1", width=4, style="POSPrimary.TButton", command=self.increase_selected_quantity).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Eliminar", style="POSDanger.TButton", command=self.remove_from_cart).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Limpiar carrito", style="POSPrimary.TButton", command=self.clear_cart).pack(side="left")

        self.discount_info_label = ttk.Label(cart_panel, text="", foreground="#666", wraplength=340, justify="left")
        self.discount_info_label.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 8))

        editor = ttk.LabelFrame(cart_panel, text="Cantidad", padding=8)
        editor.grid(row=5, column=0, columnspan=2, sticky="ew")
        editor.columnconfigure(2, weight=1)
        ttk.Label(editor, textvariable=self.selected_cart_name_var, style="POSSection.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(editor, textvariable=self.cart_hint_var, style="POSMuted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 8))
        ttk.Label(editor, text="Cantidad:").grid(row=2, column=0, sticky="w")
        self.edit_qty_spin = ttk.Spinbox(editor, from_=1, to=10000, textvariable=self.cart_editor_var, width=10, command=self.on_quantity_editor_change)
        self.edit_qty_spin.grid(row=2, column=1, sticky="w", padx=(6, 8))
        self.edit_qty_spin.bind("<KeyRelease>", self.on_quantity_editor_change)
        ttk.Label(editor, textvariable=self.selected_cart_discount_var).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(editor, textvariable=self.selected_cart_subtotal_var).grid(row=3, column=1, columnspan=2, sticky="w", pady=(8, 0))
        self.edit_qty_spin.state(["disabled"])

    def _build_checkout_ui(self):
        checkout_panel = self._create_scrollable_section(self.checkout_frame)
        checkout_panel.grid_columnconfigure(0, weight=1)
        checkout_panel.grid_rowconfigure(5, weight=1)

        client_frame = ttk.LabelFrame(checkout_panel, text="Cliente", padding=8)
        client_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        row = ttk.Frame(client_frame)
        row.pack(fill="x")
        self.client_combo = ttk.Combobox(row, textvariable=self.client_var, state="readonly")
        self.client_combo.pack(side="left", fill="x", expand=True)
        self.client_combo.bind("<<ComboboxSelected>>", self.on_client_select)
        ttk.Button(row, text="Refrescar", width=10, style="POSPrimary.TButton", command=self.load_clients).pack(side="left", padx=6)

        self.total_label = ttk.Label(
            checkout_panel,
            textvariable=self.total_display_var,
            font=("Segoe UI", 26, "bold"),
            foreground=PALETTE["danger"],
            background=PALETTE["white"],
        )
        ttk.Label(checkout_panel, text="TOTAL A PAGAR", style="POSSection.TLabel").grid(row=1, column=0, sticky="w")
        self.total_label.grid(row=2, column=0, sticky="w", pady=(2, 8))

        pay_frame = ttk.LabelFrame(checkout_panel, text="Estado de cobro", padding=8)
        pay_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(pay_frame, text="Metodo de pago:").grid(row=0, column=0, sticky="w")
        self.payment_method_combo = ttk.Combobox(
            pay_frame,
            textvariable=self.payment_method_var,
            state="readonly",
            values=("EFECTIVO", "TARJETA", "TRANSFERENCIA", "QR", "CREDITO", "NO_DEFINIDO"),
        )
        self.payment_method_combo.grid(row=1, column=0, sticky="ew", pady=(2, 6))
        self.payment_method_combo.current(0)
        ttk.Label(pay_frame, text="Monto recibido:").grid(row=2, column=0, sticky="w")
        ttk.Label(pay_frame, textvariable=self.monto_pagado_var).grid(row=3, column=0, sticky="w", pady=(2, 4))
        ttk.Label(pay_frame, text="Cambio:").grid(row=4, column=0, sticky="w")
        self.vuelto_label = ttk.Label(
            pay_frame,
            textvariable=self.vuelto_display_var,
            font=("Segoe UI", 16, "bold"),
            foreground=PALETTE["success"],
            background=PALETTE["white"],
        )
        self.vuelto_label.grid(row=5, column=0, sticky="w", pady=(2, 0))
        pay_frame.grid_columnconfigure(0, weight=1)

        self.validation_label = ttk.Label(checkout_panel, textvariable=self.status_var, wraplength=320, foreground=PALETTE["gray_text"], background=PALETTE["white"])
        self.validation_label.grid(row=4, column=0, sticky="ew", pady=(0, 8))

        preview_mode_frame = ttk.LabelFrame(checkout_panel, text="Formato de recibo", padding=8)
        preview_mode_frame.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        ttk.Radiobutton(preview_mode_frame, text="Ticket", value="ticket", variable=self.preview_mode_var, command=self.refresh_preview).pack(side="left")
        ttk.Radiobutton(preview_mode_frame, text="Carta", value="letter", variable=self.preview_mode_var, command=self.refresh_preview).pack(side="left", padx=(8, 0))
        ttk.Label(preview_mode_frame, textvariable=self.preview_label_var, style="POSMuted.TLabel").pack(side="right")

        action_frame = ttk.Frame(checkout_panel)
        action_frame.grid(row=6, column=0, sticky="ew")
        self.preview_button = ttk.Button(action_frame, text="Vista previa", style="POSPrimary.TButton", command=self.toggle_preview)
        self.preview_button.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.finalize_button = ttk.Button(action_frame, text="Vender", style="POSSuccess.TButton", command=self.open_payment_modal)
        self.finalize_button.pack(side="left", fill="x", expand=True, padx=(4, 0))

    def increase_selected_quantity(self):
        self._adjust_selected_quantity(1)

    def decrease_selected_quantity(self):
        self._adjust_selected_quantity(-1)

    def _adjust_selected_quantity(self, delta):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto del carrito.")
            return

        prod_id = int(selected[0])
        item = self.cart.get(prod_id)
        if not item:
            return

        new_qty = int(item["cantidad"]) + int(delta)
        if new_qty <= 0:
            self.remove_from_cart()
            return

        stock = self.product_index.get(prod_id, {}).get("stock", 0)
        if new_qty > stock:
            self.status_var.set(f"Stock insuficiente. Disponible: {stock}.")
            return

        item["cantidad"] = new_qty
        self.recalculate_item_discount(prod_id)
        self.pending_sale = None
        self.update_cart_display()
        self.cart_tree.selection_set(str(prod_id))
        self.cart_tree.focus(str(prod_id))
        self.refresh_preview()
        self.status_var.set(f"Cantidad actualizada para {item['nombre']}.")

    def focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)

    def open_product_search(self):
        self.focus_search()

    def on_sale_mode_change(self):
        self.pending_sale = None
        self.recalculate_cart_discounts()
        self.update_cart_display()
        self.refresh_preview()

    def load_pos_context(self, *, load_products=True, load_clients=True, load_discounts=True):
        context = self.load_pos_context_use_case.execute(
            load_products=load_products,
            load_clients=load_clients,
            load_discounts=load_discounts,
        )
        if load_discounts:
            self._apply_discount_context(context.discounts)
        if load_products:
            self._render_products(context.products)
        if load_clients:
            self._apply_client_context(context.clients)

    def load_discounts(self):
        self.load_pos_context(load_products=False, load_clients=False, load_discounts=True)

    def _apply_discount_context(self, discounts):
        options = ["Sin descuento"]
        self.discount_data = {0: {"id": 0, "nombre": "Sin descuento", "tipo": None, "porcentaje": 0.0}}
        self.discount_by_type = {}

        for idx, discount in enumerate(discounts, start=1):
            disc_id = int(discount["id"])
            nombre = str(discount["nombre"] or "")
            tipo = discount["tipo"]
            porcentaje = float(discount["porcentaje"] or 0)
            self.discount_data[idx] = {"id": disc_id, "nombre": nombre, "tipo": tipo, "porcentaje": porcentaje}
            options.append(f"{nombre} - {int(round(porcentaje * 100))}%")
            if tipo:
                self.discount_by_type[str(tipo).strip().lower()] = porcentaje

        self.discount_combo["values"] = options
        self.discount_combo.current(0)

    def load_products(self):
        self.product_index.clear()
        self.load_pos_context(load_products=True, load_clients=False, load_discounts=False)

    def _render_products(self, rows):
        self.product_index.clear()
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)

        search_term = self.search_var.get().strip().lower()
        for row in rows:
            prod_id = int(row["id"])
            nombre = row["nombre"]
            descripcion = row.get("descripcion") or ""
            precio = float(row.get("precio") or 0)
            stock = int(row.get("stock") or 0)
            codigo_producto = str(row.get("codigo_producto") or "")
            if search_term:
                haystack = f"{nombre} {descripcion or ''} {codigo_producto}".lower()
                if search_term not in haystack:
                    continue

            self.product_index[int(prod_id)] = {
                "id": int(prod_id),
                "nombre": nombre,
                "descripcion": descripcion or "",
                "precio": float(precio or 0),
                "stock": int(stock or 0),
                "codigo_producto": str(codigo_producto or ""),
            }
            self.products_tree.insert("", "end", iid=str(prod_id), values=(nombre, stock, format_hnl(precio)))

    def filter_products(self):
        self.load_products()

    def on_product_select(self, event=None):
        selected = self.products_tree.selection()
        if not selected:
            return

        prod_id = int(selected[0])
        self.selected_product_id = prod_id
        data = self.product_index.get(prod_id)
        if not data:
            return

        self._set_detail_text(
            f"Producto: {data['nombre']}\n"
            f"Codigo: {data.get('codigo_producto') or 'N/D'}\n"
            f"Stock: {data['stock']}\n"
            f"Precio: {format_hnl(data['precio'])}\n\n"
            f"Descripcion:\n{data['descripcion'] or 'Sin descripcion'}"
        )

    def _set_detail_text(self, text):
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", text)
        self.detail_text.config(state="disabled")

    def add_selected_product(self):
        selected = self.products_tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto del catalogo.")
            return

        prod_id = int(selected[0])
        qty = int(self.qty_var.get() or 0)
        if qty <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a 0.")
            return

        data = self.product_index.get(prod_id)
        if not data:
            messagebox.showerror("Error", "No fue posible cargar el producto.")
            return

        current_qty = self.cart.get(prod_id, {}).get("cantidad", 0)
        if current_qty + qty > data["stock"]:
            messagebox.showerror("Stock insuficiente", f"Solo hay {data['stock']} unidades disponibles.")
            return

        item = self.cart.get(prod_id)
        if item:
            item["cantidad"] += qty
        else:
            item = {
                "producto_id": prod_id,
                "nombre": data["nombre"],
                "cantidad": qty,
                "precio_unitario": data["precio"],
                "descuento_porcentaje": 0.0,
                "manual": False,
                "manual_label": "",
                "auto_label": "",
            }
            self.cart[prod_id] = item

        self.recalculate_item_discount(prod_id)
        self.pending_sale = None
        self.qty_var.set(1)
        self.update_cart_display()
        self.refresh_preview()
        self.status_var.set(f"{data['nombre']} agregado al carrito.")

    def quick_add(self):
        self.add_selected_product()

    def on_cart_select(self, event=None):
        selected = self.cart_tree.selection()
        if not selected:
            self._set_cart_editor_state(None)
            return

        prod_id = int(selected[0])
        item = self.cart.get(prod_id)
        if item:
            self.status_var.set(f"Seleccionado: {item['nombre']}.")
            self._set_cart_editor_state(prod_id)

    def on_quantity_editor_change(self, event=None):
        selected = self.cart_tree.selection()
        if not selected:
            return

        prod_id = int(selected[0])
        item = self.cart.get(prod_id)
        if not item:
            return

        value = str(self.cart_editor_var.get()).strip()
        if not value:
            return

        try:
            new_qty = int(value)
        except ValueError:
            self.status_var.set("Ingrese una cantidad valida.")
            return

        if new_qty <= 0:
            self.status_var.set("La cantidad debe ser mayor a 0.")
            return

        stock = self.product_index.get(prod_id, {}).get("stock", 0)
        if new_qty > stock:
            self.status_var.set(f"Stock insuficiente. Disponible: {stock}.")
            return

        if new_qty == int(item["cantidad"]):
            self._set_cart_editor_state(prod_id)
            return

        item["cantidad"] = new_qty
        self.recalculate_item_discount(prod_id)
        self.pending_sale = None
        self.update_cart_display()
        self.cart_tree.selection_set(str(prod_id))
        self.cart_tree.focus(str(prod_id))
        self.refresh_preview()
        self.status_var.set(f"Cantidad actualizada para {item['nombre']}.")

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto del carrito.")
            return

        prod_id = int(selected[0])
        if prod_id in self.cart:
            del self.cart[prod_id]
            self.pending_sale = None
            self.update_cart_display()
            self.refresh_preview()
            self.status_var.set("Producto eliminado del carrito.")
            self._set_cart_editor_state(None)

    def clear_cart(self, silent=False):
        if not self.cart:
            return
        if not silent and not messagebox.askyesno("Confirmar", "Limpiar todo el carrito?"):
            return

        self.cart.clear()
        self.pending_sale = None
        self.total_var.set(0.0)
        self.total_display_var.set(format_hnl(0))
        self.monto_pagado_var.set("0.00")
        self.vuelto_var.set(0.0)
        self.vuelto_display_var.set(format_hnl(0))
        self.payment_method_var.set("EFECTIVO")
        self.client_var.set("Cliente General")
        self.selected_client_id = None
        self.selected_client_is_wholesale = False
        self.update_cart_display()
        self._set_cart_editor_state(None)
        self.calculate_change()
        self.refresh_preview()

    def load_clients(self):
        self.load_pos_context(load_products=False, load_clients=True, load_discounts=False)

    def _apply_client_context(self, clients):
        display_names = ["Cliente General"]
        self.client_data = {"Cliente General": {"id": None, "mayorista": False}}

        for client in clients:
            client_id = int(client["id"])
            nombre = str(client["nombre"] or "")
            apellido = str(client["apellido"] or "")
            mayorista = bool(client["mayorista"])
            label = f"{apellido}, {nombre}"
            if mayorista:
                label += " (Mayorista)"
            display_names.append(label)
            self.client_data[label] = {"id": client_id, "mayorista": bool(mayorista)}

        self.client_combo["values"] = display_names
        current_label = self.client_var.get()
        if current_label not in self.client_data:
            self.client_var.set("Cliente General")
            self.selected_client_id = None
            self.selected_client_is_wholesale = False
            self.client_combo.current(0)
        else:
            self.client_combo.current(display_names.index(current_label))

    def on_client_select(self, event=None):
        selected = self.client_var.get()
        data = self.client_data.get(selected, self.client_data["Cliente General"])
        self.selected_client_id = data["id"]
        self.selected_client_is_wholesale = bool(data["mayorista"])
        self.pending_sale = None
        self.recalculate_cart_discounts()
        self.update_cart_display()
        self.refresh_preview()
        self.calculate_change()

    def get_discount_pct_by_type(self, discount_type, default=0.0):
        return float(self.discount_by_type.get(str(discount_type).strip().lower(), default) or 0)

    def recalculate_item_discount(self, prod_id):
        item = self.cart.get(prod_id)
        if not item or item.get("manual"):
            return

        qty = int(item["cantidad"])
        auto_docena = self.get_discount_pct_by_type("Docena", 0.10) if qty >= 12 else 0.0
        wholesale_context = self.selected_client_is_wholesale or self.sale_mode_var.get() == "ESPECIAL"
        auto_mayorista = self.get_discount_pct_by_type("Mayorista", 0.15) if wholesale_context else 0.0

        best = max(auto_docena, auto_mayorista)
        if auto_docena > 0 and auto_mayorista > 0:
            if abs(auto_docena - auto_mayorista) < 1e-9:
                source = "Docena/Majorista"
            else:
                source = "Docena" if auto_docena > auto_mayorista else "Mayorista"
        elif auto_docena > 0:
            source = "Docena"
        elif auto_mayorista > 0:
            source = "Mayorista"
        else:
            source = ""

        item["descuento_porcentaje"] = best
        item["manual_label"] = ""
        item["auto_label"] = source

    def recalculate_cart_discounts(self):
        for prod_id in list(self.cart):
            self.recalculate_item_discount(prod_id)

    def apply_selected_discount(self, event=None):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto del carrito.")
            return

        prod_id = int(selected[0])
        item = self.cart.get(prod_id)
        if not item:
            return

        discount_idx = self.discount_combo.current()
        discount_info = self.discount_data.get(discount_idx)
        if not discount_info:
            return

        pct = float(discount_info["porcentaje"] or 0)
        if pct <= 0:
            item["manual"] = False
            item["manual_label"] = ""
            self.recalculate_item_discount(prod_id)
        else:
            item["manual"] = True
            item["manual_label"] = discount_info["nombre"]
            item["descuento_porcentaje"] = pct
            item["auto_label"] = ""

        self.update_cart_display()
        self.refresh_preview()
        self.status_var.set(f"Descuento {'removido' if pct <= 0 else discount_info['nombre']} en {item['nombre']}.")
        self.pending_sale = None

    def apply_discount_to_all(self):
        if not self.cart:
            messagebox.showwarning("Advertencia", "El carrito esta vacio.")
            return

        discount_idx = self.discount_combo.current()
        discount_info = self.discount_data.get(discount_idx)
        if not discount_info:
            return

        pct = float(discount_info["porcentaje"] or 0)
        if pct > 0 and not messagebox.askyesno("Confirmar", f"Aplicar '{discount_info['nombre']}' ({int(round(pct * 100))}%) a todo el carrito?"):
            return

        for prod_id in self.cart:
            item = self.cart[prod_id]
            if pct <= 0:
                item["manual"] = False
                item["manual_label"] = ""
                self.recalculate_item_discount(prod_id)
            else:
                item["manual"] = True
                item["manual_label"] = discount_info["nombre"]
                item["descuento_porcentaje"] = pct
                item["auto_label"] = ""

        self.update_cart_display()
        self.refresh_preview()
        self.status_var.set("Descuento masivo aplicado.")
        self.pending_sale = None

    def remove_all_discounts(self):
        if not self.cart:
            messagebox.showwarning("Advertencia", "El carrito esta vacio.")
            return

        if not messagebox.askyesno("Confirmar", "Remover todos los descuentos manuales?"):
            return

        for prod_id in self.cart:
            item = self.cart[prod_id]
            item["manual"] = False
            item["manual_label"] = ""
            self.recalculate_item_discount(prod_id)

        self.discount_combo.current(0)
        self.update_cart_display()
        self.refresh_preview()
        self.status_var.set("Descuentos removidos.")
        self.pending_sale = None

    def update_cart_display(self):
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)

        line_total = 0.0
        auto_count = 0
        manual_count = 0
        info_sources = set()

        for prod_id, item in self.cart.items():
            qty = int(item["cantidad"])
            price = float(item["precio_unitario"])
            pct = float(item.get("descuento_porcentaje", 0))
            subtotal = (price * qty) * (1 - pct)
            line_total += subtotal

            if item.get("manual"):
                manual_count += 1
                info_sources.add("Manual")
                desc_text = f"{int(round(pct * 100))}%"
            elif pct > 0:
                auto_count += 1
                info_sources.add(item.get("auto_label") or "Auto")
                desc_text = f"{int(round(pct * 100))}%"
            else:
                desc_text = "0%"

            self.cart_tree.insert(
                "",
                "end",
                iid=str(prod_id),
                values=(item["nombre"], qty, format_hnl(price), desc_text, format_hnl(subtotal)),
            )

        invoice = self._calculate_invoice_totals(validate_payment=False)
        self.total_var.set(round(invoice.total, 2))
        self.total_display_var.set(format_hnl(invoice.total))
        if self.cart:
            units = sum(int(item["cantidad"]) for item in self.cart.values())
            self.cart_items_var.set(f"{units} unidades en {len(self.cart)} productos")
        else:
            self.cart_items_var.set("0 productos")

        if manual_count:
            source = "Manual"
        elif auto_count:
            source = "/".join(sorted(info_sources)) if info_sources else "Auto"
        else:
            source = "Sin descuento"

        self.discount_info_label.config(text=f"Desc.: {source}. Auto: Docena/Majorista cuando aplique. Manual no se sobrescribe.", foreground="#2e7d32" if line_total else "#666")
        self._refresh_cart_editor()
        self.calculate_change()

    def calculate_change(self, event=None):
        invoice = self._calculate_invoice_totals(validate_payment=False)
        total = float(invoice.total)
        self.total_var.set(total)
        self.total_display_var.set(format_hnl(total))

        metodo_pago = (self.payment_method_var.get() or "NO_DEFINIDO").upper()
        if metodo_pago == "TRANSFERENCIA":
            self.monto_pagado_var.set(f"{invoice.monto_recibido:.2f}")
            if self._widget_exists(getattr(self, "monto_entry", None)):
                self.monto_entry.state(["disabled"])
        else:
            if self._widget_exists(getattr(self, "monto_entry", None)):
                self.monto_entry.state(["!disabled"])

        self.vuelto_var.set(round(invoice.vuelto, 2))
        self.vuelto_display_var.set(format_hnl(invoice.vuelto))

        if total <= 0:
            self.status_var.set("Agregue productos al carrito.")
            self.finalize_button.state(["disabled"])
        elif invoice.validation_errors and metodo_pago == "EFECTIVO":
            faltante = total - self._parse_float(self.monto_pagado_var.get())
            self.status_var.set(f"Faltan {format_hnl(faltante)}. Presione Vender para abrir el cobro.")
            self.finalize_button.state(["!disabled"])
        elif metodo_pago == "TRANSFERENCIA":
            self.status_var.set("Transferencia validada. El monto recibido se ajusta al total y el vuelto es L 0.00.")
            self.finalize_button.state(["!disabled"])
        else:
            self.status_var.set("Pago valido. Puede continuar con Vender.")
            self.finalize_button.state(["!disabled"])

        if self.preview_visible:
            self.refresh_preview()
        if self.payment_modal_status_var is not None:
            self.payment_modal_status_var.set(self.status_var.get())

    def toggle_preview(self):
        if self.preview_visible:
            self._close_preview_window()
        else:
            self._open_preview_window()

    def show_receipt_preview(self, *args, **kwargs):
        if not self.preview_visible:
            self.toggle_preview()
        self.refresh_preview()

    def _build_sale_snapshot(self, validate_payment=True):
        invoice = self._calculate_invoice_totals(validate_payment=validate_payment)
        return {
            "venta_id": f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}",
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": float(invoice.total),
            "pagado": float(invoice.monto_recibido),
            "vuelto": float(invoice.vuelto),
            "cliente_id": self.selected_client_id,
            "metodo_pago": self.payment_method_var.get() or "NO_DEFINIDO",
            "modo": self.sale_mode_var.get(),
            "cart_snapshot": {prod_id: dict(item) for prod_id, item in self.cart.items()},
            "tax_included": self._invoice_prices_include_tax(),
        }

    def refresh_preview(self):
        if not self.preview_visible or not self.preview_text or not self.preview_text.winfo_exists():
            return

        snapshot = self.pending_sale or self._build_sale_snapshot(validate_payment=False)
        if self.preview_mode_var.get() == "letter":
            content = self.format_receipt_letter(
                snapshot["venta_id"],
                snapshot["total"],
                snapshot["pagado"],
                snapshot["vuelto"],
                snapshot["fecha"],
                snapshot["cart_snapshot"],
                snapshot.get("cliente_id"),
                snapshot.get("metodo_pago"),
            )
        else:
            content = self.format_receipt_ticket(
                snapshot["venta_id"],
                snapshot["total"],
                snapshot["pagado"],
                snapshot["vuelto"],
                snapshot["fecha"],
                snapshot["cart_snapshot"],
                snapshot.get("cliente_id"),
                snapshot.get("metodo_pago"),
            )

        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", content)
        self.preview_text.config(state="disabled")

    def finalize_sale(self):
        self.open_payment_modal()

    def open_payment_modal(self):
        if not self.cart:
            messagebox.showwarning("Advertencia", "El carrito esta vacio.")
            return
        self.calculate_change()
        self._open_payment_window()

    def _open_payment_window(self):
        if self.payment_window and self.payment_window.winfo_exists():
            self.payment_window.deiconify()
            self.payment_window.lift()
            return

        self.payment_window = tk.Toplevel(self)
        self.payment_window.title("Cobro rapido")
        self.payment_window.transient(self.winfo_toplevel())
        self.payment_window.grab_set()
        self.payment_window.resizable(False, False)
        center_window(self.payment_window, 560, 420, parent=self.winfo_toplevel())
        self.payment_window.protocol("WM_DELETE_WINDOW", self._close_payment_window)

        wrapper = ttk.Frame(self.payment_window, padding=12)
        wrapper.pack(fill="both", expand=True)
        wrapper.columnconfigure(0, weight=1)

        ttk.Label(wrapper, text="Cobro de venta", style="POSSection.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(wrapper, text=f"Total a cobrar: {self.total_display_var.get()}", style="POSSection.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 8))

        fields = ttk.LabelFrame(wrapper, text="Datos de pago", padding=10)
        fields.grid(row=2, column=0, sticky="ew")
        fields.grid_columnconfigure(0, weight=1)

        ttk.Label(fields, text="Metodo de pago:").grid(row=0, column=0, sticky="w")
        payment_combo = ttk.Combobox(
            fields,
            textvariable=self.payment_method_var,
            state="readonly",
            values=("EFECTIVO", "TARJETA", "TRANSFERENCIA", "QR", "CREDITO", "NO_DEFINIDO"),
        )
        payment_combo.grid(row=1, column=0, sticky="ew", pady=(2, 8))
        payment_combo.bind("<<ComboboxSelected>>", self.calculate_change)
        ttk.Label(fields, text="Monto recibido:").grid(row=2, column=0, sticky="w")
        self.monto_entry = ttk.Entry(fields, textvariable=self.monto_pagado_var)
        self.monto_entry.grid(row=3, column=0, sticky="ew", pady=(2, 8))
        self.monto_entry.bind("<KeyRelease>", self.calculate_change)

        ttk.Label(fields, text="Cambio:").grid(row=4, column=0, sticky="w")
        ttk.Label(
            fields,
            textvariable=self.vuelto_display_var,
            font=("Segoe UI", 16, "bold"),
            foreground=PALETTE["success"],
            background=PALETTE["white"],
        ).grid(row=5, column=0, sticky="w", pady=(2, 0))

        self.payment_modal_status_var.set(self.status_var.get())
        ttk.Label(wrapper, textvariable=self.payment_modal_status_var, wraplength=510, style="POSMuted.TLabel").grid(row=3, column=0, sticky="ew", pady=(8, 6))

        actions = ttk.Frame(wrapper)
        actions.grid(row=4, column=0, sticky="e", pady=(8, 0))
        ttk.Button(actions, text="Cancelar", style="POSDanger.TButton", command=self._close_payment_window).pack(side="right")
        ttk.Button(actions, text="Continuar", style="POSSuccess.TButton", command=self._continue_from_payment_modal).pack(side="right", padx=(0, 8))

        self.monto_entry.focus_set()
        self.monto_entry.selection_range(0, tk.END)
        self.calculate_change()

    def _continue_from_payment_modal(self):
        invoice = self._calculate_invoice_totals(validate_payment=False)
        if invoice.total <= 0:
            self.status_var.set("Agregue productos al carrito.")
            self.payment_modal_status_var.set(self.status_var.get())
            return
        if invoice.validation_errors and (self.payment_method_var.get() or "NO_DEFINIDO").upper() == "EFECTIVO":
            faltante = invoice.total - self._parse_float(self.monto_pagado_var.get())
            self.status_var.set(f"Faltan {format_hnl(faltante)} para completar el pago.")
            self.payment_modal_status_var.set(self.status_var.get())
            return

        self._close_payment_window()
        self.open_sale_summary_modal()

    def open_sale_summary_modal(self):
        if not self.cart:
            messagebox.showwarning("Advertencia", "El carrito esta vacio.")
            return
        invoice = self._calculate_invoice_totals(validate_payment=False)
        if invoice.validation_errors and (self.payment_method_var.get() or "NO_DEFINIDO").upper() == "EFECTIVO":
            faltante = invoice.total - self._parse_float(self.monto_pagado_var.get())
            messagebox.showwarning("Pago incompleto", f"Faltan {format_hnl(faltante)} para completar el pago.")
            return

        self.pending_sale = self._build_sale_snapshot()
        self.refresh_preview()

        self._close_summary_window()
        self.summary_window = tk.Toplevel(self)
        self.summary_window.title("Resumen de venta")
        self.summary_window.transient(self.winfo_toplevel())
        self.summary_window.grab_set()
        self.summary_window.resizable(True, True)
        center_window(self.summary_window, 920, 620, parent=self.winfo_toplevel())
        self.summary_window.protocol("WM_DELETE_WINDOW", self._close_summary_window)

        container = ttk.Frame(self.summary_window, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Resumen de venta (previo a confirmar)", style="POSSection.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            header,
            text=(
                f"Cliente: {self.client_var.get()} | Modo: {self.sale_mode_var.get()} | "
                f"Metodo: {self.payment_method_var.get()}"
            ),
            style="POSMuted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        body = ttk.Frame(container)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        columns = ("producto", "cantidad", "precio", "desc", "subtotal")
        summary_tree = ttk.Treeview(body, columns=columns, show="headings", height=14)
        summary_tree.heading("producto", text="Producto")
        summary_tree.heading("cantidad", text="Cantidad")
        summary_tree.heading("precio", text="Precio unitario")
        summary_tree.heading("desc", text="Descuento")
        summary_tree.heading("subtotal", text="Subtotal")
        summary_tree.column("producto", width=320, anchor="w")
        summary_tree.column("cantidad", width=110, anchor="center")
        summary_tree.column("precio", width=160, anchor="e")
        summary_tree.column("desc", width=120, anchor="center")
        summary_tree.column("subtotal", width=170, anchor="e")

        y_scroll = ttk.Scrollbar(body, orient="vertical", command=summary_tree.yview)
        x_scroll = ttk.Scrollbar(body, orient="horizontal", command=summary_tree.xview)
        summary_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        summary_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        sale = self.pending_sale
        cart_data = sale["cart_snapshot"]
        for item in cart_data.values():
            qty = int(item["cantidad"])
            price = float(item["precio_unitario"])
            pct = float(item.get("descuento_porcentaje", 0))
            subtotal = (price * qty) * (1 - pct)
            summary_tree.insert(
                "",
                "end",
                values=(
                    item["nombre"],
                    qty,
                    format_hnl(price),
                    f"{int(round(pct * 100))}%",
                    format_hnl(subtotal),
                ),
            )

        footer = ttk.Frame(container)
        footer.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)

        ttk.Label(
            footer,
            text=(
                f"Total: {format_hnl(sale['total'])}  |  "
                f"Recibido: {format_hnl(sale['pagado'])}  |  "
                f"Cambio: {format_hnl(sale['vuelto'])}"
            ),
            style="POSSection.TLabel",
        ).grid(row=0, column=0, sticky="w")

        validation_label = ttk.Label(footer, style="POSMuted.TLabel")
        validation_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        actions = ttk.Frame(footer)
        actions.grid(row=2, column=0, sticky="e", pady=(10, 0))

        ttk.Button(actions, text="Cancelar", style="POSDanger.TButton", command=self._close_summary_window).pack(
            side="right"
        )
        confirm_btn = ttk.Button(
            actions,
            text="Confirmar venta",
            style="POSSuccess.TButton",
            command=lambda: self.confirm_sale_and_process(parent_modal=self.summary_window),
        )
        confirm_btn.pack(side="right", padx=(0, 8))

        if sale["pagado"] < sale["total"]:
            faltante = sale["total"] - sale["pagado"]
            validation_label.configure(text=f"Monto insuficiente. Faltan {format_hnl(faltante)}.")
            confirm_btn.state(["disabled"])
        else:
            validation_label.configure(text="Revise la venta y confirme para procesar inventario y recibo.")
            confirm_btn.state(["!disabled"])

    def confirm_sale_and_process(self, parent_modal=None):
        if not self.pending_sale:
            self.pending_sale = self._build_sale_snapshot()

        if parent_modal is None and not messagebox.askyesno(
            "Confirmar venta",
            "Desea confirmar esta venta y actualizar inventario?",
        ):
            return

        sale = self.pending_sale
        try:
            result = self.create_pos_sale_use_case.execute(
                sale,
                usuario_id=self.app.current_user[0],
                preview_mode=self.preview_mode_var.get(),
                number_to_words=self.number_to_words,
            )
            html_content = result.receipt_html

            receipt_error = None
            try:
                self.save_receipt(html_content, result.sale_id)
            except Exception as exc:
                receipt_error = exc

            self.load_products()
            self.clear_cart(silent=True)
            self.pending_sale = {
                **sale,
                "venta_id": result.sale_id,
                "fecha": result.fecha,
                "total": result.total,
                "pagado": result.monto_pagado,
                "vuelto": result.vuelto,
                "metodo_pago": result.metodo_pago,
                "cliente_id": result.cliente_id,
                "cart_snapshot": result.cart_data,
            }
            self.update_cart_display()
            self.refresh_preview()
            self.status_var.set("Venta procesada correctamente.")
            self._close_summary_window()

            if receipt_error:
                messagebox.showwarning(
                    "Venta guardada con advertencia",
                    f"La venta se registro y el stock se actualizo, pero no se pudo guardar el recibo: {receipt_error}",
                )
            elif messagebox.askyesno("Recibo", "Venta procesada. Desea abrir el recibo?"):
                self.print_receipt(html_content)
            else:
                messagebox.showinfo("Exito", "Venta confirmada y guardada en SQLite.")

        except Exception as e:
            self.load_products()
            self.update_cart_display()
            self.status_var.set(f"No se pudo procesar la venta: {e}")
            messagebox.showerror("Error", f"No se pudo procesar la venta: {e}")

    def _receipt_items(self, cart_data):
        return self.receipt_service.build_receipt_items(cart_data)

    def _get_receipt_client(self, cliente_id):
        if cliente_id in (None, ""):
            return None
        return self.sale_repository.get_client_detail(int(cliente_id))

    def generate_receipt_html(self, venta_id, total, pagado, vuelto, fecha, cart_data=None, cliente_id=None, metodo_pago=None):
        cart_data = cart_data or (self.pending_sale or {}).get("cart_snapshot", self.cart)
        return self.receipt_service.build_html(
            venta_id=venta_id,
            fecha=fecha,
            total=total,
            monto_pagado=pagado,
            vuelto=vuelto,
            cart_data=cart_data,
            cliente=self._get_receipt_client(cliente_id),
            metodo_pago=metodo_pago or self.payment_method_var.get() or "NO_DEFINIDO",
            mode=self.preview_mode_var.get(),
            number_to_words=self.number_to_words,
            tax_included=(self.pending_sale or {}).get("tax_included", self._invoice_prices_include_tax()),
        )

    def format_receipt_ticket(self, venta_id, total, pagado, vuelto, fecha, cart_data=None, cliente_id=None, metodo_pago=None):
        return "\n".join(
            self._build_text_receipt(
                venta_id,
                total,
                pagado,
                vuelto,
                fecha,
                cart_data,
                cliente_id,
                metodo_pago=metodo_pago,
                width=42,
            )
        )

    def format_receipt_letter(self, venta_id, total, pagado, vuelto, fecha, cart_data=None, cliente_id=None, metodo_pago=None):
        return "\n".join(
            self._build_text_receipt(
                venta_id,
                total,
                pagado,
                vuelto,
                fecha,
                cart_data,
                cliente_id,
                metodo_pago=metodo_pago,
                width=80,
            )
        )

    def _build_text_receipt(self, venta_id, total, pagado, vuelto, fecha, cart_data, cliente_id, metodo_pago, width):
        cliente_data = self._get_receipt_client(cliente_id)
        cliente = None
        if cliente_data:
            cliente = (
                cliente_data.get("nombre"),
                cliente_data.get("apellido"),
                cliente_data.get("dni"),
                cliente_data.get("telefono"),
                cliente_data.get("direccion"),
            )

        cart_data = cart_data or self.cart
        lines = [
            "=" * width,
            "PODEGA Y COMERCIAL RIVERA".center(width),
            f"Venta: {venta_id}".center(width),
            f"Fecha: {fecha}".center(width),
            f"Metodo: {metodo_pago or 'NO_DEFINIDO'}".center(width),
            "=" * width,
        ]

        if cliente:
            nombre, apellido, dni, telefono, direccion = cliente
            lines.extend([
                "Cliente:".center(width),
                f"{nombre} {apellido}".center(width),
                f"DNI: {dni or 'N/A'}".center(width),
                f"Tel: {telefono or 'N/A'}".center(width),
                f"Dir: {direccion or 'N/A'}".center(width),
                "-" * width,
            ])

        lines.append(f"{'Cant.':<6}{'Producto':<{width - 22}}{'Total':>16}")
        lines.append("-" * width)
        for item in cart_data.values():
            qty = int(item["cantidad"])
            price = float(item["precio_unitario"])
            pct = float(item.get("descuento_porcentaje", 0))
            line_total = (price * qty) * (1 - pct)
            label = item["nombre"]
            if item.get("manual"):
                label += f" (M {int(round(pct * 100))}%)"
            elif pct > 0 and item.get("auto_label"):
                label += f" ({item['auto_label']} {int(round(pct * 100))}%)"
            lines.append(f"{qty:<6}{label[:width - 22]:<{width - 22}}L {line_total:>12.2f}")

        lines.extend(["-" * width, f"{'TOTAL':<{width - 15}}L {total:>10.2f}", f"{'RECIBIDO':<{width - 15}}L {pagado:>10.2f}", f"{'VUELTO':<{width - 15}}L {vuelto:>10.2f}", "=" * width])
        return lines

    def number_to_words(self, n):
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

    def _default_receipt_dir(self):
        local_appdata = os.getenv("LOCALAPPDATA") or str(Path.home())
        return Path(local_appdata) / "ERP-Facturacion" / "Recibos"

    def _candidate_receipt_dirs(self):
        configured_path = (self.db.get_config("recibo_save_path", "") or "").strip()
        candidates = []

        if configured_path:
            candidates.append(Path(configured_path).expanduser())

        default_dir = self._default_receipt_dir()
        if default_dir not in candidates:
            candidates.append(default_dir)

        return candidates

    def _write_receipt_file(self, output_dir, venta_id, html_content):
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"Recibo_{venta_id}.html"
        with file_path.open("w", encoding="utf-8") as handle:
            handle.write(html_content)
        return file_path

    def save_receipt(self, html_content, venta_id):
        configured_path = (self.db.get_config("recibo_save_path", "") or "").strip()
        last_error = None

        for output_dir in self._candidate_receipt_dirs():
            try:
                file_path = self._write_receipt_file(output_dir, venta_id, html_content)
            except OSError as exc:
                last_error = exc
                continue

            if str(output_dir) != configured_path:
                self.db.set_config("recibo_save_path", str(output_dir))

            self.last_receipt_path = str(file_path)
            return str(file_path)

        raise PermissionError(
            "No se pudo guardar el recibo en la ruta configurada ni en la ruta local predeterminada."
        ) from last_error

    def print_receipt(self, html_content):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as handle:
            handle.write(html_content)
            temp_path = handle.name
        webbrowser.open(f"file://{temp_path}")
        messagebox.showinfo("Impresion", "Se abrio el recibo en el navegador. Use Ctrl+P para imprimir.", parent=self)

    def format_receipt_for_preview(self, venta_id, total, pagado, vuelto, fecha):
        return self.format_receipt_ticket(venta_id, total, pagado, vuelto, fecha, metodo_pago=self.payment_method_var.get())

    def _parse_float(self, value):
        try:
            return normalize_hnl_amount(parse_hnl(value, default=0.0))
        except (TypeError, ValueError, tk.TclError):
            return 0.0

    def _widget_exists(self, widget):
        return bool(widget) and bool(widget.winfo_exists())

    def _invoice_prices_include_tax(self):
        raw_value = str(self.db.get_config("factura_tax_included", "1") or "1").strip().lower()
        return raw_value not in {"0", "false", "no", "off"}

    def _calculate_invoice_totals(self, cart_data=None, amount_received=None, payment_method=None, validate_payment=False):
        cart_data = cart_data or self.cart
        invoice = calculate_invoice_totals(
            self._receipt_items(cart_data),
            tax_included=self._invoice_prices_include_tax(),
            payment_method=payment_method or self.payment_method_var.get() or "NO_DEFINIDO",
            amount_received=self.monto_pagado_var.get() if amount_received is None else amount_received,
        )
        if validate_payment and invoice.validation_errors:
            raise ValueError(" ".join(invoice.validation_errors))
        return invoice

    def _set_cart_editor_state(self, prod_id):
        item = self.cart.get(prod_id) if prod_id is not None else None
        if not item:
            self.selected_cart_name_var.set("Seleccione un producto del carrito.")
            self.selected_cart_discount_var.set("Descuento: 0%")
            self.selected_cart_subtotal_var.set("Subtotal: L 0.00")
            self.cart_hint_var.set("Seleccione un producto para editar la cantidad.")
            self.cart_editor_var.set("1")
            self.edit_qty_spin.state(["disabled"])
            return

        pct = float(item.get("descuento_porcentaje", 0))
        subtotal = float(item["precio_unitario"]) * int(item["cantidad"]) * (1 - pct)
        self.selected_cart_name_var.set(item["nombre"])
        self.selected_cart_discount_var.set(f"Descuento: {int(round(pct * 100))}%")
        self.selected_cart_subtotal_var.set(f"Subtotal: {format_hnl(subtotal)}")
        self.cart_hint_var.set("Cambie la cantidad y el total se recalculara de inmediato.")
        self.cart_editor_var.set(str(int(item["cantidad"])))
        self.edit_qty_spin.state(["!disabled"])

    def _refresh_cart_editor(self):
        selected = self.cart_tree.selection()
        if not selected:
            self._set_cart_editor_state(None)
            return
        prod_id = int(selected[0])
        if prod_id not in self.cart:
            self._set_cart_editor_state(None)
            return
        self._set_cart_editor_state(prod_id)

    def _open_preview_window(self):
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.deiconify()
            self.preview_window.lift()
            self.preview_visible = True
            self.preview_button.config(text="Cerrar vista previa")
            self.preview_label_var.set("Vista previa abierta")
            self.refresh_preview()
            return

        self.preview_window = tk.Toplevel(self)
        self.preview_window.title("Vista previa del recibo")
        self.preview_window.transient(self.winfo_toplevel())
        self.preview_window.resizable(True, True)
        center_window(self.preview_window, 760, 560, parent=self.winfo_toplevel())
        self.preview_window.protocol("WM_DELETE_WINDOW", self._close_preview_window)

        container = ttk.Frame(self.preview_window, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Vista previa del recibo", style="POSSection.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Cerrar", style="POSDanger.TButton", command=self._close_preview_window).grid(row=0, column=1, sticky="e")

        text_frame = ttk.Frame(container)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.preview_text = tk.Text(text_frame, font=("Courier New", 10), wrap=tk.NONE)
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.preview_text.yview)
        x_scroll = ttk.Scrollbar(text_frame, orient="horizontal", command=self.preview_text.xview)
        self.preview_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        self.preview_visible = True
        self.preview_button.config(text="Cerrar vista previa")
        self.preview_label_var.set("Vista previa abierta")
        self.refresh_preview()

    def _close_preview_window(self):
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        self.preview_window = None
        self.preview_text = None
        self.preview_visible = False
        if hasattr(self, "preview_button"):
            self.preview_button.config(text="Vista previa")
        self.preview_label_var.set("Vista previa disponible")

    def _close_summary_window(self):
        if self.summary_window and self.summary_window.winfo_exists():
            self.summary_window.destroy()
        self.summary_window = None

    def _close_payment_window(self):
        if self.payment_window and self.payment_window.winfo_exists():
            self.payment_window.destroy()
        self.payment_window = None
        self.monto_entry = None


SalesFrame = UnifiedPOSFrame
WholesaleSalesFrame = UnifiedPOSFrame
