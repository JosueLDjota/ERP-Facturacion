"""
frames/config.py
Configuracion del sistema, descuentos y plantilla de recibos.
"""

import tempfile
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from erp.data.repositories.config_repository import ConfigRepository, RepositoryError
from receipt_builder import (
    build_receipt_html,
    build_receipt_preview_text,
    default_receipt_labels,
    load_receipt_labels,
)


class ConfigFrame(ttk.Frame):
    """Frame de configuracion del sistema."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=10, style="App.TFrame")
        self.app = app
        self.db = app.db
        self.repository = ConfigRepository(self.db)

        # Variables de descuentos
        self.disc_id = tk.StringVar(value="")
        self.disc_nombre = tk.StringVar()
        self.disc_porcentaje = tk.StringVar()
        self.disc_tipo = tk.StringVar(value="Docena")
        
        # Variables de empresa
        self.company_name_var = tk.StringVar()
        self.company_rtn_var = tk.StringVar()
        self.company_tel_var = tk.StringVar()
        self.company_email_var = tk.StringVar()
        self.company_logo_var = tk.StringVar()
        self.company_address_var = tk.StringVar()
        self.receipt_notes_var = tk.StringVar()
        
        # Variables de textos del recibo
        self.receipt_title_var = tk.StringVar()
        self.receipt_order_exempt_var = tk.StringVar()
        self.receipt_exempt_register_var = tk.StringVar()
        self.receipt_discounts_var = tk.StringVar()
        self.receipt_summary_title_var = tk.StringVar()
        self.receipt_copy_label_var = tk.StringVar()
        self.receipt_thanks_var = tk.StringVar()
        self.receipt_amount_label_var = tk.StringVar()
        self.receipt_change_label_var = tk.StringVar()
        self.receipt_observations_label_var = tk.StringVar()
        
        # Estado de edición
        self.full_template_edit_unlocked = False
        self._last_preview_path = None
        self._template_content = self.repository.get_receipt_template()
        
        if "<html" in self._template_content.lower():
            self._template_content = self.repository.default_receipt_template()

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
        self.notebook.add(disc_tab, text="Descuentos")
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
            columns=("ID", "Nombre", "Tipo", "Porcentaje"),
            show="headings",
            height=14,
        )
        
        for col, width, anchor in (
            ("ID", 60, "center"),
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

        discounts = self.repository.list_discounts()
        for disc in discounts:
            self.disc_tree.insert("", "end", values=(disc[0], disc[1], disc[2], f"{int(disc[3] * 100)}%"))

    def select_discount(self, _event):
        selected_item = self.disc_tree.focus()
        if not selected_item:
            return

        values = self.disc_tree.item(selected_item, "values")
        self.disc_id.set(values[0])
        self.disc_nombre.set(values[1])
        self.disc_tipo.set(values[2])
        self.disc_porcentaje.set(values[3].strip("%"))

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

        try:
            self.repository.save_discount(self.disc_id.get() or None, nombre, tipo, pct)
        except RepositoryError as exc:
            messagebox.showerror("Error", f"No se pudo guardar el descuento.\n\n{exc}", parent=self._parent())
            return

        messagebox.showinfo(
            "Exito",
            "Descuento actualizado." if self.disc_id.get() else "Descuento agregado.",
            parent=self._parent(),
        )

        self.load_discounts()
        self.reset_discount_form()

    def delete_discount(self):
        selected_item = self.disc_tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Seleccione un descuento primero.", parent=self._parent())
            return

        disc_id = self.disc_tree.item(selected_item, "values")[0]
        if messagebox.askyesno("Confirmar", f"Eliminar el descuento ID {disc_id}?", parent=self._parent()):
            try:
                self.repository.delete_discount(int(disc_id))
            except RepositoryError as exc:
                messagebox.showerror("Error", f"No se pudo eliminar el descuento.\n\n{exc}", parent=self._parent())
                return
            messagebox.showinfo("Exito", "Descuento eliminado.", parent=self._parent())
            self.load_discounts()
            self.reset_discount_form()

    def create_receipt_tab(self, parent):
        """Crea la pestaña de plantilla de recibo con editor visual y scrolls funcionales."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        self._load_receipt_settings()

        # Header
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Editor visual del recibo", style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Edita el recibo como lo verá el cliente. Ventas y Reimpresión usarán esta misma plantilla activa.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Body principal
        body = ttk.Frame(parent, style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # ========== PANEL DE EDICIÓN ==========
        editor_card = ttk.LabelFrame(body, text="Edición visual", style="Card.TLabelframe")
        editor_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        editor_card.columnconfigure(0, weight=1)
        editor_card.rowconfigure(1, weight=1)

        # Barra de estado
        status_bar = ttk.Frame(editor_card, style="Surface.TFrame")
        status_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        status_bar.columnconfigure(0, weight=1)

        self.template_lock_var = tk.StringVar(
            value="Modo protegido activo: la estructura, productos, cálculos e impuestos siguen bloqueados."
        )
        ttk.Label(status_bar, textvariable=self.template_lock_var, style="Muted.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.unlock_template_btn = ttk.Button(
            status_bar,
            text="Desbloquear edición total",
            style="Secondary.TButton",
            command=self.toggle_full_template_edit,
        )
        self.unlock_template_btn.grid(row=0, column=1, sticky="e")

        # Área de formularios con scroll
        form_canvas = tk.Canvas(editor_card, highlightthickness=0)
        form_canvas.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))
        
        form_scroll = ttk.Scrollbar(editor_card, orient="vertical", command=form_canvas.yview)
        form_scroll.grid(row=1, column=1, sticky="ns", pady=(4, 8))
        form_canvas.configure(yscrollcommand=form_scroll.set)
        
        form_area = ttk.Frame(form_canvas, style="App.TFrame")
        form_canvas.create_window((0, 0), window=form_area, anchor="nw", width=form_canvas.winfo_width())
        form_area.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.bind("<Configure>", lambda e: form_canvas.itemconfig(1, width=e.width))

        # Datos del negocio
        business_card = ttk.LabelFrame(form_area, text="Datos del negocio", style="Card.TLabelframe")
        business_card.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=4)
        business_card.columnconfigure(1, weight=1)

        business_fields = [
            ("Nombre negocio", self.company_name_var),
            ("RTN", self.company_rtn_var),
            ("Teléfono", self.company_tel_var),
            ("Email", self.company_email_var),
            ("Logo URL", self.company_logo_var),
        ]
        for row, (label_text, variable) in enumerate(business_fields):
            ttk.Label(business_card, text=label_text, style="FormLabel.TLabel").grid(
                row=row, column=0, sticky="w", padx=4, pady=6
            )
            ttk.Entry(business_card, textvariable=variable).grid(
                row=row, column=1, sticky="ew", padx=4, pady=6
            )

        ttk.Label(business_card, text="Dirección", style="FormLabel.TLabel").grid(
            row=len(business_fields), column=0, sticky="nw", padx=4, pady=6
        )
        self.company_address_text = tk.Text(business_card, height=4, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.company_address_text.grid(row=len(business_fields), column=1, sticky="ew", padx=4, pady=6)
        self.company_address_text.insert("1.0", self.db.get_config("empresa_direccion", "") or "")

        # Textos visibles
        texts_card = ttk.LabelFrame(form_area, text="Textos visibles del recibo", style="Card.TLabelframe")
        texts_card.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=4)
        texts_card.columnconfigure(1, weight=1)
        texts_card.columnconfigure(3, weight=1)

        visible_fields = [
            ("Título", self.receipt_title_var),
            ("Compra exenta", self.receipt_order_exempt_var),
            ("Registro exento", self.receipt_exempt_register_var),
            ("Descuentos", self.receipt_discounts_var),
            ("Resumen", self.receipt_summary_title_var),
            ("Monto recibido", self.receipt_amount_label_var),
            ("Vuelto", self.receipt_change_label_var),
            ("Observaciones", self.receipt_observations_label_var),
            ("Pie cliente", self.receipt_copy_label_var),
            ("Mensaje final", self.receipt_thanks_var),
        ]
        for index, (label_text, variable) in enumerate(visible_fields):
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(texts_card, text=label_text, style="FormLabel.TLabel").grid(
                row=row, column=col, sticky="w", padx=4, pady=6
            )
            ttk.Entry(texts_card, textvariable=variable).grid(
                row=row, column=col + 1, sticky="ew", padx=4, pady=6
            )

        # Observaciones fijas
        notes_card = ttk.LabelFrame(form_area, text="Observación fija del recibo", style="Card.TLabelframe")
        notes_card.grid(row=2, column=0, sticky="ew", pady=(0, 8), padx=4)
        notes_card.columnconfigure(0, weight=1)
        notes_card.rowconfigure(1, weight=1)
        ttk.Label(
            notes_card,
            text="Este texto se inserta en la línea de observaciones del recibo real.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 0))
        self.receipt_notes_text = tk.Text(notes_card, height=4, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.receipt_notes_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.receipt_notes_text.insert("1.0", self.db.get_config("recibo_observaciones", "") or "")

        # Modo avanzado
        self.advanced_card = ttk.LabelFrame(form_area, text="Edición total avanzada", style="Card.TLabelframe")
        self.advanced_card.grid(row=3, column=0, sticky="nsew", pady=(8, 0), padx=4)
        self.advanced_card.columnconfigure(0, weight=1)
        self.advanced_card.rowconfigure(1, weight=1)
        ttk.Label(
            self.advanced_card,
            text="Modo avanzado: edita la plantilla central en texto estructurado. Los marcadores {{...}} mantienen datos dinámicos.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
        
        # Text con scroll para modo avanzado
        advanced_text_frame = ttk.Frame(self.advanced_card)
        advanced_text_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        advanced_text_frame.columnconfigure(0, weight=1)
        advanced_text_frame.rowconfigure(0, weight=1)
        
        self.template_text = tk.Text(advanced_text_frame, height=12, font=("Consolas", 10), wrap=tk.NONE)
        self.template_text.grid(row=0, column=0, sticky="nsew")
        self.template_text.insert("1.0", self._template_content)
        self.template_text.bind("<KeyRelease>", self.on_template_text_changed)
        
        advanced_scroll_y = ttk.Scrollbar(advanced_text_frame, orient="vertical", command=self.template_text.yview)
        advanced_scroll_x = ttk.Scrollbar(advanced_text_frame, orient="horizontal", command=self.template_text.xview)
        advanced_scroll_y.grid(row=0, column=1, sticky="ns")
        advanced_scroll_x.grid(row=1, column=0, sticky="ew")
        self.template_text.configure(yscrollcommand=advanced_scroll_y.set, xscrollcommand=advanced_scroll_x.set)
        
        self.advanced_card.grid_remove()

        # ========== PANEL DE VISTA PREVIA ==========
        preview_card = ttk.LabelFrame(body, text="Vista previa en tiempo real", style="Card.TLabelframe")
        preview_card.grid(row=0, column=1, sticky="nsew")
        preview_card.columnconfigure(0, weight=1)
        preview_card.rowconfigure(1, weight=1)

        ttk.Label(
            preview_card,
            text="Así se verá el recibo en Ventas y en la reimpresión, con los datos dinámicos reales.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        # Frame contenedor para preview con scrolls
        preview_container = ttk.Frame(preview_card, style="Surface.TFrame")
        preview_container.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        preview_container.columnconfigure(0, weight=1)
        preview_container.rowconfigure(0, weight=1)

        # Text widget para preview con scrolls funcionales
        text_container = ttk.Frame(preview_container)
        text_container.grid(row=0, column=0, sticky="nsew")
        text_container.columnconfigure(0, weight=1)
        text_container.rowconfigure(0, weight=1)

        self.receipt_preview_text = tk.Text(
            text_container,
            font=("Courier New", 10),
            wrap=tk.NONE,
            state="disabled",
            relief="solid",
            borderwidth=1,
            background="#FFFFFF",
            foreground="#111827",
            padx=18,
            pady=18,
        )
        self.receipt_preview_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbars para preview
        preview_scroll_y = ttk.Scrollbar(text_container, orient="vertical", command=self.receipt_preview_text.yview)
        preview_scroll_x = ttk.Scrollbar(text_container, orient="horizontal", command=self.receipt_preview_text.xview)
        preview_scroll_y.grid(row=0, column=1, sticky="ns")
        preview_scroll_x.grid(row=1, column=0, sticky="ew")

        self.receipt_preview_text.configure(
            yscrollcommand=preview_scroll_y.set,
            xscrollcommand=preview_scroll_x.set
        )

        # Botones de acción
        btn_frame = ttk.Frame(parent, style="App.TFrame")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        
        ttk.Button(btn_frame, text="Vista previa real", style="Secondary.TButton", command=self.preview_receipt).pack(
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

        # Bindings para actualización en tiempo real
        self._bind_receipt_preview_updates()
        
        # Inicializar preview
        self.refresh_receipt_preview()

    def _load_receipt_settings(self):
        """Carga todas las configuraciones del recibo."""
        labels = load_receipt_labels(self.db.get_config)
        self.company_name_var.set(self.db.get_config("empresa_nombre", "") or "")
        self.company_rtn_var.set(self.db.get_config("empresa_rtn", "") or "")
        self.company_tel_var.set(self.db.get_config("empresa_tel", "") or "")
        self.company_email_var.set(self.db.get_config("empresa_email", "") or "")
        self.company_logo_var.set(self.db.get_config("empresa_logo_url", "") or "")
        self.receipt_title_var.set(labels["DOC_TITLE"])
        self.receipt_order_exempt_var.set(labels["ORDER_EXEMPT_LABEL"])
        self.receipt_exempt_register_var.set(labels["EXEMPT_REGISTER_LABEL"])
        self.receipt_discounts_var.set(labels["DISCOUNTS_LABEL"])
        self.receipt_summary_title_var.set(labels["SUMMARY_HEADER"])
        self.receipt_amount_label_var.set(labels["LABEL_MONTO_RECIBIDO"])
        self.receipt_change_label_var.set(labels["LABEL_VUELTO"])
        self.receipt_observations_label_var.set(labels["LABEL_OBSERVACIONES"])
        self.receipt_copy_label_var.set(labels["COPY_LABEL"])
        self.receipt_thanks_var.set(labels["THANK_YOU_MESSAGE"])

    def _bind_receipt_preview_updates(self):
        """Vincula todas las variables para actualizar el preview."""
        for variable in (
            self.company_name_var,
            self.company_rtn_var,
            self.company_tel_var,
            self.company_email_var,
            self.company_logo_var,
            self.receipt_title_var,
            self.receipt_order_exempt_var,
            self.receipt_exempt_register_var,
            self.receipt_discounts_var,
            self.receipt_summary_title_var,
            self.receipt_amount_label_var,
            self.receipt_change_label_var,
            self.receipt_observations_label_var,
            self.receipt_copy_label_var,
            self.receipt_thanks_var,
        ):
            variable.trace_add("write", self._on_receipt_settings_changed)

        self.company_address_text.bind("<KeyRelease>", self._on_receipt_text_changed)
        self.receipt_notes_text.bind("<KeyRelease>", self._on_receipt_text_changed)

    def _on_receipt_settings_changed(self, *_args):
        self.refresh_receipt_preview()

    def _on_receipt_text_changed(self, _event=None):
        self.refresh_receipt_preview()

    def _preview_company(self):
        """Devuelve los datos de la empresa para la vista previa."""
        return {
            "nombre": self.company_name_var.get().strip() or "PODEGA Y COMERCIAL RIVERA",
            "rtn": self.company_rtn_var.get().strip() or "12011972000081",
            "tel": self.company_tel_var.get().strip() or "2774-1192 / 9967-7300",
            "direccion": self.company_address_text.get("1.0", tk.END).strip()
            or "Bo. La Mercedes, Colonia la Ermita, 1ra Calle, 14-62, frente a Farmacia Santa, La Paz, Honduras",
            "email": self.company_email_var.get().strip() or "freddyrivera2015@gmail.com",
            "logo_url": self.company_logo_var.get().strip(),
        }

    def _preview_labels(self):
        """Devuelve las etiquetas del recibo para la vista previa."""
        defaults = default_receipt_labels()
        return {
            "DOC_TITLE": self.receipt_title_var.get().strip() or defaults["DOC_TITLE"],
            "ORDER_EXEMPT_LABEL": self.receipt_order_exempt_var.get().strip() or defaults["ORDER_EXEMPT_LABEL"],
            "EXEMPT_REGISTER_LABEL": self.receipt_exempt_register_var.get().strip() or defaults["EXEMPT_REGISTER_LABEL"],
            "DISCOUNTS_LABEL": self.receipt_discounts_var.get().strip() or defaults["DISCOUNTS_LABEL"],
            "SUMMARY_HEADER": self.receipt_summary_title_var.get().strip() or defaults["SUMMARY_HEADER"],
            "LABEL_MONTO_RECIBIDO": self.receipt_amount_label_var.get().strip() or defaults["LABEL_MONTO_RECIBIDO"],
            "LABEL_VUELTO": self.receipt_change_label_var.get().strip() or defaults["LABEL_VUELTO"],
            "LABEL_OBSERVACIONES": self.receipt_observations_label_var.get().strip() or defaults["LABEL_OBSERVACIONES"],
            "COPY_LABEL": self.receipt_copy_label_var.get().strip() or defaults["COPY_LABEL"],
            "THANK_YOU_MESSAGE": self.receipt_thanks_var.get().strip() or defaults["THANK_YOU_MESSAGE"],
        }

    def _current_template_content(self):
        """Obtiene el contenido actual de la plantilla."""
        if self.full_template_edit_unlocked:
            self._template_content = self.template_text.get("1.0", "end-1c")
        return self._template_content or self.repository.default_receipt_template()

    def _preview_number_to_words(self, number):
        """Convierte números a letras para la vista previa."""
        if int(number) == 15:
            return "QUINCE"
        return str(number)

    def _preview_items(self):
        """Devuelve items de ejemplo para la vista previa."""
        return [
            {
                "producto_id": 2,
                "nombre": "Agua Purificada 1L",
                "cantidad": 1,
                "precio_unitario": 15.0,
                "descuento_porcentaje": 0,
                "tax_rate": 0.15,
                "tax_exempt": False,
            }
        ]

    def refresh_receipt_preview(self):
        """Actualiza la vista previa en tiempo real con scrolls funcionales."""
        try:
            preview_text = build_receipt_preview_text(
                venta_id="439",
                fecha="2025-10-14 15:24:00",
                items=self._preview_items(),
                metodo_pago="EFECTIVO",
                empresa=self._preview_company(),
                number_to_words=self._preview_number_to_words,
                tax_included=True,
                template_text=self._current_template_content(),
                observaciones=self.receipt_notes_text.get("1.0", "end-1c").strip(),
                amount_received=20.0,
                labels=self._preview_labels(),
            )
            
            # Actualizar el texto
            self.receipt_preview_text.configure(state="normal")
            self.receipt_preview_text.delete("1.0", tk.END)
            self.receipt_preview_text.insert("1.0", preview_text)
            self.receipt_preview_text.configure(state="disabled")
            
            # Forzar actualización de scroll
            self.receipt_preview_text.update_idletasks()
            
            # Resetear scroll al inicio
            self.receipt_preview_text.xview_moveto(0)
            self.receipt_preview_text.yview_moveto(0)
            
        except Exception as e:
            # Si hay error, mostrar mensaje en el preview
            self.receipt_preview_text.configure(state="normal")
            self.receipt_preview_text.delete("1.0", tk.END)
            self.receipt_preview_text.insert("1.0", f"Error al generar vista previa: {e}")
            self.receipt_preview_text.configure(state="disabled")

    def on_template_text_changed(self, _event=None):
        """Maneja cambios en el texto de la plantilla avanzada."""
        self._template_content = self.template_text.get("1.0", "end-1c")
        self.refresh_receipt_preview()

    def preview_receipt(self):
        """Abre una vista previa real en el navegador."""
        try:
            html_preview = build_receipt_html(
                venta_id="439",
                fecha="2025-10-14 15:24:00",
                total=17.25,
                monto_pagado=20.0,
                vuelto=5.0,
                items=self._preview_items(),
                cliente=None,
                metodo_pago="EFECTIVO",
                mode="ticket",
                template_html=self._current_template_content(),
                empresa=self._preview_company(),
                observaciones=self.receipt_notes_text.get("1.0", "end-1c").strip(),
                labels=self._preview_labels(),
                number_to_words=self._preview_number_to_words,
            )
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as handle:
                handle.write(html_preview)
                self._last_preview_path = handle.name
            webbrowser.open(f"file://{self._last_preview_path}")
            messagebox.showinfo(
                "Vista previa",
                "La vista previa real se abrió en el navegador usando la misma plantilla activa de Ventas.",
                parent=self._parent(),
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar la vista previa: {e}", parent=self._parent())

    def save_receipt_template(self):
        """Guarda toda la configuración de la plantilla."""
        template_content = self._current_template_content().strip()
        if not template_content:
            messagebox.showerror("Error", "La plantilla no puede estar vacía.", parent=self._parent())
            return

        labels = self._preview_labels()
        try:
            self.repository.set_receipt_template(template_content)
            self.db.set_config("empresa_nombre", self.company_name_var.get().strip())
            self.db.set_config("empresa_rtn", self.company_rtn_var.get().strip())
            self.db.set_config("empresa_tel", self.company_tel_var.get().strip())
            self.db.set_config("empresa_email", self.company_email_var.get().strip())
            self.db.set_config("empresa_logo_url", self.company_logo_var.get().strip())
            self.db.set_config("empresa_direccion", self.company_address_text.get("1.0", tk.END).strip())
            self.db.set_config("recibo_observaciones", self.receipt_notes_text.get("1.0", tk.END).strip())
            self.db.set_config("recibo_doc_title", labels["DOC_TITLE"])
            self.db.set_config("recibo_label_orden_exenta", labels["ORDER_EXEMPT_LABEL"])
            self.db.set_config("recibo_label_registro_exento", labels["EXEMPT_REGISTER_LABEL"])
            self.db.set_config("recibo_label_descuentos", labels["DISCOUNTS_LABEL"])
            self.db.set_config("recibo_summary_title", labels["SUMMARY_HEADER"])
            self.db.set_config("recibo_label_monto_recibido", labels["LABEL_MONTO_RECIBIDO"])
            self.db.set_config("recibo_label_vuelto", labels["LABEL_VUELTO"])
            self.db.set_config("recibo_label_observaciones", labels["LABEL_OBSERVACIONES"])
            self.db.set_config("recibo_copy_label", labels["COPY_LABEL"])
            self.db.set_config("recibo_thanks_message", labels["THANK_YOU_MESSAGE"])
            
            messagebox.showinfo(
                "Éxito", 
                "La plantilla visual quedó guardada y sincronizada con Ventas.",
                parent=self._parent()
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar la plantilla.\n\n{exc}", parent=self._parent())

    def restore_default_template(self):
        """Restaura la plantilla por defecto."""
        if not messagebox.askyesno("Confirmar", "Restaurar la plantilla original del recibo?", parent=self._parent()):
            return

        defaults = default_receipt_labels()
        self._template_content = self.repository.default_receipt_template()
        self.receipt_title_var.set(defaults["DOC_TITLE"])
        self.receipt_order_exempt_var.set(defaults["ORDER_EXEMPT_LABEL"])
        self.receipt_exempt_register_var.set(defaults["EXEMPT_REGISTER_LABEL"])
        self.receipt_discounts_var.set(defaults["DISCOUNTS_LABEL"])
        self.receipt_summary_title_var.set(defaults["SUMMARY_HEADER"])
        self.receipt_amount_label_var.set(defaults["LABEL_MONTO_RECIBIDO"])
        self.receipt_change_label_var.set(defaults["LABEL_VUELTO"])
        self.receipt_observations_label_var.set(defaults["LABEL_OBSERVACIONES"])
        self.receipt_copy_label_var.set(defaults["COPY_LABEL"])
        self.receipt_thanks_var.set(defaults["THANK_YOU_MESSAGE"])
        
        if self.full_template_edit_unlocked:
            self.template_text.delete("1.0", tk.END)
            self.template_text.insert("1.0", self._template_content)
            
        self.refresh_receipt_preview()
        messagebox.showinfo("Éxito", "Se restauró la base original del recibo.", parent=self._parent())

    def toggle_full_template_edit(self):
        """Alterna entre modo protegido y edición total."""
        self.full_template_edit_unlocked = not self.full_template_edit_unlocked
        
        if self.full_template_edit_unlocked:
            self.template_lock_var.set(
                "Edición total habilitada: ahora puedes modificar toda la plantilla estructurada del recibo."
            )
            self.unlock_template_btn.configure(text="Volver a edición protegida")
            self.template_text.delete("1.0", tk.END)
            self.template_text.insert("1.0", self._template_content)
            self.advanced_card.grid()
        else:
            self._template_content = self.template_text.get("1.0", "end-1c")
            self.template_lock_var.set(
                "Modo protegido activo: la estructura, productos, cálculos e impuestos siguen bloqueados."
            )
            self.unlock_template_btn.configure(text="Desbloquear edición total")
            self.advanced_card.grid_remove()
            
        self.refresh_receipt_preview()