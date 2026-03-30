"""
frames/suppliers.py
Gestión de proveedores con CRUD.
"""

import tkinter as tk
from tkinter import messagebox, ttk


class SupplierFrame(ttk.Frame):
    """Frame para gestión de proveedores."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.db = app.db

        self.sup_id = tk.StringVar(value="")
        self.nombre = tk.StringVar()
        self.contacto = tk.StringVar()
        self.telefono = tk.StringVar()

        self._build_ui()
        self.load_suppliers()

    def _build_ui(self):
        self.columnconfigure(0, weight=7)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Gestión de proveedores", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self.list_frame = ttk.LabelFrame(self, text="Listado de proveedores", style="Card.TLabelframe")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.rowconfigure(0, weight=1)

        self.form_frame = ttk.LabelFrame(self, text="Formulario de proveedor", style="Card.TLabelframe")
        self.form_frame.grid(row=1, column=1, sticky="nsew")
        self.form_frame.columnconfigure(1, weight=1)

        self._create_supplier_list()
        self._create_supplier_form()

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

    def _create_supplier_list(self):
        self.tree = ttk.Treeview(
            self.list_frame,
            columns=("ID", "Nombre", "Contacto", "Teléfono"),
            show="headings",
            height=15,
        )
        self.tree.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        for col, width, anchor in (
            ("ID", 60, "center"),
            ("Nombre", 260, "w"),
            ("Contacto", 220, "w"),
            ("Teléfono", 140, "center"),
        ):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)

        y_scroll = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self.select_supplier)

        btn_frame = ttk.Frame(self.list_frame, style="Surface.TFrame")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        ttk.Button(btn_frame, text="Nuevo proveedor", style="Secondary.TButton", command=self.reset_form).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Eliminar", style="Danger.TButton", command=self.delete_supplier).pack(
            side="left", padx=6
        )
        ttk.Button(
            btn_frame,
            text="Exportar CSV",
            style="Primary.TButton",
            command=lambda: self.app.file_manager.export_data("Proveedores"),
        ).pack(side="right")

    def _create_supplier_form(self):
        fields = [
            ("Nombre empresa:", self.nombre),
            ("Persona contacto:", self.contacto),
            ("Teléfono:", self.telefono),
        ]

        row = 0
        for label_text, var in fields:
            ttk.Label(self.form_frame, text=label_text, style="FormLabel.TLabel").grid(
                row=row, column=0, sticky="w", padx=4, pady=8
            )
            ttk.Entry(self.form_frame, textvariable=var).grid(
                row=row, column=1, sticky="ew", padx=4, pady=8
            )
            row += 1

        ttk.Button(
            self.form_frame,
            text="Guardar proveedor",
            style="Primary.TButton",
            command=self.save_supplier,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(14, 4))

    def load_suppliers(self):
        self.tree.delete(*self.tree.get_children())
        suppliers = self.db.fetch("SELECT id, nombre, contacto, telefono FROM Proveedores ORDER BY id DESC")
        for sup in suppliers:
            self.tree.insert("", "end", values=sup)

    def select_supplier(self, _event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        values = self.tree.item(selected_item, "values")
        self.sup_id.set(values[0])
        self.nombre.set(values[1])
        self.contacto.set(values[2])
        self.telefono.set(values[3])

    def reset_form(self):
        self.sup_id.set("")
        self.nombre.set("")
        self.contacto.set("")
        self.telefono.set("")

    def save_supplier(self):
        nombre = self.nombre.get().strip()
        contacto = self.contacto.get().strip()
        telefono = self.telefono.get().strip()

        if not nombre:
            self._show_error("Error", "El nombre es obligatorio.")
            return

        if self.sup_id.get():
            self.db.execute(
                "UPDATE Proveedores SET nombre=?, contacto=?, telefono=? WHERE id=?",
                (nombre, contacto, telefono, self.sup_id.get()),
            )
            self._show_info("Éxito", "Proveedor actualizado.")
        else:
            self.db.execute(
                "INSERT INTO Proveedores (nombre, contacto, telefono) VALUES (?, ?, ?)",
                (nombre, contacto, telefono),
            )
            self._show_info("Éxito", "Proveedor agregado.")

        self.load_suppliers()
        self.reset_form()

    def delete_supplier(self):
        selected_item = self.tree.focus()
        if not selected_item:
            self._show_warning("Advertencia", "Seleccione un proveedor primero.")
            return

        sup_id = self.tree.item(selected_item, "values")[0]
        if self._ask_yes_no("Confirmar", f"¿Eliminar el proveedor ID {sup_id}?"):
            self.db.execute("DELETE FROM Proveedores WHERE id = ?", (sup_id,))
            self._show_info("Éxito", "Proveedor eliminado.")
            self.load_suppliers()
            self.reset_form()
