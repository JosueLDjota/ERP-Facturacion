"""
frames/products.py
Gestion de productos con CRUD e importacion/exportacion.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from .ui import create_modal, format_hnl, normalize_hnl_amount, parse_hnl


class ProductFrame(ttk.Frame):
    """Frame para gestion de productos con CRUD completo."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.db = app.db

        self.product_id = tk.StringVar(value="")
        self.nombre = tk.StringVar()
        self.precio = tk.StringVar()
        self.stock = tk.StringVar()
        self.proveedor_id = tk.StringVar(value="")
        self.proveedor_nombre = tk.StringVar()
        self.search_var = tk.StringVar()
        self.new_product_popup = None
        self.supplier_name_to_id = {}
        self.supplier_id_to_name = {}

        self._build_ui()
        self._load_supplier_options()
        self.load_products()

    def _build_ui(self):
        self.columnconfigure(0, weight=7)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Gestion de productos", style="Header.TLabel").grid(
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
            columns=("Nombre", "Precio", "Stock", "Proveedor"),
            show="headings",
            height=15,
        )
        self.tree.grid(row=1, column=0, sticky="nsew")

        for col, width, anchor in (
            ("Nombre", 300, "w"),
            ("Precio", 120, "e"),
            ("Stock", 90, "center"),
            ("Proveedor", 180, "w"),
        ):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)

        y_scroll = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        y_scroll.grid(row=1, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self.select_product)

        btn_frame = ttk.Frame(self.list_frame, style="Surface.TFrame")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        btn_frame.columnconfigure(0, weight=1)

        ttk.Button(
            btn_frame,
            text="Nuevo producto",
            style="Secondary.TButton",
            command=self.open_new_product_modal,
        ).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Eliminar", style="Danger.TButton", command=self.delete_product).pack(
            side="left", padx=6
        )
        ttk.Button(
            btn_frame,
            text="Ajustar precios HNL",
            style="Secondary.TButton",
            command=self.open_price_optimizer,
        ).pack(side="left", padx=6)
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
            ("Precio (HNL):", self.precio),
            ("Stock:", self.stock),
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

        ttk.Label(self.form_frame, text="Proveedor:", style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="w", padx=4, pady=7
        )
        self.proveedor_combo = ttk.Combobox(
            self.form_frame,
            textvariable=self.proveedor_nombre,
            state="readonly",
        )
        self.proveedor_combo.grid(row=row, column=1, sticky="ew", padx=4, pady=7)
        self.proveedor_combo.bind("<<ComboboxSelected>>", self._on_supplier_form_selected)
        row += 1

        ttk.Label(self.form_frame, text="Descripcion:", style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="nw", padx=4, pady=7
        )
        self.desc_text = tk.Text(self.form_frame, height=5, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.desc_text.grid(row=row, column=1, sticky="ew", padx=4, pady=7)
        row += 1

        ttk.Button(self.form_frame, text="Guardar producto", style="Primary.TButton", command=self.save_product).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(14, 4)
        )

    def _render_products(self, products):
        self.tree.delete(*self.tree.get_children())
        for prod in products:
            prod_id, nombre, precio, stock, proveedor_nombre, _codigo_producto = prod
            self.tree.insert(
                "",
                "end",
                iid=str(prod_id),
                values=(nombre, format_hnl(precio), stock, proveedor_nombre or "Sin proveedor"),
            )

    def load_products(self):
        products = self.db.fetch(
            """
            SELECT p.id, p.nombre, p.precio, p.stock, COALESCE(pr.nombre, 'Sin proveedor'), COALESCE(p.codigo_producto, '')
            FROM Productos p
            LEFT JOIN Proveedores pr ON pr.id = p.proveedor_id
            ORDER BY p.id DESC
            """
        )
        self._render_products(products)

    def filter_products(self, _event=None):
        search_term = self.search_var.get().strip().lower()
        if not search_term:
            self.load_products()
            return

        products = self.db.fetch(
            """
            SELECT p.id, p.nombre, p.precio, p.stock, COALESCE(pr.nombre, 'Sin proveedor'), COALESCE(p.codigo_producto, '')
            FROM Productos p
            LEFT JOIN Proveedores pr ON pr.id = p.proveedor_id
            """
        )
        filtered = [
            prod
            for prod in products
            if search_term in str(prod[1]).lower() or search_term in str(prod[5]).lower()
        ]
        self._render_products(filtered)

    def select_product(self, _event):
        selected_item = self.tree.focus()
        if not selected_item:
            return

        product_id = selected_item
        full_data = self.db.fetch(
            "SELECT nombre, precio, stock, descripcion, proveedor_id FROM Productos WHERE id = ?",
            (product_id,),
        )
        if not full_data:
            return

        data = full_data[0]
        self.product_id.set(product_id)
        self.nombre.set(data[0])
        self.precio.set(f"{normalize_hnl_amount(data[1]):.2f}")
        self.stock.set(data[2])
        self.proveedor_id.set(str(data[4] or ""))
        self.proveedor_nombre.set(self.supplier_id_to_name.get(self.proveedor_id.get(), ""))

        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert(tk.END, data[3] or "")

    def reset_form(self):
        self.product_id.set("")
        self.nombre.set("")
        self.precio.set("")
        self.stock.set("")
        self.proveedor_id.set("")
        self._load_supplier_options()
        self.desc_text.delete("1.0", tk.END)

    def _load_supplier_options(self):
        supplier_rows = self.db.fetch("SELECT id, nombre FROM Proveedores ORDER BY nombre")
        self.supplier_name_to_id = {}
        self.supplier_id_to_name = {}
        supplier_labels = []

        for supplier_id, supplier_name in supplier_rows:
            base_label = str(supplier_name or f"Proveedor {supplier_id}").strip()
            unique_label = base_label
            suffix = 2
            while unique_label in self.supplier_name_to_id:
                unique_label = f"{base_label} ({suffix})"
                suffix += 1

            supplier_id_str = str(supplier_id)
            self.supplier_name_to_id[unique_label] = supplier_id_str
            self.supplier_id_to_name[supplier_id_str] = unique_label
            supplier_labels.append(unique_label)

        if hasattr(self, "proveedor_combo"):
            self.proveedor_combo["values"] = supplier_labels

        current_supplier_id = str(self.proveedor_id.get() or "").strip()
        if current_supplier_id and current_supplier_id in self.supplier_id_to_name:
            self.proveedor_nombre.set(self.supplier_id_to_name[current_supplier_id])
            return

        if supplier_labels:
            default_label = supplier_labels[0]
            self.proveedor_nombre.set(default_label)
            self.proveedor_id.set(self.supplier_name_to_id[default_label])
            return

        self.proveedor_nombre.set("")
        self.proveedor_id.set("")

    def _on_supplier_form_selected(self, _event=None):
        supplier_name = self.proveedor_nombre.get().strip()
        self.proveedor_id.set(self.supplier_name_to_id.get(supplier_name, ""))

    def _validate_codigo_producto(self, codigo_producto, current_product_id=None):
        codigo_producto = str(codigo_producto or "").strip()
        if not codigo_producto:
            return ""

        if not codigo_producto.isdigit():
            self._show_error("Error", "El codigo de producto solo puede contener numeros.")
            return None

        if len(codigo_producto) > 13:
            self._show_error("Error", "El codigo de producto no puede exceder 13 digitos.")
            return None

        params = [codigo_producto]
        query = "SELECT id FROM Productos WHERE codigo_producto = ?"
        if current_product_id not in (None, ""):
            query += " AND id <> ?"
            params.append(current_product_id)

        if self.db.fetch(query, tuple(params)):
            self._show_error("Error", "El codigo de producto ya existe.")
            return None

        return codigo_producto

    def _validate_product_payload(self, nombre, precio, stock, proveedor_id, codigo_producto="", current_product_id=None):
        if not all([nombre, precio, stock, proveedor_id]):
            self._show_error("Error", "Complete todos los campos obligatorios.")
            return None

        try:
            precio_val = normalize_hnl_amount(parse_hnl(precio))
            stock_val = int(stock)
            prov_id_val = int(proveedor_id)
        except ValueError:
            self._show_error("Error", "Precio HNL, stock y proveedor deben ser valores validos.")
            return None

        if precio_val <= 0:
            self._show_error("Error", "El precio en HNL debe ser mayor que 0.")
            return None

        if stock_val < 0:
            self._show_error("Error", "El stock no puede ser negativo.")
            return None

        codigo_validado = self._validate_codigo_producto(codigo_producto, current_product_id=current_product_id)
        if codigo_validado is None:
            return None

        return precio_val, stock_val, prov_id_val, codigo_validado

    def save_product(self):
        nombre = self.nombre.get().strip()
        precio = self.precio.get().strip()
        stock = self.stock.get().strip()
        descripcion = self.desc_text.get("1.0", tk.END).strip()
        proveedor_id = self.proveedor_id.get().strip()

        validated = self._validate_product_payload(
            nombre,
            precio,
            stock,
            proveedor_id,
            current_product_id=self.product_id.get(),
        )
        if not validated:
            return
        precio_val, stock_val, prov_id_val, _codigo_validado = validated

        if self.product_id.get():
            self.db.execute(
                """
                    UPDATE Productos
                    SET nombre=?, precio=?, stock=?, descripcion=?, proveedor_id=?
                    WHERE id=?
                """,
                (nombre, precio_val, stock_val, descripcion, prov_id_val, self.product_id.get()),
            )
            self._show_info("Exito", "Producto actualizado correctamente.")
        else:
            self.db.execute(
                """
                    INSERT INTO Productos (nombre, precio, stock, descripcion, proveedor_id)
                    VALUES (?, ?, ?, ?, ?)
                """,
                (nombre, precio_val, stock_val, descripcion, prov_id_val),
            )
            self._show_info("Exito", "Producto agregado correctamente.")

        self.load_products()
        self.reset_form()

    def _fetch_supplier_matches(self, search_term="", limit=8):
        """Busca proveedores por coincidencia parcial de nombre."""
        token = str(search_term or "").strip().lower()
        query = """
            SELECT id, nombre
            FROM Proveedores
        """
        params = ()
        if token:
            query += " WHERE LOWER(nombre) LIKE ?"
            params = (f"%{token}%",)
        query += " ORDER BY nombre LIMIT ?"
        params = (*params, int(limit))
        return self.db.fetch(query, params)

    def open_new_product_modal(self):
        if self.new_product_popup and self.new_product_popup.winfo_exists():
            self.new_product_popup.deiconify()
            self.new_product_popup.lift()
            return

        popup = create_modal(self._parent(), "Nuevo producto", width=700, height=640)
        self.new_product_popup = popup
        popup.protocol("WM_DELETE_WINDOW", self._close_new_product_modal)

        content = ttk.Frame(popup, padding=18, style="Surface.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(7, weight=1)

        nombre_var = tk.StringVar()
        precio_var = tk.StringVar()
        stock_var = tk.StringVar(value="0")
        codigo_producto_var = tk.StringVar()
        proveedor_var = tk.StringVar()
        supplier_search_var = tk.StringVar()
        supplier_status_var = tk.StringVar(value="Seleccione un proveedor de la lista.")
        supplier_matches = []

        ttk.Label(
            content,
            text="Registre un producto nuevo en una ventana independiente.",
            style="Muted.TLabel",
            wraplength=540,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        fields = [
            ("Nombre:", nombre_var),
            ("Precio (HNL):", precio_var),
            ("Stock:", stock_var),
            ("Codigo producto:", codigo_producto_var),
        ]

        for row, (label_text, variable) in enumerate(fields, start=1):
            ttk.Label(content, text=label_text, style="FormLabel.TLabel").grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 10),
                pady=6,
            )
            ttk.Entry(content, textvariable=variable).grid(
                row=row,
                column=1,
                sticky="ew",
                pady=6,
            )

        ttk.Label(content, text="Buscar proveedor:", style="FormLabel.TLabel").grid(
            row=5,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=6,
        )
        supplier_entry = ttk.Entry(content, textvariable=supplier_search_var)
        supplier_entry.grid(row=5, column=1, sticky="ew", pady=6)

        ttk.Label(content, textvariable=supplier_status_var, style="Muted.TLabel", wraplength=520).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 6),
        )

        supplier_listbox = tk.Listbox(content, height=6, exportselection=False, relief="solid", borderwidth=1)
        supplier_listbox.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(0, 10))

        ttk.Label(content, text="Descripcion:", style="FormLabel.TLabel").grid(
            row=8,
            column=0,
            sticky="nw",
            padx=(0, 10),
            pady=6,
        )
        desc_text = tk.Text(content, height=8, wrap=tk.WORD, relief="solid", borderwidth=1)
        desc_text.grid(row=8, column=1, sticky="nsew", pady=6)

        actions = ttk.Frame(content, style="Surface.TFrame")
        actions.grid(row=9, column=0, columnspan=2, sticky="e", pady=(16, 0))

        def refresh_supplier_suggestions(*_args):
            nonlocal supplier_matches
            supplier_matches = self._fetch_supplier_matches(supplier_search_var.get())
            supplier_listbox.delete(0, tk.END)
            for _supplier_id, supplier_name in supplier_matches:
                supplier_listbox.insert(tk.END, supplier_name)

            if not supplier_matches:
                proveedor_var.set("")
                supplier_status_var.set("No hay coincidencias. Siga escribiendo o cree el proveedor antes.")
            elif proveedor_var.get() and all(str(match[0]) != proveedor_var.get() for match in supplier_matches):
                proveedor_var.set("")
                supplier_status_var.set("Seleccione un proveedor de la lista.")
            elif not proveedor_var.get():
                supplier_status_var.set("Seleccione un proveedor de la lista.")

        def choose_supplier(_event=None):
            nonlocal supplier_matches
            selection = supplier_listbox.curselection()
            if not selection:
                return
            supplier_id, supplier_name = supplier_matches[selection[0]]
            proveedor_var.set(str(supplier_id))
            supplier_search_var.set(supplier_name)
            supplier_status_var.set(f"Proveedor seleccionado: {supplier_name}.")
            supplier_listbox.selection_clear(0, tk.END)

        supplier_search_var.trace_add("write", refresh_supplier_suggestions)
        supplier_listbox.bind("<<ListboxSelect>>", choose_supplier)
        supplier_listbox.bind("<Double-Button-1>", choose_supplier)
        refresh_supplier_suggestions()

        def submit_new_product():
            nombre = nombre_var.get().strip()
            precio = precio_var.get().strip()
            stock = stock_var.get().strip()
            proveedor_id = proveedor_var.get().strip()
            codigo_producto = codigo_producto_var.get().strip()
            descripcion = desc_text.get("1.0", tk.END).strip()

            validated = self._validate_product_payload(
                nombre,
                precio,
                stock,
                proveedor_id,
                codigo_producto=codigo_producto,
            )
            if not validated:
                return
            precio_val, stock_val, prov_id_val, codigo_validado = validated

            result = self.db.execute(
                """
                    INSERT INTO Productos (nombre, precio, stock, descripcion, proveedor_id, codigo_producto)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    nombre,
                    precio_val,
                    stock_val,
                    descripcion,
                    prov_id_val,
                    codigo_validado or None,
                ),
            )
            if result is None:
                error_text = str(self.db.last_error or "No se pudo guardar el producto.")
                self._show_error("Error", error_text)
                return

            self.load_products()
            self._show_info("Exito", "Producto agregado correctamente.")
            self._close_new_product_modal()

        ttk.Button(actions, text="Cancelar", style="Secondary.TButton", command=self._close_new_product_modal).pack(
            side="right"
        )
        ttk.Button(actions, text="Guardar producto", style="Primary.TButton", command=submit_new_product).pack(
            side="right", padx=(0, 8)
        )

        supplier_entry.bind("<Down>", lambda _event: supplier_listbox.focus_set())

        first_entry = content.grid_slaves(row=1, column=1)
        if first_entry:
            first_entry[0].focus_set()

    def _close_new_product_modal(self):
        if self.new_product_popup and self.new_product_popup.winfo_exists():
            self.new_product_popup.destroy()
        self.new_product_popup = None

    def open_price_optimizer(self):
        popup = create_modal(self._parent(), "Ajuste competitivo de precios", width=520, height=360)
        content = ttk.Frame(popup, padding=16, style="Surface.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)

        ttk.Label(
            content,
            text="Aplique ajuste porcentual y redondeo en HNL para mantener precios competitivos.",
            style="Muted.TLabel",
            wraplength=460,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        pct_var = tk.StringVar(value="-2")
        step_var = tk.StringVar(value="0.50")

        ttk.Label(content, text="Ajuste (%):", style="FormLabel.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(content, textvariable=pct_var).grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(content, text="Redondeo HNL:", style="FormLabel.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Combobox(
            content,
            textvariable=step_var,
            state="readonly",
            values=("0.01", "0.10", "0.50", "1.00", "5.00"),
        ).grid(row=2, column=1, sticky="ew", pady=6)

        preview_var = tk.StringVar(value="")
        ttk.Label(content, textvariable=preview_var, style="Muted.TLabel", wraplength=460).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 12)
        )

        rows = self.db.fetch("SELECT COUNT(*), COALESCE(AVG(precio), 0) FROM Productos")
        total_products = int(rows[0][0] or 0) if rows else 0
        avg_price = float(rows[0][1] or 0) if rows else 0
        preview_var.set(f"Productos a ajustar: {total_products}. Precio promedio actual: {format_hnl(avg_price)}.")

        btn_row = ttk.Frame(content, style="Surface.TFrame")
        btn_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        btn_row.columnconfigure(0, weight=1)

        def apply_adjustment():
            try:
                pct = float(pct_var.get().strip())
                step = float(step_var.get().strip())
            except ValueError:
                self._show_error("Error", "Ingrese valores numericos validos para ajuste y redondeo.")
                return

            if step <= 0:
                self._show_error("Error", "El redondeo debe ser mayor que 0.")
                return

            products = self.db.fetch("SELECT id, precio FROM Productos")
            updated = 0
            for prod_id, old_price in products:
                base_price = normalize_hnl_amount(old_price)
                adjusted_price = base_price * (1 + (pct / 100.0))
                adjusted_price = round(adjusted_price / step) * step
                adjusted_price = max(0.01, normalize_hnl_amount(adjusted_price))
                self.db.execute("UPDATE Productos SET precio = ? WHERE id = ?", (adjusted_price, prod_id))
                updated += 1

            popup.destroy()
            self.load_products()
            self._show_info(
                "Exito",
                f"Precios ajustados en {updated} productos.\nAjuste aplicado: {pct:.2f}% | Redondeo: {step:.2f} HNL.",
            )

        ttk.Button(btn_row, text="Cancelar", style="Secondary.TButton", command=popup.destroy).pack(side="right")
        ttk.Button(btn_row, text="Aplicar ajuste", style="Primary.TButton", command=apply_adjustment).pack(
            side="right", padx=(0, 8)
        )

    def delete_product(self):
        selected_item = self.tree.focus()
        if not selected_item:
            self._show_warning("Advertencia", "Seleccione un producto primero.")
            return

        prod_id = selected_item
        product_name = self.tree.item(selected_item, "values")[0]
        if self._ask_yes_no("Confirmar", f"Eliminar el producto \"{product_name}\"?"):
            self.db.execute("DELETE FROM Productos WHERE id = ?", (prod_id,))
            self._show_info("Exito", "Producto eliminado.")
            self.load_products()
            self.reset_form()

    def refresh_products(self):
        """Metodo publico para refrescar la lista (usado por FileManager)."""
        self.load_products()
