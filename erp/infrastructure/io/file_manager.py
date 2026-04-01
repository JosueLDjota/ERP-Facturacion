"""
Gestor de importación y exportación de datos CSV.
"""

# Contexto del archivo:
# Adaptador de infraestructura para importacion y exportacion de archivos.
# Coordina dialogos de escritorio, lectura/escritura CSV y casos de uso de
# productos sin mezclar esas responsabilidades dentro de `main.py` o de los
# frames de la UI.

import csv
import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox, ttk

from erp.data.repositories.product_repository import ProductRepository, RepositoryError as ProductRepositoryError
from erp.data.repositories.supplier_repository import SupplierRepository
from erp.domain.services.product_import_service import ProductImportService
from erp.domain.services.product_validation_service import ProductValidationService
from erp.domain.use_cases.products.bulk_import_products import BulkImportProducts
from erp.ui.shared import format_hnl, normalize_hnl_amount, parse_hnl


def center_window(window, width, height, parent=None):
    window.update_idletasks()
    base = parent if parent is not None else window
    x = base.winfo_rootx() + max(0, (base.winfo_width() - width) // 2)
    y = base.winfo_rooty() + max(0, (base.winfo_height() - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


class FileManager:
    TABLE_MAP = {
        "Productos": "Productos.csv",
        "Proveedores": "Proveedores.csv",
        "Usuarios": "Usuarios.csv",
        "Descuentos": "Descuentos.csv",
    }

    def __init__(self, db_manager):
        self.db = db_manager
        self.product_repository = ProductRepository(self.db)
        self.supplier_repository = SupplierRepository(self.db)
        self.product_validation_service = ProductValidationService()
        self.product_import_service = ProductImportService(self.product_validation_service)
        self.bulk_import_products_use_case = BulkImportProducts(
            self.product_repository,
            self.supplier_repository,
            self.product_import_service,
        )

    def get_data_from_db(self, table_name):
        if table_name == "Productos":
            return self.product_repository.export_rows()
        if table_name == "Proveedores":
            return self.db.fetch("SELECT id, nombre, contacto, telefono FROM Proveedores")
        if table_name == "Usuarios":
            return self.db.fetch("SELECT id, nombre, usuario, rol FROM Usuarios")
        if table_name == "Descuentos":
            return self.db.fetch("SELECT id, nombre, tipo, porcentaje FROM Descuentos")
        return []

    def export_data(self, table_name):
        data = self.get_data_from_db(table_name)
        if not data:
            messagebox.showinfo("Exportar", f"No hay datos en {table_name} para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=self.TABLE_MAP.get(table_name, "data.csv"),
            title=f"Guardar datos de {table_name}",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = {
                    "Productos": ["id", "nombre", "descripcion", "precio", "stock", "proveedor_id", "codigo_producto"],
                    "Proveedores": ["id", "nombre", "contacto", "telefono"],
                    "Usuarios": ["id", "nombre", "usuario", "rol"],
                    "Descuentos": ["id", "nombre", "tipo", "porcentaje"],
                }
                writer.writerow(headers.get(table_name, []))
                writer.writerows(data)
            messagebox.showinfo("Éxito", f"Datos exportados a:\n{file_path}")
        except Exception as exc:
            messagebox.showerror("Error", f"Error al exportar: {exc}")

    def import_products(self, app_reference):
        file_path = filedialog.askopenfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Seleccionar archivo CSV de productos",
        )
        if not file_path:
            return

        try:
            product_list = []
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError("El archivo no contiene encabezados.")

                field_map = {str(name or "").strip().lower(): name for name in reader.fieldnames}
                required = {"nombre", "descripcion", "precio", "stock"}
                if not required.issubset(field_map):
                    raise ValueError("El CSV debe incluir las columnas nombre, descripcion, precio y stock.")

                for row in reader:
                    nombre = str(row.get(field_map["nombre"], "") or "").strip()
                    if not nombre:
                        continue

                    descripcion = str(row.get(field_map["descripcion"], "") or "").strip()
                    precio = normalize_hnl_amount(parse_hnl(row.get(field_map["precio"], "")))
                    stock = int(row.get(field_map["stock"], 0) or 0)
                    proveedor_raw = row.get(field_map.get("proveedor_id", ""), 1) if "proveedor_id" in field_map else 1
                    codigo_producto = (
                        str(row.get(field_map.get("codigo_producto", ""), "") or "").strip()
                        if "codigo_producto" in field_map
                        else ""
                    )

                    product_list.append(
                        (
                            nombre,
                            descripcion,
                            precio,
                            stock,
                            int(proveedor_raw or 1),
                            codigo_producto,
                        )
                    )

            if product_list:
                self.show_import_preview(product_list, app_reference)
            else:
                messagebox.showwarning("Importar", "No se encontraron productos válidos en el archivo.")
        except Exception as exc:
            messagebox.showerror(
                "Error de importación",
                "Error al leer el archivo.\n\n"
                "Asegúrese de que el formato sea CSV y que precio/stock sean números válidos.\n\n"
                f"Error: {exc}",
            )

    def show_import_preview(self, product_list, app_reference):
        parent = app_reference.winfo_toplevel() if hasattr(app_reference, "winfo_toplevel") else None
        preview_window = Toplevel(parent)
        preview_window.title("Vista previa de importación")
        preview_window.geometry("800x500")
        preview_window.transient(parent)
        if parent:
            center_window(preview_window, 800, 500, parent=parent)

        ttk.Label(
            preview_window,
            text=f"Productos a importar: {len(product_list)}",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        tree = ttk.Treeview(
            preview_window,
            columns=("Nombre", "Precio", "Stock", "Proveedor", "Codigo"),
            show="headings",
            height=15,
        )
        tree.heading("Nombre", text="Nombre")
        tree.heading("Precio", text="Precio")
        tree.heading("Stock", text="Stock")
        tree.heading("Proveedor", text="Proveedor ID")
        tree.heading("Codigo", text="Codigo")
        tree.column("Nombre", width=300)
        tree.column("Precio", width=110, anchor="e")
        tree.column("Stock", width=100, anchor="center")
        tree.column("Proveedor", width=120, anchor="center")
        tree.column("Codigo", width=140, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        for i, (nombre, desc, precio, stock, prov_id, codigo_producto) in enumerate(product_list):
            tree.insert(
                "",
                "end",
                iid=i,
                values=(nombre, format_hnl(precio), stock, prov_id, codigo_producto),
                tags=(nombre, desc, precio, stock, prov_id, codigo_producto),
            )

        def edit_selected():
            selected = tree.focus()
            if not selected:
                messagebox.showwarning("Editar", "Seleccione un producto primero.")
                return

            data = tree.item(selected, "tags")
            edit_win = Toplevel(preview_window)
            edit_win.title("Editar producto")
            edit_win.geometry("460x320")
            edit_win.transient(preview_window)
            center_window(edit_win, 460, 320, parent=preview_window)

            vars_list = [tk.StringVar(value=str(x)) for x in data]
            fields = ["Nombre", "Descripción", "Precio", "Stock", "Proveedor ID", "Codigo producto"]
            for i, field in enumerate(fields):
                ttk.Label(edit_win, text=f"{field}:").grid(row=i, column=0, padx=10, pady=6, sticky="w")
                ttk.Entry(edit_win, textvariable=vars_list[i], width=32).grid(row=i, column=1, padx=10, pady=6)

            def save_changes():
                try:
                    new_data = (
                        vars_list[0].get(),
                        vars_list[1].get(),
                        normalize_hnl_amount(parse_hnl(vars_list[2].get())),
                        int(vars_list[3].get()),
                        int(vars_list[4].get()),
                        vars_list[5].get().strip(),
                    )
                    tree.item(selected, tags=new_data)
                    tree.item(
                        selected,
                        values=(new_data[0], format_hnl(new_data[2]), new_data[3], new_data[4], new_data[5]),
                    )
                    edit_win.destroy()
                except ValueError:
                    messagebox.showerror("Error", "Precio HNL, stock y proveedor deben ser numeros.")

            ttk.Button(edit_win, text="Guardar", command=save_changes).grid(
                row=len(fields), column=0, columnspan=2, pady=14
            )

        def confirm_import():
            final_products = [tree.item(item, "tags") for item in tree.get_children()]
            if not final_products:
                messagebox.showwarning("Importar", "No hay productos para importar.")
                return

            try:
                imported = self.bulk_import_products_use_case.execute(final_products)
                messagebox.showinfo("Éxito", f"{imported} productos importados.")
                preview_window.destroy()
                if hasattr(app_reference, "refresh_products"):
                    app_reference.refresh_products()
            except (ValueError, ProductRepositoryError) as exc:
                messagebox.showerror("Error", f"Error al guardar: {exc}")

        btn_frame = ttk.Frame(preview_window)
        btn_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text="Editar seleccionado", command=edit_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=preview_window.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Confirmar importación", command=confirm_import).pack(side="right", padx=5)
