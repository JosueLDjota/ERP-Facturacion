"""
frames/registro.py
Modulo de consulta de ventas (solo lectura) sincronizado con POS.
"""

import csv
import tempfile
import webbrowser
from datetime import datetime
from html import escape
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tkcalendar import DateEntry

from erp.domain.services.access_control import can_manage_legacy_registry
from receipt_builder import build_receipt_html
from .ui import create_modal, format_hnl


class RegistroVentasFrame(ttk.Frame):
    """Vista de consulta de ventas POS con filtros dinamicos y reimpresion."""

    FILTER_FECHA = "Fecha"
    FILTER_PRODUCTO = "Producto"
    FILTER_CLIENTE = "Nombre de cliente"

    MONTH_OPTIONS = (
        ("Todos", ""),
        ("Enero", "1"),
        ("Febrero", "2"),
        ("Marzo", "3"),
        ("Abril", "4"),
        ("Mayo", "5"),
        ("Junio", "6"),
        ("Julio", "7"),
        ("Agosto", "8"),
        ("Septiembre", "9"),
        ("Octubre", "10"),
        ("Noviembre", "11"),
        ("Diciembre", "12"),
    )

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self._refresh_job = None
        self.current_rows = []

        self.filter_type_var = tk.StringVar(value=self.FILTER_FECHA)
        self.fecha_desde_var = tk.StringVar()
        self.fecha_hasta_var = tk.StringVar()
        self.producto_var = tk.StringVar()
        self.cliente_var = tk.StringVar()
        self.venta_id_var = tk.StringVar()
        self.mes_var = tk.StringVar(value=self.MONTH_OPTIONS[0][0])
        self.anio_var = tk.StringVar(value="Todos")

        self.product_map = {}
        self.client_map = {}
        self.month_map = {label: value for label, value in self.MONTH_OPTIONS}

        self._build_ui()
        self._load_filter_options()
        self.refresh_table()

    def _invoice_prices_include_tax(self):
        raw_value = str(self.app.db.get_config("factura_tax_included", "1") or "1").strip().lower()
        return raw_value not in {"0", "false", "no", "off"}

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text="Registro de ventas", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        self.filters_frame = ttk.LabelFrame(self, text="Filtros de consulta", style="Card.TLabelframe")
        self.filters_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.filters_frame.columnconfigure(1, weight=1)

        self.table_frame = ttk.LabelFrame(self, text="Historial de ventas POS", style="Card.TLabelframe")
        self.table_frame.grid(row=2, column=0, sticky="nsew")

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
        period_row = ttk.Frame(self.filters_frame, style="Surface.TFrame")
        period_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        period_row.columnconfigure(1, weight=1)
        period_row.columnconfigure(3, weight=1)

        ttk.Label(period_row, text="Mes:", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.month_combo = ttk.Combobox(
            period_row,
            textvariable=self.mes_var,
            state="readonly",
            values=[label for label, _value in self.MONTH_OPTIONS],
            width=20,
        )
        self.month_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.month_combo.bind("<<ComboboxSelected>>", self._schedule_refresh)

        ttk.Label(period_row, text="Ano:", style="FormLabel.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.year_combo = ttk.Combobox(
            period_row,
            textvariable=self.anio_var,
            state="readonly",
            values=self._build_year_options(),
            width=14,
        )
        self.year_combo.grid(row=0, column=3, sticky="ew")
        self.year_combo.bind("<<ComboboxSelected>>", self._schedule_refresh)

        ttk.Label(self.filters_frame, text="Filtrar por:", style="FormLabel.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.filter_type_combo = ttk.Combobox(
            self.filters_frame,
            textvariable=self.filter_type_var,
            state="readonly",
            values=(self.FILTER_FECHA, self.FILTER_PRODUCTO, self.FILTER_CLIENTE),
            width=28,
        )
        self.filter_type_combo.grid(row=1, column=1, sticky="ew", pady=4)
        self.filter_type_combo.bind("<<ComboboxSelected>>", self._on_filter_type_change)

        self.dynamic_filter_frame = ttk.Frame(self.filters_frame, style="Surface.TFrame")
        self.dynamic_filter_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 10))
        self.dynamic_filter_frame.columnconfigure(1, weight=1)

        action_frame = ttk.Frame(self.filters_frame, style="Surface.TFrame")
        action_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        action_frame.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        ttk.Button(action_frame, text="Buscar", style="Primary.TButton", command=self.apply_filters).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(action_frame, text="Limpiar", style="Secondary.TButton", command=self.clear_filters).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ttk.Button(action_frame, text="Exportar CSV", style="Secondary.TButton", command=self.export_filtered_results).grid(
            row=0, column=2, sticky="ew", padx=4
        )
        ttk.Button(action_frame, text="Imprimir lista", style="Secondary.TButton", command=self.print_filtered_results).grid(
            row=0, column=3, sticky="ew", padx=4
        )
        ttk.Button(
            action_frame,
            text="Reimprimir factura",
            style="Secondary.TButton",
            command=self.reprint_selected_invoice,
        ).grid(row=0, column=4, sticky="ew", padx=4)
        self.cleanup_button = ttk.Button(
            action_frame,
            text="Depurar legado",
            style="Danger.TButton",
            command=self.cleanup_legacy_registry,
        )
        self.cleanup_button.grid(row=0, column=5, sticky="ew", padx=(4, 0))

        self.status_label = ttk.Label(self.filters_frame, text="", style="Muted.TLabel")
        self.status_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.status_label.grid_remove()

        ttk.Label(
            self.filters_frame,
            text="Fuente principal: Ventas + DetalleVenta. La tabla ventas_diarias se conserva solo para trazabilidad legacy.",
            style="Muted.TLabel",
            wraplength=920,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        if not can_manage_legacy_registry(self.app.current_user[2]):
            self.cleanup_button.state(["disabled"])

        self._render_dynamic_filter_inputs()

    def _build_table(self):
        columns = ("fecha", "cliente", "total", "pagado", "vuelto", "productos", "lineas")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=18)

        headings = {
            "fecha": "Fecha",
            "cliente": "Cliente",
            "total": "Total",
            "pagado": "Pagado",
            "vuelto": "Vuelto",
            "productos": "Productos",
            "lineas": "Items",
        }
        widths = {
            "fecha": (165, "center"),
            "cliente": (240, "w"),
            "total": (130, "e"),
            "pagado": (130, "e"),
            "vuelto": (130, "e"),
            "productos": (340, "w"),
            "lineas": (80, "center"),
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

    def _build_year_options(self):
        current_year = datetime.now().year
        years = ["Todos"]
        for year in range(current_year, current_year - 8, -1):
            years.append(str(year))
        return years

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

    def _on_filter_type_change(self, _event=None):
        self.clear_filters(refresh=False)
        self._render_dynamic_filter_inputs()
        self._clear_status()
        self._clear_table()

    @staticmethod
    def _build_visible_option_map(rows, fallback_label):
        option_map = {}
        label_counts = {}
        for row_id, label in rows:
            base_label = str(label or fallback_label).strip() or fallback_label
            visible_label = base_label
            label_counts[base_label] = label_counts.get(base_label, 0) + 1
            if label_counts[base_label] > 1:
                visible_label = f"{base_label} ({label_counts[base_label]})"
            option_map[visible_label] = row_id
        return option_map

    def _load_filter_options(self):
        options = self.app.db.fetch_filter_options()
        self.product_map = self._build_visible_option_map(options.get("productos", []), "Producto sin nombre")
        self.client_map = self._build_visible_option_map(options.get("clientes", []), "Cliente sin nombre")
        self._render_dynamic_filter_inputs()

    def _build_filter_payload(self):
        filter_type = self.filter_type_var.get()
        payload = {}

        selected_month = self.month_map.get(self.mes_var.get(), "")
        if selected_month:
            payload["mes"] = int(selected_month)

        selected_year = self.anio_var.get().strip()
        if selected_year and selected_year != "Todos":
            payload["anio"] = int(selected_year)

        if filter_type == self.FILTER_FECHA:
            desde = self.fecha_desde_var.get().strip()
            hasta = self.fecha_hasta_var.get().strip()
            if desde and not self._is_valid_date(desde):
                raise ValueError("Fecha 'Desde' invalida. Use YYYY-MM-DD.")
            if hasta and not self._is_valid_date(hasta):
                raise ValueError("Fecha 'Hasta' invalida. Use YYYY-MM-DD.")
            if desde and hasta and desde > hasta:
                raise ValueError("Rango invalido: 'Desde' es mayor que 'Hasta'.")
            payload["fecha_desde"] = desde or None
            payload["fecha_hasta"] = hasta or None
            return payload

        if filter_type == self.FILTER_PRODUCTO:
            selected = self.producto_var.get().strip()
            payload["producto_id"] = self.product_map.get(selected)
            if not selected:
                raise ValueError("Seleccione un producto del listado.")
            if payload["producto_id"] is None:
                raise ValueError("Seleccione un producto valido del listado.")
            return payload

        if filter_type == self.FILTER_CLIENTE:
            selected = self.cliente_var.get().strip()
            payload["cliente_id"] = self.client_map.get(selected)
            if not selected:
                raise ValueError("Seleccione un cliente del listado.")
            if payload["cliente_id"] is None:
                raise ValueError("Seleccione un cliente valido del listado.")
            return payload

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
            self.current_rows = []
            self._clear_table()
            self._set_status("No hay registros disponibles")
            return
        except Exception as exc:
            self._show_error("Error de DB", f"No se pudo consultar ventas: {exc}")
            self.current_rows = []
            self._clear_table()
            self._set_status("No hay registros disponibles")
            return

        self.current_rows = rows
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
                values=(
                    fecha,
                    cliente,
                    format_hnl(total),
                    format_hnl(pagado),
                    format_hnl(vuelto),
                    productos,
                    lineas,
                ),
            )

        self._set_status(f"{len(rows)} venta(s) encontrada(s).")

    def export_filtered_results(self):
        if not self.current_rows:
            self._show_warning("Sin resultados", "No hay resultados filtrados para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            parent=self._parent(),
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="registro_ventas_filtrado.csv",
            title="Exportar registro filtrado",
        )
        if not file_path:
            return

        headers = ["venta_id", "fecha", "cliente", "total_hnl", "pagado_hnl", "vuelto_hnl", "productos", "lineas"]
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                for row in self.current_rows:
                    writer.writerow(
                        [
                            row[0],
                            row[1],
                            row[5] or "Cliente General",
                            f"{float(row[2] or 0):.2f}",
                            f"{float(row[3] or 0):.2f}",
                            f"{float(row[4] or 0):.2f}",
                            row[6] or "-",
                            int(row[7] or 0),
                        ]
                    )
            self._show_info("Exportacion completa", f"Archivo generado:\n{file_path}")
        except Exception as exc:
            self._show_error("Error", f"No se pudo exportar el archivo: {exc}")

    def print_filtered_results(self):
        if not self.current_rows:
            self._show_warning("Sin resultados", "No hay resultados filtrados para imprimir.")
            return

        rows_html = []
        for row in self.current_rows:
            rows_html.append(
                "<tr>"
                f"<td>{escape(str(row[1]))}</td>"
                f"<td>{escape(str(row[5] or 'Cliente General'))}</td>"
                f"<td>{escape(format_hnl(row[2]))}</td>"
                f"<td>{escape(format_hnl(row[3]))}</td>"
                f"<td>{escape(format_hnl(row[4]))}</td>"
                f"<td>{escape(str(row[6] or '-'))}</td>"
                f"<td>{int(row[7] or 0)}</td>"
                "</tr>"
            )

        html = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>Reporte de ventas filtradas</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; color: #111827; }}
        h1 {{ margin-bottom: 6px; }}
        p {{ color: #4b5563; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        th, td {{ border: 1px solid #d1d5db; padding: 8px; font-size: 12px; }}
        th {{ background: #f3f4f6; text-align: left; }}
    </style>
</head>
<body>
    <h1>Reporte de ventas filtradas</h1>
    <p>Generado: {escape(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>
    <table>
        <thead>
            <tr>
                <th>Fecha</th>
                <th>Cliente</th>
                <th>Total</th>
                <th>Pagado</th>
                <th>Vuelto</th>
                <th>Productos</th>
                <th>Items</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows_html)}
        </tbody>
    </table>
</body>
</html>
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(html)
            file_path = temp_file.name
        webbrowser.open(f"file://{file_path}")
        self._show_info("Impresion", "Se abrio el reporte en el navegador. Use Ctrl+P para imprimir.")

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
        self.mes_var.set(self.MONTH_OPTIONS[0][0])
        self.anio_var.set("Todos")
        self._clear_status()
        if refresh:
            self.refresh_table()

    def reprint_selected_invoice(self):
        selected = self.tree.selection()
        if not selected:
            self._show_warning("Seleccion requerida", "Seleccione una venta para reimprimir.")
            return

        venta_id = selected[0]
        sale = self.app.db.fetch_sale_header(venta_id)
        if not sale:
            self._show_error("No encontrada", "No se encontro la venta seleccionada.")
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
            metodo_pago=sale.get("metodo_pago", "NO_DEFINIDO"),
            mode="ticket",
            tax_included=self._invoice_prices_include_tax(),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(html)
            file_path = temp_file.name
        webbrowser.open(f"file://{file_path}")
        self._show_info("Reimpresion generada", "Factura abierta en el navegador. Use Ctrl+P para imprimir.")

    def cleanup_legacy_registry(self):
        if not can_manage_legacy_registry(self.app.current_user[2]):
            self._show_warning("Acceso restringido", "Solo administracion puede depurar tablas legacy.")
            return

        if not self._ask_yes_no(
            "Depuracion de legado",
            "Se depurara la tabla legado 'ventas_diarias' eliminando huerfanos y duplicados verificables.\n\nDesea continuar?",
        ):
            return

        report = self.app.db.cleanup_legacy_sales_registry()
        popup = create_modal(self._parent(), "Depuracion completada", width=560, height=380)
        content = ttk.Frame(popup, padding=18, style="Surface.TFrame")
        content.pack(fill="both", expand=True)

        ttk.Label(content, text="Resultados de depuracion", style="Subheader.TLabel").pack(anchor="w", pady=(0, 12))
        lines = [
            f"Antes: {report['antes_total']}",
            f"Despues: {report['despues_total']}",
            f"Eliminados huerfanos venta: {report['eliminados_huerfanos_venta']}",
            f"Eliminados huerfanos producto: {report['eliminados_huerfanos_producto']}",
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
