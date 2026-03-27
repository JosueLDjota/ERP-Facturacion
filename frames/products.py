"""
frames/products.py
Gestión de productos con CRUD e importación/exportación.
"""

import tkinter as tk
from tkinter import messagebox, ttk


class ProductFrame(ttk.Frame):
    """Frame para gestión de productos con CRUD completo."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.db = app.db

        self.product_id = tk.StringVar(value="")
        self.nombre = tk.StringVar()
        self.precio = tk.StringVar()
        self.stock = tk.StringVar()
        self.proveedor_id = tk.StringVar(value="1")
        self.search_var = tk.StringVar()

        self._build_ui()
        self.load_products()

    def _build_ui(self):
        self.columnconfigure(0, weight=7)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Gestión de productos", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self.list_frame = ttk.LabelFrame(self, text="Listado de productos", style="Card.TLabelframe")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.rowconfigure(1, weight=1)

        self.form_frame = ttk.LabelFrame(self, text="Formulario de producto", style="Card.TLabelframe")
        self.form_frame.grid(row=1, column=1, sticky="nsew")
        self.form_frame.columnconfigure(1, weight=1)

        self._create_product_list()
        self._create_product_form()

    def _parent(self):
        return self.winfo_toplevel()

    def _show_info(self, title, text):
        messagebox.showinfo(title, text, parent=self._parent())

    def _show_error(self, title, text):
        messagebox.showerror(title, text, parent=self._parent())

    def _show_warning(self, title, text):
        messagebox.showwarning(title, text, parent=self._parent())

    def _ask_yes_no(self, title, text):
        return messagebox.askyesno(title, text, parent=self._parent())

    def _create_product_list(self):
        search_frame = ttk.Frame(self.list_frame, style="Surface.TFrame")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Buscar:", style="FormLabel.TLabel").grid(row=0, column=0, padx=(0, 6), sticky="w")
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.bind("<KeyRelease>", self.filter_products)

        self.tree = ttk.Treeview(
            self.list_frame,
            columns=("ID", "Nombre", "Precio", "Stock", "Proveedor"),
            show="headings",
            height=15,
        )
        self.tree.grid(row=1, column=0, sticky="nsew")

        for col, width, anchor in (
            ("ID", 60, "center"),
            ("Nombre", 300, "w"),
            ("Precio", 110, "e"),
            ("Stock", 90, "center"),
            ("Proveedor", 100, "center"),
        ):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)

        y_scroll = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        y_scroll.grid(row=1, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self.select_product)

        btn_frame = ttk.Frame(self.list_frame, style="Surface.TFrame")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(btn_frame, text="Nuevo producto", style="Secondary.TButton", command=self.reset_form).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Eliminar", style="Danger.TButton", command=self.delete_product).pack(
            side="left", padx=6
        )
        ttk.Button(
            btn_frame,
            text="Importar CSV",
            style="Secondary.TButton",
            command=lambda: self.app.file_manager.import_products(self),
        ).pack(side="right", padx=(6, 0))
        ttk.Button(
            btn_frame,
            text="Exportar CSV",
            style="Primary.TButton",
            command=lambda: self.app.file_manager.export_data("Productos"),
        ).pack(side="right")

    def _create_product_form(self):
        fields = [
            ("Nombre:", self.nombre),
            ("Precio (USD):", self.precio),
            ("Stock:", self.stock),
            ("Proveedor ID:", self.proveedor_id),
        ]

        row = 0
        for label_text, var in fields:
            ttk.Label(self.form_frame, text=label_text, style="FormLabel.TLabel").grid(
                row=row, column=0, sticky="w", padx=4, pady=7
            )
            ttk.Entry(self.form_frame, textvariable=var).grid(
                row=row, column=1, sticky="ew", padx=4, pady=7
            )
            row += 1

        ttk.Label(self.form_frame, text="Descripción:", style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="nw", padx=4, pady=7
        )
        self.desc_text = tk.Text(self.form_frame, height=5, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.desc_text.grid(row=row, column=1, sticky="ew", padx=4, pady=7)
        row += 1

        ttk.Button(self.form_frame, text="Guardar producto", style="Primary.TButton", command=self.save_product).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(14, 4)
        )

    def load_products(self):
        self.tree.delete(*self.tree.get_children())
        products = self.db.fetch("SELECT id, nombre, precio, stock, proveedor_id FROM Productos ORDER BY id DESC")
        for prod in products:
            self.tree.insert("", "end", values=prod)

    def filter_products(self, _event=None):
        search_term = self.search_var.get().strip().lower()
        if not search_term:
            self.load_products()
            return

        self.tree.delete(*self.tree.get_children())
        products = self.db.fetch("SELECT id, nombre, precio, stock, proveedor_id FROM Productos")
        for prod in products:
            if search_term in str(prod[1]).lower():
                self.tree.insert("", "end", values=prod)

    def select_product(self, _event):
        selected_item = self.tree.focus()
        if not selected_item:
            return

        values = self.tree.item(selected_item, "values")
        product_id = values[0]
        full_data = self.db.fetch(
            "SELECT nombre, precio, stock, descripcion, proveedor_id FROM Productos WHERE id = ?",
            (product_id,),
        )
        if not full_data:
            return

        data = full_data[0]
        self.product_id.set(product_id)
        self.nombre.set(data[0])
        self.precio.set(data[1])
        self.stock.set(data[2])
        self.proveedor_id.set(data[4])

        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert(tk.END, data[3] or "")

    def reset_form(self):
        self.product_id.set("")
        self.nombre.set("")
        self.precio.set("")
        self.stock.set("")
        self.proveedor_id.set("1")
        self.desc_text.delete("1.0", tk.END)

    def save_product(self):
        nombre = self.nombre.get().strip()
        precio = self.precio.get().strip()
        stock = self.stock.get().strip()
        descripcion = self.desc_text.get("1.0", tk.END).strip()
        proveedor_id = self.proveedor_id.get().strip()

        if not all([nombre, precio, stock, proveedor_id]):
            self._show_error("Error", "Complete todos los campos obligatorios.")
            return

        try:
            precio_val = float(precio)
            stock_val = int(stock)
            prov_id_val = int(proveedor_id)
        except ValueError:
            self._show_error("Error", "Precio, stock y proveedor ID deben ser números válidos.")
            return

        if self.product_id.get():
            self.db.execute(
                """
                    UPDATE Productos
                    SET nombre=?, precio=?, stock=?, descripcion=?, proveedor_id=?
                    WHERE id=?
                """,
                (nombre, precio_val, stock_val, descripcion, prov_id_val, self.product_id.get()),
            )
            self._show_info("Éxito", "Producto actualizado correctamente.")
        else:
            self.db.execute(
                """
                    INSERT INTO Productos (nombre, precio, stock, descripcion, proveedor_id)
                    VALUES (?, ?, ?, ?, ?)
                """,
                (nombre, precio_val, stock_val, descripcion, prov_id_val),
            )
            self._show_info("Éxito", "Producto agregado correctamente.")

        self.load_products()
        self.reset_form()

    def delete_product(self):
        selected_item = self.tree.focus()
        if not selected_item:
            self._show_warning("Advertencia", "Seleccione un producto primero.")
            return

        prod_id = self.tree.item(selected_item, "values")[0]
        if self._ask_yes_no("Confirmar", f"¿Eliminar el producto ID {prod_id}?"):
            self.db.execute("DELETE FROM Productos WHERE id = ?", (prod_id,))
            self._show_info("Éxito", "Producto eliminado.")
            self.load_products()
            self.reset_form()

    def refresh_products(self):
        """Método público para refrescar la lista (usado por FileManager)."""
        self.load_products()
