"""
frames/taxonomy.py
Gestion de categorias y marcas del catalogo.
"""

# Contexto del archivo:
# Esta pantalla conecta la taxonomia nueva del catalogo con la UI legacy.
# Administra categorias y marcas desde configuracion y sirve como soporte para
# que productos pueda evolucionar hacia un catalogo mas estructurado.

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk


class _TaxonomyCrudPanel(ttk.Frame):
    """Panel reutilizable para CRUD de tablas catalogo simples."""

    def __init__(self, parent, app, *, title, table_name, singular_label, relation_column):
        super().__init__(parent, padding=12, style="App.TFrame")
        self.app = app
        self.db = app.db
        self.title = title
        self.table_name = table_name
        self.singular_label = singular_label
        self.relation_column = relation_column

        self.record_id = tk.StringVar(value="")
        self.name_var = tk.StringVar()
        self.search_var = tk.StringVar()

        self._build_ui()
        self.load_records()

    def _build_ui(self):
        self.columnconfigure(0, weight=5)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(self, text=f"Listado de {self.title.lower()}", style="Card.TLabelframe")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)

        form_frame = ttk.LabelFrame(self, text=f"Formulario de {self.singular_label.lower()}", style="Card.TLabelframe")
        form_frame.grid(row=0, column=1, sticky="nsew")
        form_frame.columnconfigure(1, weight=1)

        search_frame = ttk.Frame(list_frame, style="Surface.TFrame")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Buscar:", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.bind("<KeyRelease>", self.filter_records)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("Nombre", "Descripcion", "Productos"),
            show="headings",
            height=15,
        )
        self.tree.grid(row=1, column=0, sticky="nsew")
        for col, width, anchor in (
            ("Nombre", 220, "w"),
            ("Descripcion", 340, "w"),
            ("Productos", 90, "center"),
        ):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)

        y_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        y_scroll.grid(row=1, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self.select_record)

        actions = ttk.Frame(list_frame, style="Surface.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text=f"Nueva {self.singular_label.lower()}", style="Secondary.TButton", command=self.reset_form).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Eliminar", style="Danger.TButton", command=self.delete_record).pack(side="left")

        ttk.Label(
            form_frame,
            text=f"Administre {self.title.lower()} sin exponer identificadores internos.",
            style="Muted.TLabel",
            wraplength=320,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(form_frame, text="Nombre:", style="FormLabel.TLabel").grid(
            row=1, column=0, sticky="w", padx=4, pady=7
        )
        ttk.Entry(form_frame, textvariable=self.name_var).grid(
            row=1, column=1, sticky="ew", padx=4, pady=7
        )

        ttk.Label(form_frame, text="Descripcion:", style="FormLabel.TLabel").grid(
            row=2, column=0, sticky="nw", padx=4, pady=7
        )
        self.description_text = tk.Text(form_frame, height=7, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.description_text.grid(row=2, column=1, sticky="ew", padx=4, pady=7)

        self.status_var = tk.StringVar(value="")
        ttk.Label(form_frame, textvariable=self.status_var, style="Muted.TLabel", wraplength=320).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 10)
        )

        ttk.Button(
            form_frame,
            text=f"Guardar {self.singular_label.lower()}",
            style="Primary.TButton",
            command=self.save_record,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))

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

    def _fetch_rows(self):
        return self.db.fetch(
            f"""
            SELECT ref.id, ref.nombre, COALESCE(ref.descripcion, ''), COUNT(prod.id) AS productos_asociados
            FROM {self.table_name} ref
            LEFT JOIN Productos prod
                ON prod.{self.relation_column} = ref.id
            GROUP BY ref.id, ref.nombre, ref.descripcion
            ORDER BY ref.nombre COLLATE NOCASE
            """
        )

    def _render_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        for record_id, name, description, related_count in rows:
            preview = str(description or "").strip()
            if len(preview) > 80:
                preview = f"{preview[:77].rstrip()}..."
            self.tree.insert(
                "",
                "end",
                iid=str(record_id),
                values=(name, preview or "Sin descripcion", related_count),
            )

    def load_records(self):
        self._render_rows(self._fetch_rows())

    def filter_records(self, _event=None):
        search_term = self.search_var.get().strip().lower()
        if not search_term:
            self.load_records()
            return

        filtered = []
        for row in self._fetch_rows():
            haystack = f"{row[1]} {row[2]}".lower()
            if search_term in haystack:
                filtered.append(row)
        self._render_rows(filtered)

    def select_record(self, _event=None):
        selected_item = self.tree.focus()
        if not selected_item:
            return

        row = self.db.fetch(
            f"SELECT nombre, COALESCE(descripcion, '') FROM {self.table_name} WHERE id = ?",
            (selected_item,),
        )
        if not row:
            return

        self.record_id.set(selected_item)
        self.name_var.set(row[0][0])
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", row[0][1])

        related_count = self.tree.item(selected_item, "values")[2]
        self.status_var.set(f"Productos vinculados: {related_count}")

    def reset_form(self):
        self.record_id.set("")
        self.name_var.set("")
        self.status_var.set("")
        self.description_text.delete("1.0", tk.END)
        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def save_record(self):
        name = self.name_var.get().strip()
        description = self.description_text.get("1.0", tk.END).strip() or None

        if not name:
            self._show_error("Error", f"El nombre de la {self.singular_label.lower()} es obligatorio.")
            return

        try:
            if self.record_id.get():
                self.db.execute(
                    f"UPDATE {self.table_name} SET nombre = ?, descripcion = ? WHERE id = ?",
                    (name, description, self.record_id.get()),
                )
                if self.db.last_error:
                    raise self.db.last_error
                self._show_info("Exito", f"{self.singular_label} actualizada correctamente.")
            else:
                self.db.execute(
                    f"INSERT INTO {self.table_name} (nombre, descripcion) VALUES (?, ?)",
                    (name, description),
                )
                if self.db.last_error:
                    raise self.db.last_error
                self._show_info("Exito", f"{self.singular_label} agregada correctamente.")
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed" in str(exc):
                self._show_error("Duplicado", f"Ya existe una {self.singular_label.lower()} con ese nombre.")
            else:
                self._show_error("Error", f"No se pudo guardar la {self.singular_label.lower()}: {exc}")
            return

        self.load_records()
        self.reset_form()

    def delete_record(self):
        selected_item = self.tree.focus()
        if not selected_item:
            self._show_warning("Advertencia", f"Seleccione una {self.singular_label.lower()} primero.")
            return

        name, _description, related_count = self.tree.item(selected_item, "values")
        if int(related_count or 0) > 0:
            self._show_warning(
                "En uso",
                f"No puede eliminar \"{name}\" porque ya esta asociada a {related_count} producto(s).",
            )
            return

        if not self._ask_yes_no("Confirmar", f"Eliminar la {self.singular_label.lower()} \"{name}\"?"):
            return

        result = self.db.execute(
            f"DELETE FROM {self.table_name} WHERE id = ?",
            (selected_item,),
        )
        if result is None and self.db.last_error:
            self._show_error("Error", f"No se pudo eliminar la {self.singular_label.lower()}: {self.db.last_error}")
            return

        self._show_info("Exito", f"{self.singular_label} eliminada correctamente.")
        self.load_records()
        self.reset_form()


class CatalogTaxonomyFrame(ttk.Frame):
    """Modulo de gestion para categorias y marcas del catalogo."""

    def __init__(self, parent, app):
        super().__init__(parent, style="App.TFrame")
        self.app = app

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew")

        categories_tab = _TaxonomyCrudPanel(
            notebook,
            app,
            title="Categorias",
            table_name="Categorias",
            singular_label="Categoria",
            relation_column="categoria_id",
        )
        brands_tab = _TaxonomyCrudPanel(
            notebook,
            app,
            title="Marcas",
            table_name="Marcas",
            singular_label="Marca",
            relation_column="marca_id",
        )

        notebook.add(categories_tab, text="Categorias")
        notebook.add(brands_tab, text="Marcas")
