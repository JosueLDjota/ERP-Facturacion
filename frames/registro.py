"""
frames/registro.py
Modulo de registro de ventas en memoria para el dashboard administrativo.
"""

from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox


class RegistroVentasFrame(ttk.Frame):
    """Frame para registrar y listar ventas en memoria (sesion actual)."""

    def __init__(self, parent, app):
        super().__init__(parent, padding="10")
        self.app = app

        self.sales_records = []
        self.record_counter = 1

        self.monto_total_var = tk.StringVar()
        self.metodo_pago_var = tk.StringVar()
        self.referencia_var = tk.StringVar()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.form_frame = ttk.LabelFrame(
            self, text="Formulario de Registro de Venta", padding=15
        )
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.table_frame = ttk.LabelFrame(
            self, text="Listado de Ventas Registradas", padding=15
        )
        self.table_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._build_form()
        self._build_table()

    def _build_form(self):
        """Crea formulario de captura."""
        ttk.Label(self.form_frame, text="Monto Total *:").grid(
            row=0, column=0, sticky="w", pady=6
        )
        ttk.Entry(
            self.form_frame, textvariable=self.monto_total_var, width=28
        ).grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(self.form_frame, text="Metodo de Pago *:").grid(
            row=1, column=0, sticky="w", pady=6
        )
        ttk.Entry(
            self.form_frame, textvariable=self.metodo_pago_var, width=28
        ).grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(self.form_frame, text="Referencia *:").grid(
            row=2, column=0, sticky="w", pady=6
        )
        ttk.Entry(
            self.form_frame, textvariable=self.referencia_var, width=28
        ).grid(row=2, column=1, sticky="ew", pady=6)

        ttk.Label(self.form_frame, text="Observacion (Opcional):").grid(
            row=3, column=0, sticky="nw", pady=6
        )
        self.observacion_text = tk.Text(self.form_frame, height=5, width=28)
        self.observacion_text.grid(row=3, column=1, sticky="ew", pady=6)

        actions_frame = ttk.Frame(self.form_frame)
        actions_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        ttk.Button(
            actions_frame,
            text="Registrar Venta",
            style="Accent.TButton",
            command=self.register_sale,
        ).pack(side="left", padx=(0, 6), fill="x", expand=True)

        ttk.Button(actions_frame, text="Limpiar", command=self.clear_form).pack(
            side="left", padx=(6, 0), fill="x", expand=True
        )

        self.form_frame.columnconfigure(1, weight=1)

    def _build_table(self):
        """Crea tabla de ventas."""
        columns = ("ID", "monto", "metodo_pago", "referencia", "fecha", "usuario")
        self.tree = ttk.Treeview(
            self.table_frame, columns=columns, show="headings", height=16
        )

        self.tree.heading("ID", text="ID")
        self.tree.heading("monto", text="Monto")
        self.tree.heading("metodo_pago", text="Metodo de Pago")
        self.tree.heading("referencia", text="Referencia")
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("usuario", text="Usuario")

        self.tree.column("ID", width=90, anchor="center")
        self.tree.column("monto", width=100, anchor="e")
        self.tree.column("metodo_pago", width=140, anchor="center")
        self.tree.column("referencia", width=140, anchor="w")
        self.tree.column("fecha", width=155, anchor="center")
        self.tree.column("usuario", width=130, anchor="center")

        y_scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(
            self.table_frame, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        self.table_frame.rowconfigure(0, weight=1)
        self.table_frame.columnconfigure(0, weight=1)

    def register_sale(self):
        """Valida y registra una venta en memoria."""
        monto_raw = self.monto_total_var.get().strip()
        metodo_pago = self.metodo_pago_var.get().strip()
        referencia = self.referencia_var.get().strip()
        observacion = self.observacion_text.get("1.0", tk.END).strip()

        if not monto_raw:
            messagebox.showerror("Error", "El campo monto_total es obligatorio.")
            return

        try:
            monto_total = float(monto_raw)
            if monto_total <= 0:
                messagebox.showerror(
                    "Error", "El campo monto_total debe ser un numero mayor a 0."
                )
                return
        except ValueError:
            messagebox.showerror(
                "Error", "El campo monto_total debe ser un numero valido."
            )
            return

        if not metodo_pago:
            messagebox.showerror("Error", "El campo metodo_pago es obligatorio.")
            return

        if not referencia:
            messagebox.showerror("Error", "El campo referencia es obligatorio.")
            return

        sale_id = f"RV-{self.record_counter:04d}"
        self.record_counter += 1

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        usuario = (
            self.app.current_user[1]
            if getattr(self.app, "current_user", None) and len(self.app.current_user) > 1
            else "N/A"
        )

        self.sales_records.append(
            {
                "id": sale_id,
                "monto": monto_total,
                "metodo_pago": metodo_pago,
                "referencia": referencia,
                "observacion": observacion,
                "fecha": fecha,
                "usuario": usuario,
                "sort_key": datetime.now(),
            }
        )

        self.refresh_table()
        self.clear_form()
        messagebox.showinfo("Exito", f"Venta {sale_id} registrada correctamente.")

    def refresh_table(self):
        """Refresca tabla ordenando por fecha descendente."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        ordered_records = sorted(
            self.sales_records, key=lambda record: record["sort_key"], reverse=True
        )

        for record in ordered_records:
            self.tree.insert(
                "",
                "end",
                values=(
                    record["id"],
                    f"${record['monto']:.2f}",
                    record["metodo_pago"],
                    record["referencia"],
                    record["fecha"],
                    record["usuario"],
                ),
            )

    def clear_form(self):
        """Limpia los campos del formulario."""
        self.monto_total_var.set("")
        self.metodo_pago_var.set("")
        self.referencia_var.set("")
        self.observacion_text.delete("1.0", tk.END)
