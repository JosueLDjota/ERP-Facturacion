"""
file_manager.py
Gestor de importación y exportación de datos CSV.
"""

import csv
import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox, ttk

def center_window(window, width, height, parent=None):
    window.update_idletasks()
    base = parent if parent is not None else window
    x = base.winfo_rootx() + max(0, (base.winfo_width() - width) // 2)
    y = base.winfo_rooty() + max(0, (base.winfo_height() - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


class FileManager:
    """Maneja la importación y exportación de datos CSV."""

    TABLE_MAP = {
        "Productos": "Productos.csv",
        "Proveedores": "Proveedores.csv",
        "Usuarios": "Usuarios.csv",
        "Descuentos": "Descuentos.csv",
    }

    def __init__(self, db_manager):
        self.db = db_manager

    def get_data_from_db(self, table_name):
        """Obtiene datos de la DB para exportar."""
        if table_name == "Productos":
            return self.db.fetch("SELECT id, nombre, descripcion, precio, stock, proveedor_id FROM Productos")
        if table_name == "Proveedores":
            return self.db.fetch("SELECT id, nombre, contacto, telefono FROM Proveedores")
        if table_name == "Usuarios":
            return self.db.fetch("SELECT id, nombre, usuario, rol FROM Usuarios")
        if table_name == "Descuentos":
            return self.db.fetch("SELECT id, nombre, tipo, porcentaje FROM Descuentos")
        return []

    def export_data(self, table_name):
        """Exporta datos a un archivo CSV."""
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
                    "Productos": ["id", "nombre", "descripcion", "precio", "stock", "proveedor_id"],
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
        """Importa productos desde un archivo CSV."""
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
                reader = csv.reader(f)
                next(reader, None)  # Header
                for row in reader:
                    if len(row) >= 5:
                        product_list.append(
                            (
                                row[1],  # nombre
                                row[2],  # descripcion
                                float(row[3]),  # precio
                                int(row[4]),  # stock
                                int(row[5]) if len(row) > 5 else 1,  # proveedor_id
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
        """Muestra vista previa de productos a importar."""
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
            columns=("Nombre", "Precio", "Stock", "Proveedor"),
            show="headings",
            height=15,
        )
        tree.heading("Nombre", text="Nombre")
        tree.heading("Precio", text="Precio")
        tree.heading("Stock", text="Stock")
        tree.heading("Proveedor", text="Proveedor ID")
        tree.column("Nombre", width=300)
        tree.column("Precio", width=110, anchor="e")
        tree.column("Stock", width=100, anchor="center")
        tree.column("Proveedor", width=120, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        for i, (nombre, desc, precio, stock, prov_id) in enumerate(product_list):
            tree.insert(
                "",
                "end",
                iid=i,
                values=(nombre, f"${precio:.2f}", stock, prov_id),
                tags=(nombre, desc, precio, stock, prov_id),
            )

        def edit_selected():
            selected = tree.focus()
            if not selected:
                messagebox.showwarning("Editar", "Seleccione un producto primero.")
                return

            data = tree.item(selected, "tags")
            edit_win = Toplevel(preview_window)
            edit_win.title("Editar producto")
            edit_win.geometry("420x280")
            edit_win.transient(preview_window)
            center_window(edit_win, 420, 280, parent=preview_window)

            vars_list = [tk.StringVar(value=str(x)) for x in data]
            fields = ["Nombre", "Descripción", "Precio", "Stock", "Proveedor ID"]
            for i, field in enumerate(fields):
                ttk.Label(edit_win, text=f"{field}:").grid(row=i, column=0, padx=10, pady=6, sticky="w")
                ttk.Entry(edit_win, textvariable=vars_list[i], width=32).grid(row=i, column=1, padx=10, pady=6)

            def save_changes():
                try:
                    new_data = (
                        vars_list[0].get(),
                        vars_list[1].get(),
                        float(vars_list[2].get()),
                        int(vars_list[3].get()),
                        int(vars_list[4].get()),
                    )
                    tree.item(selected, tags=new_data)
                    tree.item(selected, values=(new_data[0], f"${new_data[2]:.2f}", new_data[3], new_data[4]))
                    edit_win.destroy()
                except ValueError:
                    messagebox.showerror("Error", "Precio, stock y proveedor deben ser números.")

            ttk.Button(edit_win, text="Guardar", command=save_changes).grid(
                row=len(fields), column=0, columnspan=2, pady=14
            )

        def confirm_import():
            final_products = [tree.item(item, "tags") for item in tree.get_children()]
            if not final_products:
                messagebox.showwarning("Importar", "No hay productos para importar.")
                return

            query = """
                INSERT INTO Productos (nombre, descripcion, precio, stock, proveedor_id)
                VALUES (?, ?, ?, ?, ?)
            """
            try:
                self.db.cursor.executemany(query, final_products)
                self.db.conn.commit()
                messagebox.showinfo("Éxito", f"{len(final_products)} productos importados.")
                preview_window.destroy()
                if hasattr(app_reference, "refresh_products"):
                    app_reference.refresh_products()
            except Exception as exc:
                messagebox.showerror("Error", f"Error al guardar: {exc}")

        btn_frame = ttk.Frame(preview_window)
        btn_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text="Editar seleccionado", command=edit_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=preview_window.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Confirmar importación", command=confirm_import).pack(side="right", padx=5)
