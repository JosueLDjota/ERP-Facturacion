"""
frames/clients.py
Módulo de gestión de clientes.
"""

# Contexto del archivo:
# Aqui vive la interfaz legacy de clientes: listado, formulario, filtros,
# acciones CRUD y utilidades de busqueda. Sigue siendo un modulo importante
# porque alimenta ventas, historial y relaciones comerciales en la base.

from datetime import datetime
import csv
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .ui import create_modal


class ClientsFrame(ttk.Frame):
    """Frame para gestión completa de clientes."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.db = app.db

        self.nombre_var = tk.StringVar()
        self.apellido_var = tk.StringVar()
        self.dni_var = tk.StringVar()
        self.telefono_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.activo_var = tk.BooleanVar(value=True)
        self.mayorista_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="todos")
        self.cliente_id_seleccionado = None

        self._build_ui()
        self.load_clients()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)


        main = ttk.Frame(self, style="App.TFrame")
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=5)
        main.columnconfigure(1, weight=7)
        main.rowconfigure(0, weight=1)

        self._build_form_card(main)
        self._build_list_card(main)

    def _build_form_card(self, parent):
        form_card = ttk.LabelFrame(parent, text="Información del cliente", style="Card.TLabelframe")
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        form_card.columnconfigure(1, weight=1)

        fields = [
            ("Nombre *", self.nombre_var),
            ("Apellido *", self.apellido_var),
            ("DNI/Identidad", self.dni_var),
            ("Teléfono", self.telefono_var),
            ("Email", self.email_var),
        ]

        row = 0
        for label, var in fields:
            ttk.Label(form_card, text=f"{label}:", style="FormLabel.TLabel").grid(
                row=row, column=0, sticky="w", padx=4, pady=6
            )
            entry = ttk.Entry(form_card, textvariable=var)
            entry.grid(
                row=row, column=1, columnspan=2, sticky="ew", padx=4, pady=6
            )
            if row == 0:
                self.nombre_entry = entry
            row += 1

        ttk.Label(form_card, text="Dirección:", style="FormLabel.TLabel").grid(
            row=row, column=0, sticky="nw", padx=4, pady=6
        )
        self.direccion_text = tk.Text(form_card, height=4, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.direccion_text.grid(row=row, column=1, columnspan=2, sticky="ew", padx=4, pady=6)
        row += 1

        ttk.Checkbutton(form_card, text="Cliente activo", variable=self.activo_var).grid(
            row=row, column=1, sticky="w", padx=4, pady=(8, 4)
        )
        ttk.Checkbutton(form_card, text="Cliente mayorista", variable=self.mayorista_var).grid(
            row=row, column=2, sticky="w", padx=4, pady=(8, 4)
        )
        row += 1

        actions = ttk.Frame(form_card, style="Surface.TFrame")
        actions.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(14, 6))
        actions.columnconfigure((0, 1, 2, 3), weight=1)

        ttk.Button(actions, text="Guardar", style="Primary.TButton", command=self.save_client).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ttk.Button(actions, text="Nuevo", style="Secondary.TButton", command=self.start_new_client).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ttk.Button(actions, text="Eliminar", style="Danger.TButton", command=self.delete_client).grid(
            row=0, column=2, sticky="ew", padx=4
        )
        ttk.Button(actions, text="Limpiar", style="Secondary.TButton", command=self.clear_form).grid(
            row=0, column=3, sticky="ew", padx=4
        )

    def _build_list_card(self, parent):
        list_card = ttk.LabelFrame(parent, text="Listado de clientes", style="Card.TLabelframe")
        list_card.grid(row=0, column=1, sticky="nsew")
        list_card.columnconfigure(0, weight=1)
        list_card.rowconfigure(2, weight=1)

        search_frame = ttk.Frame(list_card, style="Surface.TFrame")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)

        self.search_var.trace_add("write", lambda *_args: self.search_clients())
        ttk.Label(search_frame, text="Buscar:", style="FormLabel.TLabel").grid(row=0, column=0, padx=(0, 6), sticky="w")
        ttk.Entry(search_frame, textvariable=self.search_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(search_frame, text="Estado:", style="FormLabel.TLabel").grid(row=0, column=2, padx=(10, 6), sticky="e")
        filter_combo = ttk.Combobox(
            search_frame,
            textvariable=self.filter_var,
            values=["todos", "activos", "inactivos"],
            state="readonly",
            width=12,
        )
        filter_combo.grid(row=0, column=3, sticky="e")
        filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_clients())

        columns = ("Nombre", "Apellido", "DNI", "Teléfono", "Email", "Estado", "Mayorista")
        self.tree = ttk.Treeview(list_card, columns=columns, show="headings", height=14)
        self.tree.grid(row=2, column=0, sticky="nsew")

        for col, width, anchor in (
            ("Nombre", 130, "w"),
            ("Apellido", 130, "w"),
            ("DNI", 140, "center"),
            ("Teléfono", 140, "center"),
            ("Email", 180, "w"),
            ("Estado", 90, "center"),
            ("Mayorista", 95, "center"),
        ):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)

        self.tree.tag_configure("activo", foreground="black")
        self.tree.tag_configure("inactivo", foreground="#6B7280")

        y_scroll = ttk.Scrollbar(list_card, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(list_card, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.grid(row=2, column=1, sticky="ns")
        x_scroll.grid(row=3, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self.on_client_select)

        footer = ttk.Frame(list_card, style="Surface.TFrame")
        footer.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(footer, text="Exportar CSV", style="Secondary.TButton", command=self.export_to_csv).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(footer, text="Importar CSV", style="Secondary.TButton", command=self.import_from_csv).pack(
            side="left", padx=6
        )
        ttk.Button(footer, text="Estadísticas", style="Primary.TButton", command=self.show_statistics).pack(
            side="right"
        )

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

    def _render_clients(self, rows):
        self.tree.delete(*self.tree.get_children())
        for cliente in rows:
            (
                id_cliente,
                nombre,
                apellido,
                dni,
                telefono,
                email,
                _direccion,
                _fecha_registro,
                activo,
                mayorista,
            ) = cliente
            estado = "Activo" if activo else "Inactivo"
            tag = "activo" if activo else "inactivo"
            self.tree.insert(
                "",
                tk.END,
                iid=str(id_cliente),
                values=(
                    nombre,
                    apellido,
                    dni or "N/A",
                    telefono or "N/A",
                    email or "N/A",
                    estado,
                    "Sí" if mayorista else "No",
                ),
                tags=(tag,),
            )

    def load_clients(self):
        """Carga la lista de clientes desde la base de datos."""
        filter_estado = self.filter_var.get()
        if filter_estado == "activos":
            query = """
                SELECT id, nombre, apellido, dni, telefono, email, direccion,
                       fecha_registro, activo, COALESCE(mayorista, 0)
                FROM Clientes
                WHERE activo = 1
                ORDER BY apellido, nombre
            """
        elif filter_estado == "inactivos":
            query = """
                SELECT id, nombre, apellido, dni, telefono, email, direccion,
                       fecha_registro, activo, COALESCE(mayorista, 0)
                FROM Clientes
                WHERE activo = 0
                ORDER BY apellido, nombre
            """
        else:
            query = """
                SELECT id, nombre, apellido, dni, telefono, email, direccion,
                       fecha_registro, activo, COALESCE(mayorista, 0)
                FROM Clientes
                ORDER BY apellido, nombre
            """

        self._render_clients(self.db.fetch(query))

    def search_clients(self):
        """Busca clientes en tiempo real."""
        search_term = self.search_var.get().strip().lower()
        if not search_term:
            self.load_clients()
            return

        query = """
            SELECT id, nombre, apellido, dni, telefono, email, direccion,
                   fecha_registro, activo, COALESCE(mayorista, 0)
            FROM Clientes
            WHERE LOWER(nombre) LIKE ?
               OR LOWER(apellido) LIKE ?
               OR LOWER(dni) LIKE ?
               OR LOWER(telefono) LIKE ?
               OR LOWER(email) LIKE ?
            ORDER BY apellido, nombre
        """
        pattern = f"%{search_term}%"
        self._render_clients(self.db.fetch(query, (pattern, pattern, pattern, pattern, pattern)))

    def on_client_select(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        if selection[0]:
            self.cliente_id_seleccionado = selection[0]
            self.load_client_details(self.cliente_id_seleccionado)

    def load_client_details(self, cliente_id):
        cliente = self.db.fetch("SELECT * FROM Clientes WHERE id = ?", (cliente_id,))
        if not cliente:
            return

        (
            _id_cliente,
            nombre,
            apellido,
            dni,
            telefono,
            email,
            direccion,
            _fecha_registro,
            activo,
            mayorista,
        ) = cliente[0]

        self.nombre_var.set(nombre)
        self.apellido_var.set(apellido)
        self.dni_var.set(dni or "")
        self.telefono_var.set(telefono or "")
        self.email_var.set(email or "")
        self.direccion_text.delete("1.0", tk.END)
        self.direccion_text.insert("1.0", direccion or "")
        self.activo_var.set(bool(activo))
        self.mayorista_var.set(bool(mayorista))

    def validate_form(self):
        if not self.nombre_var.get().strip():
            self._show_error("Error", "El nombre es obligatorio.")
            return False
        if not self.apellido_var.get().strip():
            self._show_error("Error", "El apellido es obligatorio.")
            return False

        dni = self.dni_var.get().strip()
        if dni and not re.match(r"^[0-9]{13}$", dni):
            self._show_error("Error", "El DNI debe tener 13 dígitos.")
            return False

        email = self.email_var.get().strip()
        if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            self._show_error("Error", "Formato de email inválido.")
            return False
        return True

    def save_client(self):
        """Guarda un nuevo cliente o actualiza uno existente."""
        if not self.validate_form():
            return

        nombre = self.nombre_var.get().strip()
        apellido = self.apellido_var.get().strip()
        dni = self.dni_var.get().strip() or None
        telefono = self.telefono_var.get().strip() or None
        email = self.email_var.get().strip() or None
        direccion = self.direccion_text.get("1.0", tk.END).strip() or None
        activo = 1 if self.activo_var.get() else 0
        mayorista = 1 if self.mayorista_var.get() else 0

        try:
            if self.cliente_id_seleccionado:
                query = """
                    UPDATE Clientes
                    SET nombre=?, apellido=?, dni=?, telefono=?, email=?, direccion=?, activo=?, mayorista=?
                    WHERE id=?
                """
                self.db.execute(
                    query,
                    (nombre, apellido, dni, telefono, email, direccion, activo, mayorista, self.cliente_id_seleccionado),
                )
                self._show_info("Éxito", "Cliente actualizado correctamente.")
            else:
                fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                query = """
                    INSERT INTO Clientes (nombre, apellido, dni, telefono, email, direccion, fecha_registro, activo, mayorista)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.db.execute(query, (nombre, apellido, dni, telefono, email, direccion, fecha_registro, activo, mayorista))
                self._show_info("Éxito", "Cliente registrado correctamente.")

            self.clear_form()
            self.load_clients()
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                self._show_error("Error", "El DNI ya está registrado para otro cliente.")
            else:
                self._show_error("Error", f"Error al guardar cliente: {exc}")

    def start_new_client(self):
        self.clear_form()
        self.tree.focus("")
        self.nombre_entry.focus_set()

    def delete_client(self):
        if not self.cliente_id_seleccionado:
            self._show_warning("Advertencia", "Seleccione un cliente para eliminar.")
            return

        ventas = self.db.fetch("SELECT COUNT(*) FROM Ventas WHERE id_cliente = ?", (self.cliente_id_seleccionado,))
        tiene_ventas = ventas[0][0] > 0 if ventas else False

        if tiene_ventas:
            respuesta = self._ask_yes_no(
                "Cliente con ventas",
                "Este cliente tiene ventas registradas.\n¿Desea desactivarlo en lugar de eliminarlo?\n\nSí = Desactivar\nNo = Eliminar permanentemente",
            )
            if respuesta:
                self.db.execute("UPDATE Clientes SET activo = 0 WHERE id = ?", (self.cliente_id_seleccionado,))
                self._show_info("Éxito", "Cliente desactivado correctamente.")
            else:
                if self._ask_yes_no(
                    "Confirmación",
                    "Advertencia: se eliminarán también las ventas asociadas.\n¿Continuar?",
                ):
                    self.db.execute(
                        "DELETE FROM DetalleVenta WHERE venta_id IN (SELECT id FROM Ventas WHERE id_cliente = ?)",
                        (self.cliente_id_seleccionado,),
                    )
                    self.db.execute("DELETE FROM Ventas WHERE id_cliente = ?", (self.cliente_id_seleccionado,))
                    self.db.execute("DELETE FROM Clientes WHERE id = ?", (self.cliente_id_seleccionado,))
                    self._show_info("Éxito", "Cliente y ventas asociadas eliminados.")
        else:
            if self._ask_yes_no("Confirmación", "¿Está seguro de eliminar este cliente?"):
                self.db.execute("DELETE FROM Clientes WHERE id = ?", (self.cliente_id_seleccionado,))
                self._show_info("Éxito", "Cliente eliminado correctamente.")

        self.clear_form()
        self.load_clients()

    def clear_form(self):
        self.nombre_var.set("")
        self.apellido_var.set("")
        self.dni_var.set("")
        self.telefono_var.set("")
        self.email_var.set("")
        self.direccion_text.delete("1.0", tk.END)
        self.activo_var.set(True)
        self.mayorista_var.set(False)
        self.cliente_id_seleccionado = None
        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def export_to_csv(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Exportar clientes",
        )
        if not filename:
            return

        try:
            clientes = self.db.fetch("SELECT * FROM Clientes ORDER BY apellido, nombre")
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    ["ID", "Nombre", "Apellido", "DNI", "Teléfono", "Email", "Dirección", "Fecha Registro", "Activo", "Mayorista"]
                )
                writer.writerows(clientes)
            self._show_info("Éxito", f"Clientes exportados a:\n{filename}")
        except Exception as exc:
            self._show_error("Error", f"Error al exportar: {exc}")

    def import_from_csv(self):
        filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Importar clientes",
        )
        if not filename:
            return

        try:
            imported_count = 0
            skipped_count = 0
            with open(filename, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        if not row.get("Nombre") or not row.get("Apellido"):
                            skipped_count += 1
                            continue

                        fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        mayorista = 1 if row.get("Mayorista", "0") in ("1", "Sí", "Si", "si", "true", "True") else 0
                        self.db.execute(
                            """
                                INSERT INTO Clientes (nombre, apellido, dni, telefono, email, direccion, fecha_registro, activo, mayorista)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                row["Nombre"],
                                row["Apellido"],
                                row.get("DNI") or None,
                                row.get("Teléfono") or None,
                                row.get("Email") or None,
                                row.get("Dirección") or None,
                                fecha_registro,
                                1 if row.get("Activo", "1") == "1" else 0,
                                mayorista,
                            ),
                        )
                        imported_count += 1
                    except Exception as exc:
                        if "UNIQUE constraint failed" not in str(exc):
                            skipped_count += 1

            self.load_clients()
            self._show_info(
                "Importación completa",
                f"Clientes importados: {imported_count}\nRegistros omitidos: {skipped_count}",
            )
        except Exception as exc:
            self._show_error("Error", f"Error al importar: {exc}")

    def show_statistics(self):
        try:
            total = self.db.fetch("SELECT COUNT(*) FROM Clientes")[0][0]
            activos = self.db.fetch("SELECT COUNT(*) FROM Clientes WHERE activo = 1")[0][0]
            inactivos = total - activos
            con_ventas = self.db.fetch("SELECT COUNT(DISTINCT id_cliente) FROM Ventas WHERE id_cliente IS NOT NULL")[0][0]
            inicio_mes = datetime.now().strftime("%Y-%m-01")
            este_mes = self.db.fetch("SELECT COUNT(*) FROM Clientes WHERE fecha_registro >= ?", (inicio_mes,))[0][0]

            popup = create_modal(self._parent(), "Estadísticas de clientes", width=520, height=350)
            content = ttk.Frame(popup, padding=18, style="Surface.TFrame")
            content.pack(fill="both", expand=True)

            ttk.Label(content, text="Resumen de clientes", style="Subheader.TLabel").pack(anchor="w", pady=(0, 12))
            ttk.Label(content, text=f"Total de clientes: {total}", style="FormLabel.TLabel").pack(anchor="w", pady=3)
            ttk.Label(content, text=f"Clientes activos: {activos}", style="FormLabel.TLabel").pack(anchor="w", pady=3)
            ttk.Label(content, text=f"Clientes inactivos: {inactivos}", style="FormLabel.TLabel").pack(anchor="w", pady=3)
            ttk.Label(content, text=f"Clientes con ventas: {con_ventas}", style="FormLabel.TLabel").pack(anchor="w", pady=3)
            ttk.Label(content, text=f"Registrados este mes: {este_mes}", style="FormLabel.TLabel").pack(anchor="w", pady=3)

            actividad = (activos / total * 100) if total else 0
            compradores = (con_ventas / total * 100) if total else 0
            ttk.Label(content, text=f"Actividad: {actividad:.1f}%", style="Muted.TLabel").pack(anchor="w", pady=(12, 2))
            ttk.Label(content, text=f"Clientes compradores: {compradores:.1f}%", style="Muted.TLabel").pack(anchor="w", pady=2)

            ttk.Button(content, text="Cerrar", style="Primary.TButton", command=popup.destroy).pack(
                anchor="e", pady=(20, 0)
            )
        except Exception as exc:
            self._show_error("Error", f"Error al calcular estadísticas: {exc}")

