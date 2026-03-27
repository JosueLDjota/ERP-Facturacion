"""
frames/registro.py
Módulo de consulta de ventas (solo lectura) sincronizado con POS.
"""

import tempfile
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

from tkcalendar import DateEntry

from receipt_builder import build_receipt_html
from .ui import create_modal


class RegistroVentasFrame(ttk.Frame):
    """Vista de consulta de ventas POS con filtros dinámicos y reimpresión."""

    FILTER_FECHA = "Fecha"
    FILTER_PRODUCTO = "Producto"
    FILTER_CLIENTE = "Nombre de cliente"
    FILTER_VENTA_ID = "ID de venta"

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self._refresh_job = None

        self.filter_type_var = tk.StringVar(value=self.FILTER_FECHA)
        self.fecha_desde_var = tk.StringVar()
        self.fecha_hasta_var = tk.StringVar()
        self.producto_var = tk.StringVar()
        self.cliente_var = tk.StringVar()
        self.venta_id_var = tk.StringVar()

        self.product_map = {}
        self.client_map = {}

        self._build_ui()
        self._load_filter_options()
        self.refresh_table()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Registro de ventas", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        self.filters_frame = ttk.LabelFrame(self, text="Filtros de consulta", style="Card.TLabelframe")
        self.filters_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.filters_frame.columnconfigure(1, weight=1)

        self.table_frame = ttk.LabelFrame(self, text="Historial de ventas POS", style="Card.TLabelframe")
        self.table_frame.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)

        self._build_filters()
        self._build_table()

    def _parent(self):
        return self.winfo_toplevel()

    def _show_error(self, title, text):
        messagebox.showerror(title, text, parent=self._parent())

    def _show_info(self, title, text):
        messagebox.showinfo(title, text, parent=self._parent())

    def _show_warning(self, title, text):
        messagebox.showwarning(title, text, parent=self._parent())

    def _ask_yes_no(self, title, text):
        return messagebox.askyesno(title, text, parent=self._parent())

    def _build_filters(self):
        ttk.Label(self.filters_frame, text="Filtrar por:", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.filter_type_combo = ttk.Combobox(
            self.filters_frame,
            textvariable=self.filter_type_var,
            state="readonly",
            values=(self.FILTER_FECHA, self.FILTER_PRODUCTO, self.FILTER_CLIENTE, self.FILTER_VENTA_ID),
            width=28,
        )
        self.filter_type_combo.grid(row=0, column=1, sticky="ew", pady=4)
        self.filter_type_combo.bind("<<ComboboxSelected>>", self._on_filter_type_change)

        self.dynamic_filter_frame = ttk.Frame(self.filters_frame, style="Surface.TFrame")
        self.dynamic_filter_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 10))
        self.dynamic_filter_frame.columnconfigure(1, weight=1)

        action_frame = ttk.Frame(self.filters_frame, style="Surface.TFrame")
        action_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        action_frame.columnconfigure((0, 1, 2, 3), weight=1)

        ttk.Button(action_frame, text="Buscar", style="Primary.TButton", command=self.apply_filters).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(action_frame, text="Limpiar", style="Secondary.TButton", command=self.clear_filters).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Button(
            action_frame,
            text="Reimprimir factura",
            style="Secondary.TButton",
            command=self.reprint_selected_invoice,
        ).grid(row=0, column=2, sticky="ew", padx=6)
        ttk.Button(
            action_frame,
            text="Depurar legado",
            style="Danger.TButton",
            command=self.cleanup_legacy_registry,
        ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        self.status_label = ttk.Label(self.filters_frame, text="", style="Muted.TLabel")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.status_label.grid_remove()

        self._render_dynamic_filter_inputs()

    def _build_table(self):
        columns = ("venta_id", "fecha", "cliente", "total", "pagado", "vuelto", "productos", "lineas")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=18)

        headings = {
            "venta_id": "ID Venta",
            "fecha": "Fecha",
            "cliente": "Cliente",
            "total": "Total",
            "pagado": "Pagado",
            "vuelto": "Vuelto",
            "productos": "Productos",
            "lineas": "Items",
        }
        widths = {
            "venta_id": (190, "center"),
            "fecha": (155, "center"),
            "cliente": (220, "w"),
            "total": (100, "e"),
            "pagado": (100, "e"),
            "vuelto": (100, "e"),
            "productos": (320, "w"),
            "lineas": (70, "center"),
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key][0], anchor=widths[key][1])

        y_scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.table_frame.rowconfigure(0, weight=1)
        self.table_frame.columnconfigure(0, weight=1)

    def _render_dynamic_filter_inputs(self):
        for widget in self.dynamic_filter_frame.winfo_children():
            widget.destroy()

        filter_type = self.filter_type_var.get()
        if filter_type == self.FILTER_FECHA:
            ttk.Label(self.dynamic_filter_frame, text="Desde:", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
            desde_entry = DateEntry(self.dynamic_filter_frame, textvariable=self.fecha_desde_var, date_pattern="yyyy-mm-dd", width=20)
            desde_entry.grid(row=0, column=1, sticky="w", pady=4)

            ttk.Label(self.dynamic_filter_frame, text="Hasta:", style="FormLabel.TLabel").grid(row=1, column=0, sticky="w", pady=4)
            hasta_entry = DateEntry(self.dynamic_filter_frame, textvariable=self.fecha_hasta_var, date_pattern="yyyy-mm-dd", width=20)
            hasta_entry.grid(row=1, column=1, sticky="w", pady=4)

            desde_entry.bind("<<DateEntrySelected>>", self._schedule_refresh)
            hasta_entry.bind("<<DateEntrySelected>>", self._schedule_refresh)
            return

        if filter_type == self.FILTER_PRODUCTO:
            ttk.Label(self.dynamic_filter_frame, text="Producto:", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
            combo = ttk.Combobox(
                self.dynamic_filter_frame,
                textvariable=self.producto_var,
                values=list(self.product_map.keys()),
                state="readonly",
                width=45,
            )
            combo.grid(row=0, column=1, sticky="ew", pady=4)
            combo.bind("<<ComboboxSelected>>", self._schedule_refresh)
            return

        if filter_type == self.FILTER_CLIENTE:
            ttk.Label(self.dynamic_filter_frame, text="Cliente:", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
            combo = ttk.Combobox(
                self.dynamic_filter_frame,
                textvariable=self.cliente_var,
                values=list(self.client_map.keys()),
                state="readonly",
                width=45,
            )
            combo.grid(row=0, column=1, sticky="ew", pady=4)
            combo.bind("<<ComboboxSelected>>", self._schedule_refresh)
            return

        ttk.Label(self.dynamic_filter_frame, text="ID de venta:", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        entry = ttk.Entry(self.dynamic_filter_frame, textvariable=self.venta_id_var)
        entry.grid(row=0, column=1, sticky="ew", pady=4)

    def _on_filter_type_change(self, _event=None):
        self.clear_filters(refresh=False)
        self._render_dynamic_filter_inputs()
        self._clear_status()
        self._clear_table()

    def _load_filter_options(self):
        options = self.app.db.fetch_filter_options()
        self.product_map = {f"{row[0]} - {row[1]}": row[0] for row in options.get("productos", [])}
        self.client_map = {f"{row[0]} - {row[1]}": row[0] for row in options.get("clientes", [])}
        self._render_dynamic_filter_inputs()

    def _build_filter_payload(self):
        filter_type = self.filter_type_var.get()
        payload = {}

        if filter_type == self.FILTER_FECHA:
            desde = self.fecha_desde_var.get().strip()
            hasta = self.fecha_hasta_var.get().strip()
            if desde and not self._is_valid_date(desde):
                raise ValueError("Fecha 'Desde' inválida. Use YYYY-MM-DD.")
            if hasta and not self._is_valid_date(hasta):
                raise ValueError("Fecha 'Hasta' inválida. Use YYYY-MM-DD.")
            if desde and hasta and desde > hasta:
                raise ValueError("Rango inválido: 'Desde' es mayor que 'Hasta'.")
            payload["fecha_desde"] = desde or None
            payload["fecha_hasta"] = hasta or None
            return payload

        if filter_type == self.FILTER_PRODUCTO:
            selected = self.producto_var.get().strip()
            payload["producto_id"] = self.product_map.get(selected)
            if not selected:
                raise ValueError("Seleccione un producto del listado.")
            if payload["producto_id"] is None:
                raise ValueError("Seleccione un producto válido del listado.")
            return payload

        if filter_type == self.FILTER_CLIENTE:
            selected = self.cliente_var.get().strip()
            payload["cliente_id"] = self.client_map.get(selected)
            if not selected:
                raise ValueError("Seleccione un cliente del listado.")
            if payload["cliente_id"] is None:
                raise ValueError("Seleccione un cliente válido del listado.")
            return payload

        venta_id = self.venta_id_var.get().strip()
        if not venta_id:
            raise ValueError("Ingrese un ID de venta.")
        payload["venta_id"] = venta_id
        return payload

    def apply_filters(self):
        self.refresh_table()

    def refresh_table(self):
        self._clear_status()
        try:
            filters = self._build_filter_payload()
            rows = self.app.db.fetch_sales_registry(filters)
        except ValueError as exc:
            self._show_error("Error", str(exc))
            self._clear_table()
            self._set_status("No hay registros disponibles")
            return
        except Exception as exc:
            self._show_error("Error de DB", f"No se pudo consultar ventas: {exc}")
            self._clear_table()
            self._set_status("No hay registros disponibles")
            return

        self._clear_table()
        if not rows:
            self._set_status("No hay registros disponibles")
            return

        for row in rows:
            venta_id = row[0]
            fecha = row[1]
            total = float(row[2] or 0)
            pagado = float(row[3] or 0)
            vuelto = float(row[4] or 0)
            cliente = row[5] or "Cliente General"
            productos = row[6] or "-"
            lineas = int(row[7] or 0)
            self.tree.insert(
                "",
                "end",
                iid=str(venta_id),
                values=(venta_id, fecha, cliente, f"L {total:.2f}", f"L {pagado:.2f}", f"L {vuelto:.2f}", productos, lineas),
            )

    def _clear_table(self):
        self.tree.delete(*self.tree.get_children())

    def _set_status(self, message):
        if message:
            self.status_label.configure(text=message)
            self.status_label.grid()
            return
        self._clear_status()

    def _clear_status(self):
        self.status_label.configure(text="")
        self.status_label.grid_remove()

    def clear_filters(self, refresh=True):
        self.fecha_desde_var.set("")
        self.fecha_hasta_var.set("")
        self.producto_var.set("")
        self.cliente_var.set("")
        self.venta_id_var.set("")
        self._clear_status()
        if refresh:
            self.refresh_table()

    def reprint_selected_invoice(self):
        selected = self.tree.selection()
        if not selected:
            self._show_warning("Selección requerida", "Seleccione una venta para reimprimir.")
            return

        venta_id = selected[0]
        sale = self.app.db.fetch_sale_header(venta_id)
        if not sale:
            self._show_error("No encontrada", "No se encontró la venta seleccionada.")
            return

        items = self.app.db.fetch_sale_items(venta_id)
        if not items:
            self._show_error("Sin detalle", "La venta no tiene detalle de productos.")
            return

        html = build_receipt_html(
            venta_id=sale["venta_id"],
            fecha=sale["fecha"],
            total=sale["total"],
            monto_pagado=sale["monto_pagado"],
            vuelto=sale["vuelto"],
            items=items,
            cliente=sale["cliente"],
            mode="ticket",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(html)
            file_path = temp_file.name
        webbrowser.open(f"file://{file_path}")
        self._show_info("Reimpresión generada", "Factura abierta en el navegador. Use Ctrl+P para imprimir.")

    def cleanup_legacy_registry(self):
        if not self._ask_yes_no(
            "Depuración de legado",
            "Se depurará la tabla legado 'ventas_diarias' eliminando huérfanos y duplicados verificables.\n\n¿Desea continuar?",
        ):
            return

        report = self.app.db.cleanup_legacy_sales_registry()
        popup = create_modal(self._parent(), "Depuración completada", width=560, height=380)
        content = ttk.Frame(popup, padding=18, style="Surface.TFrame")
        content.pack(fill="both", expand=True)

        ttk.Label(content, text="Resultados de depuración", style="Subheader.TLabel").pack(anchor="w", pady=(0, 12))
        lines = [
            f"Antes: {report['antes_total']}",
            f"Después: {report['despues_total']}",
            f"Eliminados huérfanos venta: {report['eliminados_huerfanos_venta']}",
            f"Eliminados huérfanos producto: {report['eliminados_huerfanos_producto']}",
            f"Eliminados duplicados legacy: {report['eliminados_duplicados_legacy']}",
            f"Eliminados duplicados referencia: {report['eliminados_duplicados_referencia']}",
            f"Total eliminados: {report['total_eliminados']}",
        ]
        for line in lines:
            ttk.Label(content, text=line, style="FormLabel.TLabel").pack(anchor="w", pady=2)

        ttk.Button(content, text="Cerrar", style="Primary.TButton", command=popup.destroy).pack(anchor="e", pady=(16, 0))

    def _schedule_refresh(self, _event=None):
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(350, self.refresh_table)

    @staticmethod
    def _is_valid_date(date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
