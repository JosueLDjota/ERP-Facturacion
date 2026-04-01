"""
frames/config.py
Configuracion del sistema, descuentos y plantilla de recibos.
"""

from datetime import datetime
import re
import tkinter as tk
from tkinter import messagebox, ttk

from .taxonomy import CatalogTaxonomyFrame


class ConfigFrame(ttk.Frame):
    """Frame de configuracion del sistema."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=10, style="App.TFrame")
        self.app = app
        self.db = app.db

        self.disc_id = tk.StringVar(value="")
        self.disc_nombre = tk.StringVar()
        self.disc_porcentaje = tk.StringVar()
        self.disc_tipo = tk.StringVar(value="Docena")

        self._build_ui()
        self.load_discounts()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Configuracion", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        disc_tab = ttk.Frame(self.notebook, padding=12, style="App.TFrame")
        receipt_tab = ttk.Frame(self.notebook, padding=12, style="App.TFrame")
        taxonomy_tab = CatalogTaxonomyFrame(self.notebook, self.app)
        self.notebook.add(disc_tab, text="Descuentos")
        self.notebook.add(taxonomy_tab, text="Categorias y Marcas")
        self.notebook.add(receipt_tab, text="Plantilla de recibo")

        self.create_discount_tab(disc_tab)
        self.create_receipt_tab(receipt_tab)

    def _parent(self):
        return self.winfo_toplevel()

    def create_discount_tab(self, parent):
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
            columns=("Nombre", "Tipo", "Porcentaje"),
            show="headings",
            height=14,
        )
        for col, width, anchor in (
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

        ttk.Button(btn_frame, text="Nuevo", style="Secondary.TButton", command=self.reset_discount_form).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Eliminar", style="Danger.TButton", command=self.delete_discount).pack(side="left")

        fields = [
            ("Nombre", self.disc_nombre),
            ("Porcentaje (%)", self.disc_porcentaje),
        ]
        row = 0
        for label, var in fields:
            ttk.Label(form_frame, text=label, style="FormLabel.TLabel").grid(
                row=row, column=0, sticky="w", padx=4, pady=7
            )
            ttk.Entry(form_frame, textvariable=var).grid(row=row, column=1, sticky="ew", padx=4, pady=7)
            row += 1

        ttk.Label(form_frame, text="Tipo", style="FormLabel.TLabel").grid(row=row, column=0, sticky="w", padx=4, pady=7)
        ttk.Combobox(
            form_frame,
            textvariable=self.disc_tipo,
            values=["Docena", "Mayorista", "Producto"],
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", padx=4, pady=7)
        row += 1

        ttk.Button(form_frame, text="Guardar descuento", style="Primary.TButton", command=self.save_discount).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(16, 0)
        )

    def load_discounts(self):
        for item in self.disc_tree.get_children():
            self.disc_tree.delete(item)

        discounts = self.db.fetch("SELECT id, nombre, tipo, porcentaje FROM Descuentos ORDER BY nombre")
        for disc in discounts:
            self.disc_tree.insert("", "end", iid=str(disc[0]), values=(disc[1], disc[2], f"{int(disc[3] * 100)}%"))

    def select_discount(self, _event):
        selected_item = self.disc_tree.focus()
        if not selected_item:
            return

        values = self.disc_tree.item(selected_item, "values")
        self.disc_id.set(selected_item)
        self.disc_nombre.set(values[0])
        self.disc_tipo.set(values[1])
        self.disc_porcentaje.set(values[2].strip("%"))

    def reset_discount_form(self):
        self.disc_id.set("")
        self.disc_nombre.set("")
        self.disc_porcentaje.set("")
        self.disc_tipo.set("Docena")

    def save_discount(self):
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

        if self.disc_id.get():
            self.db.execute(
                "UPDATE Descuentos SET nombre=?, tipo=?, porcentaje=? WHERE id=?",
                (nombre, tipo, pct, self.disc_id.get()),
            )
            messagebox.showinfo("Exito", "Descuento actualizado.", parent=self._parent())
        else:
            self.db.execute(
                "INSERT INTO Descuentos (nombre, tipo, porcentaje) VALUES (?, ?, ?)",
                (nombre, tipo, pct),
            )
            messagebox.showinfo("Exito", "Descuento agregado.", parent=self._parent())

        self.load_discounts()
        self.reset_discount_form()

    def delete_discount(self):
        selected_item = self.disc_tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Seleccione un descuento primero.", parent=self._parent())
            return

        disc_id = selected_item
        disc_name = self.disc_tree.item(selected_item, "values")[0]
        if messagebox.askyesno("Confirmar", f"Eliminar el descuento \"{disc_name}\"?", parent=self._parent()):
            self.db.execute("DELETE FROM Descuentos WHERE id = ?", (disc_id,))
            messagebox.showinfo("Exito", "Descuento eliminado.", parent=self._parent())
            self.load_discounts()
            self.reset_discount_form()

    def create_receipt_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Editor de plantilla HTML", style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Variables: {{ID_VENTA}}, {{FECHA}}, {{TOTAL}}, {{MONTO_PAGADO}}, {{VUELTO}}, {{NOMBRE_NEGOCIO}}",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        editor_card = ttk.LabelFrame(parent, text="Codigo de plantilla", style="Card.TLabelframe")
        editor_card.grid(row=1, column=0, sticky="nsew")
        editor_card.columnconfigure(0, weight=1)
        editor_card.rowconfigure(0, weight=1)

        self.template_text = tk.Text(editor_card, height=20, width=80, font=("Consolas", 10), wrap=tk.NONE)
        self.template_text.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(editor_card, orient="vertical", command=self.template_text.yview)
        x_scroll = ttk.Scrollbar(editor_card, orient="horizontal", command=self.template_text.xview)
        self.template_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        template = self.db.get_config("recibo_template", self.db.default_receipt_template())
        self.template_text.insert(tk.END, template)

        btn_frame = ttk.Frame(parent, style="App.TFrame")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(btn_frame, text="Vista previa", style="Secondary.TButton", command=self.preview_receipt).pack(
            side="left"
        )
        ttk.Button(
            btn_frame,
            text="Restaurar original",
            style="Secondary.TButton",
            command=self.restore_default_template,
        ).pack(side="right")
        ttk.Button(btn_frame, text="Guardar plantilla", style="Primary.TButton", command=self.save_receipt_template).pack(
            side="right", padx=(0, 8)
        )

    def preview_receipt(self):
        template_content = self.template_text.get(1.0, tk.END).strip()

        html_preview = template_content
        html_preview = html_preview.replace("{{NOMBRE_NEGOCIO}}", "Mi Negocio ERP")
        html_preview = html_preview.replace("{{ID_VENTA}}", "V-20250929-001")
        html_preview = html_preview.replace("{{FECHA}}", datetime.now().strftime("%d/%m/%Y %H:%M"))
        html_preview = html_preview.replace("{{TOTAL}}", "150.00")
        html_preview = html_preview.replace("{{MONTO_PAGADO}}", "200.00")
        html_preview = html_preview.replace("{{VUELTO}}", "50.00")
        html_preview = html_preview.replace(
            "<!-- ITEMS_PLACEHOLDER -->",
            "<div class='item'><span>Monitor 27\"</span><span>1 / L 120.00</span></div>"
            "<div class='item'><span>Mouse Gamer</span><span>2 / L 30.00</span></div>",
        )

        preview_win = tk.Toplevel(self.app)
        preview_win.title("Vista previa de recibo")
        preview_win.geometry("560x650")

        frame = ttk.Frame(preview_win, padding=12, style="Surface.TFrame")
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Vista previa simplificada", style="Subheader.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        preview_text = tk.Text(frame, font=("Consolas", 9), wrap=tk.WORD)
        preview_text.grid(row=1, column=0, sticky="nsew")

        clean_text = re.sub("<[^<]+?>", "", html_preview)
        clean_text = clean_text.replace("&nbsp;", " ")
        preview_text.insert(tk.END, clean_text)
        preview_text.config(state=tk.DISABLED)

    def save_receipt_template(self):
        template_content = self.template_text.get(1.0, tk.END).strip()
        if not template_content:
            messagebox.showerror("Error", "La plantilla no puede estar vacia.", parent=self._parent())
            return

        self.db.set_config("recibo_template", template_content)
        messagebox.showinfo("Exito", "Plantilla guardada correctamente.", parent=self._parent())

    def restore_default_template(self):
        if messagebox.askyesno("Confirmar", "Restaurar la plantilla original?", parent=self._parent()):
            default_template = self.db.default_receipt_template()
            self.template_text.delete(1.0, tk.END)
            self.template_text.insert(tk.END, default_template)
            messagebox.showinfo("Exito", "Plantilla restaurada.", parent=self._parent())
