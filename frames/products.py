"""
frames/products.py
Gestion de productos con CRUD e importacion/exportacion.
"""

# Contexto del archivo:
# Este modulo conserva la interfaz legacy de productos con formularios,
# buscadores, importacion CSV y ajuste masivo de precios.
# La validacion y la persistencia importante ya no deberian decidirse aqui:
# se delegan a servicios, repositorios y casos de uso dentro de `erp/`.

import tkinter as tk
from tkinter import messagebox, ttk

from erp.data.repositories.product_repository import ProductRepository, RepositoryError as ProductRepositoryError
from erp.data.repositories.product_taxonomy_repository import ProductTaxonomyRepository
from erp.data.repositories.supplier_repository import SupplierRepository
from erp.domain.services.price_adjustment_service import PriceAdjustmentService
from erp.domain.services.product_validation_service import ProductValidationService
from erp.domain.use_cases.products.adjust_prices import AdjustPrices
from erp.domain.use_cases.products.delete_product import DeleteProduct
from erp.domain.use_cases.products.list_products import ListProducts
from erp.domain.use_cases.products.save_product import SaveProduct
from .ui import create_modal, format_hnl, normalize_hnl_amount


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
        self.codigo_producto = tk.StringVar()
        self.proveedor_id = tk.StringVar(value="")
        self.proveedor_nombre = tk.StringVar()
        self.categoria_id = tk.StringVar(value="")
        self.categoria_nombre = tk.StringVar()
        self.marca_id = tk.StringVar(value="")
        self.marca_nombre = tk.StringVar()
        self.search_var = tk.StringVar()
        self.supplier_name_to_id = {}
        self.supplier_id_to_name = {}
        self.category_name_to_id = {}
        self.category_id_to_name = {}
        self.brand_name_to_id = {}
        self.brand_id_to_name = {}
        self.product_repository = ProductRepository(self.db)
        self.supplier_repository = SupplierRepository(self.db)
        self.taxonomy_repository = ProductTaxonomyRepository(self.db)
        self.product_validation_service = ProductValidationService()
        self.price_adjustment_service = PriceAdjustmentService()
        self.list_products_use_case = ListProducts(self.product_repository)
        self.save_product_use_case = SaveProduct(
            self.product_repository,
            self.supplier_repository,
            self.product_validation_service,
            self.taxonomy_repository,
        )
        self.delete_product_use_case = DeleteProduct(self.product_repository)
        self.adjust_prices_use_case = AdjustPrices(self.product_repository, self.price_adjustment_service)

        self._build_ui()
        self._load_supplier_options()
        self._load_category_options()
        self._load_brand_options()
        self.load_products()

    def _build_ui(self):
        self.columnconfigure(0, weight=8)
        self.columnconfigure(1, weight=5)
        self.rowconfigure(0, weight=1)


        self.list_frame = ttk.LabelFrame(self, text="Listado de productos", style="Card.TLabelframe")
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.rowconfigure(1, weight=1)

        self.form_frame = ttk.LabelFrame(self, text="Formulario de producto", style="Card.TLabelframe")
        self.form_frame.grid(row=0, column=1, sticky="nsew")
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
        ttk.Label(
            search_frame,
            text="Nombre, codigo, categoria o marca",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        tree_container = ttk.Frame(self.list_frame, style="Surface.TFrame")
        tree_container.grid(row=1, column=0, sticky="nsew")
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_container,
            columns=("Nombre", "Categoria", "Marca", "Precio", "Stock", "Proveedor"),
            show="headings",
            height=15,
        )
        self.tree.grid(row=0, column=0, sticky="nsew")

        for col, width, anchor in (
            ("Nombre", 250, "w"),
            ("Categoria", 150, "w"),
            ("Marca", 130, "w"),
            ("Precio", 120, "e"),
            ("Stock", 80, "center"),
            ("Proveedor", 180, "w"),
        ):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)

        y_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=x_scroll.set)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self.select_product)

        btn_frame = ttk.Frame(self.list_frame, style="Surface.TFrame")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        btn_frame.columnconfigure(0, weight=1)

        ttk.Button(
            btn_frame,
            text="Nuevo producto",
            style="Secondary.TButton",
            command=self.start_new_product,
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
            ("Codigo producto:", self.codigo_producto),
        ]

        row = 0
        for label_text, var in fields:
            ttk.Label(self.form_frame, text=label_text, style="FormLabel.TLabel").grid(
                row=row, column=0, sticky="w", padx=4, pady=7
            )
            entry = ttk.Entry(self.form_frame, textvariable=var)
            entry.grid(
                row=row, column=1, sticky="ew", padx=4, pady=7
            )
            if row == 0:
                self.nombre_entry = entry
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

        ttk.Label(self.form_frame, text="Categoria:", style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="w", padx=4, pady=7
        )
        self.categoria_combo = ttk.Combobox(
            self.form_frame,
            textvariable=self.categoria_nombre,
            state="readonly",
        )
        self.categoria_combo.grid(row=row, column=1, sticky="ew", padx=4, pady=7)
        self.categoria_combo.bind("<<ComboboxSelected>>", self._on_category_form_selected)
        row += 1

        ttk.Label(self.form_frame, text="Marca:", style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="w", padx=4, pady=7
        )
        self.marca_combo = ttk.Combobox(
            self.form_frame,
            textvariable=self.marca_nombre,
            state="readonly",
        )
        self.marca_combo.grid(row=row, column=1, sticky="ew", padx=4, pady=7)
        self.marca_combo.bind("<<ComboboxSelected>>", self._on_brand_form_selected)
        row += 1

        ttk.Label(self.form_frame, text="Descripcion:", style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="nw", padx=4, pady=7
        )
        self.form_frame.rowconfigure(row, weight=1)
        self.desc_text = tk.Text(self.form_frame, height=4, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.desc_text.grid(row=row, column=1, sticky="ew", padx=4, pady=7)
        row += 1

        ttk.Button(self.form_frame, text="Guardar producto", style="Primary.TButton", command=self.save_product).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(14, 4)
        )

    def _render_products(self, products):
        self.tree.delete(*self.tree.get_children())
        for prod in products:
            prod_id = int(prod["id"])
            nombre = prod["nombre"]
            precio = prod["precio"]
            stock = prod["stock"]
            proveedor_nombre = prod["proveedor_nombre"]
            categoria_nombre = prod["categoria_nombre"]
            marca_nombre = prod["marca_nombre"]
            self.tree.insert(
                "",
                "end",
                iid=str(prod_id),
                values=(
                    nombre,
                    categoria_nombre or "Sin categoria",
                    marca_nombre or "Sin marca",
                    format_hnl(precio),
                    stock,
                    proveedor_nombre or "Sin proveedor",
                ),
            )

    def load_products(self, search_term=""):
        products = self.list_products_use_case.execute(search_term)
        self._render_products(products)

    def filter_products(self, _event=None):
        search_term = self.search_var.get().strip().lower()
        self.load_products(search_term)

    def select_product(self, _event):
        selected_item = self.tree.focus()
        if not selected_item:
            return

        product_id = selected_item
        data = self.product_repository.get_detail(int(product_id))
        if not data:
            return

        self.product_id.set(product_id)
        self.nombre.set(data["nombre"])
        self.precio.set(f"{normalize_hnl_amount(data['precio']):.2f}")
        self.stock.set(data["stock"])
        self.codigo_producto.set(data["codigo_producto"])
        self.proveedor_id.set(str(data["proveedor_id"] or ""))
        self.proveedor_nombre.set(self.supplier_id_to_name.get(self.proveedor_id.get(), ""))
        self.categoria_id.set(str(data["categoria_id"] or ""))
        self.categoria_nombre.set(self.category_id_to_name.get(self.categoria_id.get(), ""))
        self.marca_id.set(str(data["marca_id"] or ""))
        self.marca_nombre.set(self.brand_id_to_name.get(self.marca_id.get(), ""))

        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert(tk.END, data["descripcion"] or "")

    def reset_form(self):
        self.product_id.set("")
        self.nombre.set("")
        self.precio.set("")
        self.stock.set("")
        self.codigo_producto.set("")
        self.proveedor_id.set("")
        self.proveedor_nombre.set("")
        self.categoria_id.set("")
        self.categoria_nombre.set("")
        self.marca_id.set("")
        self.marca_nombre.set("")
        self._load_supplier_options()
        self._load_category_options()
        self._load_brand_options()
        self.desc_text.delete("1.0", tk.END)

    def start_new_product(self):
        self.reset_form()
        self.tree.selection_remove(self.tree.selection())
        self.tree.focus("")
        self.nombre_entry.focus_set()

    def _load_choice_options(
        self,
        *,
        rows,
        combo_attr: str,
        id_var: tk.StringVar,
        name_var: tk.StringVar,
        name_to_id_attr: str,
        id_to_name_attr: str,
        fallback_prefix: str,
    ):
        name_to_id = {}
        id_to_name = {}
        labels = []

        for row in rows:
            item_id = row["id"]
            item_name = row["nombre"]
            base_label = str(item_name or f"{fallback_prefix} {item_id}").strip()
            unique_label = base_label
            suffix = 2
            while unique_label in name_to_id:
                unique_label = f"{base_label} ({suffix})"
                suffix += 1

            item_id_str = str(item_id)
            name_to_id[unique_label] = item_id_str
            id_to_name[item_id_str] = unique_label
            labels.append(unique_label)

        setattr(self, name_to_id_attr, name_to_id)
        setattr(self, id_to_name_attr, id_to_name)

        combo = getattr(self, combo_attr, None)
        if combo is not None:
            combo["values"] = labels

        current_id = str(id_var.get() or "").strip()
        if current_id and current_id in id_to_name:
            name_var.set(id_to_name[current_id])
            return

        if labels:
            default_label = labels[0]
            name_var.set(default_label)
            id_var.set(name_to_id[default_label])
            return

        name_var.set("")
        id_var.set("")

    def _load_supplier_options(self):
        self._load_choice_options(
            rows=self.supplier_repository.list_choices(),
            combo_attr="proveedor_combo",
            id_var=self.proveedor_id,
            name_var=self.proveedor_nombre,
            name_to_id_attr="supplier_name_to_id",
            id_to_name_attr="supplier_id_to_name",
            fallback_prefix="Proveedor",
        )

    def _load_category_options(self):
        self._load_choice_options(
            rows=self.taxonomy_repository.list_category_choices(),
            combo_attr="categoria_combo",
            id_var=self.categoria_id,
            name_var=self.categoria_nombre,
            name_to_id_attr="category_name_to_id",
            id_to_name_attr="category_id_to_name",
            fallback_prefix="Categoria",
        )

    def _load_brand_options(self):
        self._load_choice_options(
            rows=self.taxonomy_repository.list_brand_choices(),
            combo_attr="marca_combo",
            id_var=self.marca_id,
            name_var=self.marca_nombre,
            name_to_id_attr="brand_name_to_id",
            id_to_name_attr="brand_id_to_name",
            fallback_prefix="Marca",
        )

    def _on_supplier_form_selected(self, _event=None):
        supplier_name = self.proveedor_nombre.get().strip()
        self.proveedor_id.set(self.supplier_name_to_id.get(supplier_name, ""))

    def _on_category_form_selected(self, _event=None):
        category_name = self.categoria_nombre.get().strip()
        self.categoria_id.set(self.category_name_to_id.get(category_name, ""))

    def _on_brand_form_selected(self, _event=None):
        brand_name = self.marca_nombre.get().strip()
        self.marca_id.set(self.brand_name_to_id.get(brand_name, ""))

    def _require_selection(self, value: str, *, label: str) -> bool:
        if str(value or "").strip():
            return True
        self._show_error("Error", f"Debe seleccionar una {label} valida.")
        return False

    def save_product(self):
        if self.product_id.get():
            action_text = "actualizado"
        else:
            action_text = "agregado"

        if not self._require_selection(self.categoria_id.get(), label="categoria"):
            return
        if not self._require_selection(self.marca_id.get(), label="marca"):
            return
        if self.product_id.get() and not self._ask_yes_no(
            "Confirmar cambios",
            "¿Estás seguro de los cambios que harás en este producto?",
        ):
            return

        try:
            self.save_product_use_case.execute(
                nombre=self.nombre.get().strip(),
                precio=self.precio.get().strip(),
                stock=self.stock.get().strip(),
                proveedor_id=self.proveedor_id.get().strip(),
                descripcion=self.desc_text.get("1.0", tk.END).strip(),
                codigo_producto=self.codigo_producto.get().strip(),
                categoria_id=self.categoria_id.get().strip(),
                marca_id=self.marca_id.get().strip(),
                product_id=int(self.product_id.get()) if self.product_id.get() else None,
            )
        except (ValueError, ProductRepositoryError) as exc:
            self._show_error("Error", str(exc))
            return

        self.load_products()
        self.reset_form()
        self._show_info("Éxito", f"Producto {action_text} correctamente.")

    def focus_product(self, product_id):
        """Carga y enfoca un producto concreto dentro del listado para edición rápida."""
        product_key = str(product_id or "").strip()
        if not product_key:
            return

        self.search_var.set("")
        self.load_products()

        if not self.tree.exists(product_key):
            self._show_warning("Producto no encontrado", "No se pudo ubicar el producto solicitado.")
            return

        self.tree.selection_set(product_key)
        self.tree.focus(product_key)
        self.tree.see(product_key)
        self.select_product(None)

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

        preview = self.adjust_prices_use_case.get_preview()
        total_products = preview.total_products
        avg_price = preview.average_price
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

            try:
                result = self.adjust_prices_use_case.execute(pct=pct, step=step)
            except (ValueError, ProductRepositoryError) as exc:
                self._show_error("Error", str(exc))
                return

            popup.destroy()
            self.load_products()
            self._show_info(
                "Éxito",
                f"Precios ajustados en {result.updated} productos.\nAjuste aplicado: {pct:.2f}% | Redondeo: {step:.2f} HNL.",
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
            try:
                self.delete_product_use_case.execute(int(prod_id))
            except ProductRepositoryError as exc:
                self._show_error("Error", str(exc))
                return
            self._show_info("Éxito", "Producto eliminado.")
            self.load_products()
            self.reset_form()

    def refresh_products(self):
        """Método público para refrescar la lista (usado por FileManager)."""
        self.load_products()


