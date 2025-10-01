"""
frames/sales.py
Sistema POS (Point of Sale) para gestión de ventas
"""

from tkinter import ttk, messagebox, Toplevel, filedialog
import tkinter as tk
from datetime import datetime
import random
import os


class SalesFrame(ttk.Frame):
    """Frame de ventas POS."""

    def __init__(self, parent, app):
        super().__init__(parent, padding="10")
        self.app = app
        self.db = app.db
        self.cart = {}
        self.discount_data = {}

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.cart_frame = ttk.Frame(self, padding="10", relief="groove")
        self.cart_frame.grid(row=0, column=0, sticky="nsew", padx=10)

        self.checkout_frame = ttk.Frame(self, padding="15", relief="groove")
        self.checkout_frame.grid(row=0, column=1, sticky="nsew", padx=10)

        self.create_cart_ui()
        self.create_checkout_ui()
        self.update_cart_display()

        # Atajos de teclado
        self.app.bind("<F1>", lambda e: self.open_product_search())
        self.app.bind("<F2>", lambda e: self.finalize_sale())
        self.app.bind("<F3>", lambda e: self.apply_discount_to_all())
        self.app.bind("<F4>", lambda e: self.remove_all_discounts())

    def load_discounts(self):
        """Carga los descuentos disponibles desde la base de datos."""
        try:
            discounts = self.db.fetch(
                "SELECT id, nombre, porcentaje FROM Descuentos ORDER BY nombre"
            )

            self.discount_combo["values"] = ()
            discount_options = ["Sin descuento"]
            self.discount_data = {
                0: {"id": 0, "nombre": "Sin descuento", "porcentaje": 0.0}
            }

            for discount in discounts:
                discount_id, nombre, porcentaje = discount
                porcentaje_int = (
                    int(porcentaje * 100)
                    if (porcentaje * 100).is_integer()
                    else round(porcentaje * 100, 1)
                )
                display_text = f"{nombre} - {porcentaje_int}%"
                discount_options.append(display_text)
                self.discount_data[len(discount_options) - 1] = {
                    "id": discount_id,
                    "nombre": nombre,
                    "porcentaje": porcentaje,
                }

            self.discount_combo["values"] = discount_options
            self.discount_combo.set("Sin descuento")

        except Exception as e:
            print(f"Error cargando descuentos: {e}")
            self.discount_combo["values"] = ("Sin descuento",)
            self.discount_combo.set("Sin descuento")
            self.discount_data = {
                0: {"id": 0, "nombre": "Sin descuento", "porcentaje": 0.0}
            }

    def create_cart_ui(self):
        """Crea la interfaz del carrito."""
        ttk.Label(
            self.cart_frame, text="Carrito de Compras", font=("Arial", 14, "bold")
        ).pack(pady=(0, 10))

        ttk.Button(
            self.cart_frame,
            text="Buscar Producto (F1)",
            command=self.open_product_search,
        ).pack(fill="x", pady=5)

        self.cart_tree = ttk.Treeview(
            self.cart_frame,
            columns=("ID", "Producto", "Cant", "PrecioU", "Desc", "Subtotal"),
            show="headings",
            height=15,
        )

        self.cart_tree.heading("ID", text="ID")
        self.cart_tree.heading("Producto", text="Producto")
        self.cart_tree.heading("Cant", text="Cant.")
        self.cart_tree.heading("PrecioU", text="P. Unit.")
        self.cart_tree.heading("Desc", text="Desc.")
        self.cart_tree.heading("Subtotal", text="Subtotal")

        self.cart_tree.column("ID", width=40, anchor="center")
        self.cart_tree.column("Producto", width=200)
        self.cart_tree.column("Cant", width=60, anchor="center")
        self.cart_tree.column("PrecioU", width=80, anchor="center")
        self.cart_tree.column("Desc", width=60, anchor="center")
        self.cart_tree.column("Subtotal", width=90, anchor="center")

        self.cart_tree.pack(fill="both", expand=True, pady=10)

        action_frame = ttk.Frame(self.cart_frame)
        action_frame.pack(fill="x", pady=5)

        ttk.Button(
            action_frame, text="Eliminar Producto", command=self.remove_from_cart
        ).pack(side="left", padx=5)

        ttk.Label(action_frame, text="Descuento:").pack(side="left", padx=(10, 5))
        self.discount_var = tk.StringVar()
        self.discount_combo = ttk.Combobox(
            action_frame, textvariable=self.discount_var, state="readonly", width=20
        )
        self.discount_combo.pack(side="left", padx=5)
        self.discount_combo.bind("<<ComboboxSelected>>", self.apply_selected_discount)

        ttk.Button(
            action_frame,
            text="Aplicar a Todos (F3)",
            command=self.apply_discount_to_all,
        ).pack(side="left", padx=2)

        ttk.Button(
            action_frame, text="Quitar Todos (F4)", command=self.remove_all_discounts
        ).pack(side="left", padx=2)

        self.load_discounts()

        ttk.Button(action_frame, text="Limpiar Carrito", command=self.clear_cart).pack(
            side="right", padx=5
        )

        self.discount_info_label = ttk.Label(
            self.cart_frame, text="", font=("Arial", 9), foreground="#666666"
        )
        self.discount_info_label.pack(fill="x", pady=(5, 0))

    def create_checkout_ui(self):
        """Crea la interfaz de pago."""
        ttk.Label(
            self.checkout_frame, text="Resumen de Venta", font=("Arial", 14, "bold")
        ).pack(pady=(0, 20))

        self.total_var = tk.DoubleVar(value=0.0)
        self.monto_pagado_var = tk.DoubleVar(value=0.0)
        self.vuelto_var = tk.DoubleVar(value=0.0)

        ttk.Label(self.checkout_frame, text="TOTAL A PAGAR:", font=("Arial", 14)).pack(
            anchor="w"
        )

        total_label = ttk.Label(
            self.checkout_frame,
            textvariable=self.total_var,
            font=("Arial", 32, "bold"),
            foreground="#dc3545",
        )
        total_label.pack(anchor="w", pady=(5, 20))

        monto_frame = ttk.Frame(self.checkout_frame)
        monto_frame.pack(fill="x", pady=10)

        ttk.Label(monto_frame, text="Monto Recibido:", font=("Arial", 12)).pack(
            side="left", padx=5
        )

        self.monto_entry = ttk.Entry(
            monto_frame,
            textvariable=self.monto_pagado_var,
            font=("Arial", 14),
            width=15,
        )
        self.monto_entry.pack(side="left", expand=True, fill="x")
        self.monto_entry.bind("<KeyRelease>", self.calculate_change)

        ttk.Label(self.checkout_frame, text="VUELTO:", font=("Arial", 14)).pack(
            anchor="w", pady=(20, 0)
        )

        vuelto_label = ttk.Label(
            self.checkout_frame,
            textvariable=self.vuelto_var,
            font=("Arial", 28, "bold"),
            foreground="#28a745",
        )
        vuelto_label.pack(anchor="w", pady=(5, 20))

        ttk.Button(
            self.checkout_frame, text="FINALIZAR VENTA (F2)", command=self.finalize_sale
        ).pack(fill="x", pady=20)

        self.status_label = ttk.Label(
            self.checkout_frame,
            text="Agregue productos al carrito",
            font=("Arial", 10),
            foreground="#666",
        )
        self.status_label.pack(pady=10)

    def open_product_search(self):
        """Abre ventana de búsqueda de productos."""
        search_win = Toplevel(self.app)
        search_win.title("Buscar Productos")
        search_win.geometry("900x600")

        search_win.grid_columnconfigure(0, weight=2)
        search_win.grid_columnconfigure(1, weight=1)
        search_win.grid_rowconfigure(2, weight=1)

        ttk.Label(
            search_win, text="Búsqueda de Productos", font=("Arial", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=10)

        search_frame = ttk.Frame(search_win)
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        search_var = tk.StringVar()
        ttk.Label(search_frame, text="Buscar:").pack(side="left", padx=5)
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind(
            "<KeyRelease>", lambda e: self.filter_search(tree, search_var.get())
        )

        tree = ttk.Treeview(
            search_win,
            columns=("ID", "Nombre", "Stock", "Precio"),
            show="headings",
            height=15,
        )

        tree.heading("ID", text="ID")
        tree.heading("Nombre", text="Producto")
        tree.heading("Stock", text="Stock")
        tree.heading("Precio", text="Precio")

        tree.column("ID", width=50, anchor="center")
        tree.column("Nombre", width=300)
        tree.column("Stock", width=80, anchor="center")
        tree.column("Precio", width=100, anchor="center")

        tree.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        tree.bind(
            "<<TreeviewSelect>>", lambda e: self.show_product_detail(tree, detail_frame)
        )

        detail_frame = ttk.LabelFrame(
            search_win, text="Detalle del Producto", padding=10
        )
        detail_frame.grid(row=2, column=1, sticky="nsew", padx=10, pady=5)

        self.detail_label = ttk.Label(
            detail_frame, text="Seleccione un producto", justify=tk.LEFT, wraplength=200
        )
        self.detail_label.pack(fill="both", expand=True)

        qty_frame = ttk.Frame(detail_frame)
        qty_frame.pack(fill="x", pady=10)

        qty_var = tk.IntVar(value=1)
        ttk.Label(qty_frame, text="Cantidad:").pack(side="left", padx=5)
        ttk.Spinbox(qty_frame, from_=1, to=100, textvariable=qty_var, width=10).pack(
            side="left", padx=5
        )

        ttk.Button(
            detail_frame,
            text="Añadir al Carrito",
            command=lambda: self.add_from_search(tree, qty_var.get(), search_win),
        ).pack(fill="x", pady=5)

        self.load_products_search(tree)

    def load_products_search(self, tree):
        """Carga productos en la ventana de búsqueda."""
        for item in tree.get_children():
            tree.delete(item)

        products = self.db.fetch(
            "SELECT id, nombre, stock, precio, descripcion FROM Productos WHERE stock > 0"
        )

        for prod in products:
            tree.insert(
                "",
                "end",
                values=(prod[0], prod[1], prod[2], f"${prod[3]:.2f}"),
                tags=(prod,),
            )

    def filter_search(self, tree, search_term):
        """Filtra productos en búsqueda."""
        for item in tree.get_children():
            tree.delete(item)

        if not search_term:
            self.load_products_search(tree)
            return

        products = self.db.fetch(
            "SELECT id, nombre, stock, precio, descripcion FROM Productos WHERE stock > 0"
        )

        search_lower = search_term.lower()
        for prod in products:
            if search_lower in prod[1].lower():
                tree.insert(
                    "",
                    "end",
                    values=(prod[0], prod[1], prod[2], f"${prod[3]:.2f}"),
                    tags=(prod,),
                )

    def show_product_detail(self, tree, detail_frame):
        """Muestra detalle del producto seleccionado."""
        selected = tree.focus()
        if not selected:
            return

        try:
            values = tree.item(selected, "values")

            if not values or len(values) < 4:
                self.detail_label.config(
                    text="Error: No se pudieron cargar los datos del producto"
                )
                return

            nombre = values[1]
            stock = values[2]
            precio_str = values[3].replace("$", "").replace(",", "")
            precio = float(precio_str)

            prod_id = values[0]
            result = self.db.fetch(
                "SELECT descripcion FROM Productos WHERE id = ?", (prod_id,)
            )
            desc = result[0][0] if result and result[0] else "Sin descripción"

            detail_text = f"Nombre: {nombre}\n\n"
            detail_text += f"Stock: {stock} unidades\n\n"
            detail_text += f"Precio: ${precio:.2f}\n\n"
            detail_text += f"Descripción:\n{desc or 'Sin descripción'}"

            self.detail_label.config(text=detail_text)

        except (ValueError, IndexError, TypeError) as e:
            self.detail_label.config(text=f"Error al cargar datos del producto: {e}")

    def add_from_search(self, tree, quantity, window):
        """Añade producto al carrito desde búsqueda."""
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto")
            return

        if quantity <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a 0")
            return

        try:
            item_values = tree.item(selected, "values")

            if not item_values or len(item_values) < 4:
                messagebox.showerror("Error", "No se encontraron datos del producto")
                return

            prod_id = int(item_values[0])
            nombre = str(item_values[1])
            stock = int(item_values[2])
            precio_str = item_values[3].replace("$", "").replace(",", "")
            precio = float(precio_str)

            current_qty = self.cart.get(prod_id, {}).get("cantidad", 0)
            if (current_qty + quantity) > stock:
                messagebox.showerror(
                    "Stock Insuficiente", f"Solo hay {stock} unidades disponibles"
                )
                return

            if prod_id in self.cart:
                self.cart[prod_id]["cantidad"] += quantity
            else:
                self.cart[prod_id] = {
                    "id": prod_id,
                    "nombre": nombre,
                    "precio_unitario": precio,
                    "cantidad": quantity,
                    "descuento_porcentaje": 0.0,
                }

            self.update_cart_display()
            messagebox.showinfo("Éxito", f"{nombre} añadido al carrito")
            window.destroy()

        except (IndexError, ValueError, TypeError) as e:
            error_msg = f"Error al obtener datos del producto: {e}"
            if "item_values" in locals():
                error_msg += f"\nValues: {item_values}"
            error_msg += "\nIntente seleccionar el producto nuevamente."
            messagebox.showerror("Error", error_msg)

    def update_cart_display(self):
        """Actualiza la visualización del carrito."""
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)

        total = 0.0
        total_descuentos = 0.0
        productos_con_descuento = 0

        for prod_id, data in self.cart.items():
            cant = data["cantidad"]
            precio = data["precio_unitario"]
            desc_pct = data["descuento_porcentaje"]

            desc_monto = (precio * cant) * desc_pct
            subtotal = (precio * cant) - desc_monto
            total += subtotal
            total_descuentos += desc_monto

            if desc_pct > 0:
                productos_con_descuento += 1

            self.cart_tree.insert(
                "",
                "end",
                iid=prod_id,
                values=(
                    prod_id,
                    data["nombre"],
                    cant,
                    f"${precio:.2f}",
                    f"{int(desc_pct*100)}%",
                    f"${subtotal:.2f}",
                ),
            )

        self.total_var.set(round(total, 2))

        if productos_con_descuento > 0:
            info_text = f"{productos_con_descuento} productos con descuento - Ahorro total: ${total_descuentos:.2f}"
            self.discount_info_label.config(text=info_text, foreground="#28a745")
        else:
            self.discount_info_label.config(text="", foreground="#666666")

        self.calculate_change()

    def calculate_change(self, event=None):
        """Calcula el vuelto."""
        try:
            total = self.total_var.get()
            pagado = self.monto_pagado_var.get()
            vuelto = pagado - total

            self.vuelto_var.set(round(max(0, vuelto), 2))

            if vuelto < 0:
                self.status_label.config(
                    text=f"Falta: ${abs(vuelto):.2f}", foreground="#dc3545"
                )
            else:
                self.status_label.config(
                    text="Listo para procesar", foreground="#28a745"
                )
        except:
            self.vuelto_var.set(0.0)

    def remove_from_cart(self):
        """Elimina producto del carrito."""
        selected = self.cart_tree.focus()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto")
            return

        try:
            prod_id = int(self.cart_tree.item(selected, "values")[0])
            if prod_id in self.cart:
                del self.cart[prod_id]
                self.update_cart_display()
            else:
                messagebox.showerror("Error", "Producto no encontrado en el carrito")
        except (ValueError, IndexError) as e:
            messagebox.showerror("Error", f"Error al eliminar producto: {e}")

    def clear_cart(self):
        """Limpia todo el carrito."""
        if not self.cart:
            return

        if messagebox.askyesno("Confirmar", "¿Limpiar todo el carrito?"):
            self.cart = {}
            self.update_cart_display()
            self.monto_pagado_var.set(0.0)
            self.discount_combo.set("Sin descuento")

    def apply_selected_discount(self, event=None):
        """Aplica el descuento seleccionado del combobox al producto seleccionado."""
        selected = self.cart_tree.focus()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un producto del carrito")
            return

        try:
            prod_id = int(self.cart_tree.item(selected, "values")[0])

            if prod_id not in self.cart:
                messagebox.showerror("Error", "Producto no encontrado en el carrito")
                return

            selected_index = self.discount_combo.current()
            if selected_index == -1:
                return

            discount_info = self.discount_data.get(selected_index)
            if not discount_info:
                messagebox.showerror("Error", "Descuento no válido")
                return

            descuento_porcentaje = discount_info["porcentaje"]
            self.cart[prod_id]["descuento_porcentaje"] = descuento_porcentaje

            self.update_cart_display()

            if descuento_porcentaje > 0:
                messagebox.showinfo(
                    "Descuento Aplicado",
                    f"Descuento '{discount_info['nombre']}' aplicado: {int(descuento_porcentaje * 100)}%",
                )
            else:
                messagebox.showinfo(
                    "Descuento Removido", "Descuento removido del producto"
                )

        except (ValueError, IndexError) as e:
            messagebox.showerror("Error", f"Error al aplicar descuento: {e}")

    def apply_discount_to_all(self):
        """Aplica el descuento seleccionado a todos los productos del carrito."""
        if not self.cart:
            messagebox.showwarning("Advertencia", "El carrito está vacío")
            return

        selected_index = self.discount_combo.current()
        if selected_index == -1:
            messagebox.showwarning("Advertencia", "Seleccione un descuento primero")
            return

        discount_info = self.discount_data.get(selected_index)
        if not discount_info:
            messagebox.showerror("Error", "Descuento no válido")
            return

        discount_name = discount_info["nombre"]
        discount_pct = int(discount_info["porcentaje"] * 100)

        if discount_pct > 0:
            mensaje = f"¿Aplicar '{discount_name}' ({discount_pct}%) a todos los {len(self.cart)} productos del carrito?"
        else:
            mensaje = f"¿Remover descuentos de todos los {len(self.cart)} productos del carrito?"

        if not messagebox.askyesno("Confirmar Descuento Masivo", mensaje):
            return

        try:
            descuento_porcentaje = discount_info["porcentaje"]
            productos_afectados = 0

            for prod_id in self.cart:
                self.cart[prod_id]["descuento_porcentaje"] = descuento_porcentaje
                productos_afectados += 1

            self.update_cart_display()

            if descuento_porcentaje > 0:
                messagebox.showinfo(
                    "Descuento Aplicado",
                    f"Descuento '{discount_name}' ({discount_pct}%) aplicado a {productos_afectados} productos",
                )
            else:
                messagebox.showinfo(
                    "Descuentos Removidos",
                    f"Descuentos removidos de {productos_afectados} productos",
                )

        except Exception as e:
            messagebox.showerror("Error", f"Error al aplicar descuento masivo: {e}")

    def remove_all_discounts(self):
        """Remueve todos los descuentos del carrito."""
        if not self.cart:
            messagebox.showwarning("Advertencia", "El carrito está vacío")
            return

        productos_con_descuento = sum(
            1 for item in self.cart.values() if item.get("descuento_porcentaje", 0) > 0
        )

        if productos_con_descuento == 0:
            messagebox.showinfo(
                "Información", "No hay productos con descuentos en el carrito"
            )
            return

        if not messagebox.askyesno(
            "Confirmar", f"¿Remover descuentos de {productos_con_descuento} productos?"
        ):
            return

        try:
            productos_afectados = 0
            for prod_id in self.cart:
                if self.cart[prod_id].get("descuento_porcentaje", 0) > 0:
                    self.cart[prod_id]["descuento_porcentaje"] = 0.0
                    productos_afectados += 1

            self.update_cart_display()
            self.discount_combo.set("Sin descuento")

            messagebox.showinfo(
                "Descuentos Removidos",
                f"Descuentos removidos de {productos_afectados} productos",
            )

        except Exception as e:
            messagebox.showerror("Error", f"Error al remover descuentos: {e}")

    def finalize_sale(self):
        """Finaliza la venta y muestra vista previa del recibo."""
        if not self.cart:
            messagebox.showwarning("Advertencia", "El carrito está vacío")
            return

        total = self.total_var.get()
        pagado = self.monto_pagado_var.get()

        if pagado < total:
            messagebox.showerror("Error", "Monto insuficiente")
            return

        vuelto = self.vuelto_var.get()
        venta_id = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # Guardar venta en base de datos
            self.db.execute(
                "INSERT INTO Ventas (id, fecha, total, monto_pagado, vuelto, usuario_id, tipo_recibo) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (venta_id, fecha, total, pagado, vuelto, self.app.current_user[0], "HTML"),
            )

            # Guardar detalle y actualizar stock
            for prod_id, data in self.cart.items():
                cant = data["cantidad"]
                precio = data["precio_unitario"]
                desc_pct = data["descuento_porcentaje"]
                desc_monto = (precio * cant) * desc_pct
                subtotal = (precio * cant) - desc_monto

                self.db.execute(
                    "INSERT INTO DetalleVenta (venta_id, producto_id, nombre_producto, cantidad, precio_unitario, descuento, subtotal) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (venta_id, prod_id, data["nombre"], cant, precio, desc_monto, subtotal),
                )

                self.db.execute(
                    "UPDATE Productos SET stock = stock - ? WHERE id = ?",
                    (cant, prod_id),
                )

            # Mostrar ventana de vista previa y opciones de recibo
            self.show_receipt_preview(venta_id, total, pagado, vuelto, fecha)

            # Limpiar carrito después de procesar venta
            self.cart = {}
            self.update_cart_display()
            self.monto_pagado_var.set(0.0)
            self.discount_combo.set("Sin descuento")

        except Exception as e:
            messagebox.showerror("Error", f"Error al procesar venta: {e}")

    def show_receipt_preview(self, venta_id, total, pagado, vuelto, fecha):
        """Muestra ventana profesional de vista previa del recibo."""
        preview_win = Toplevel(self.app)
        preview_win.title("Vista Previa - Recibo de Venta")
        preview_win.geometry("850x1100")  # Aproximado tamaño carta en pixeles
        preview_win.resizable(True, True)  # Permite redimensionar la ventana
        
        # Generar HTML del recibo
        html_content = self.generate_receipt_html(venta_id, total, pagado, vuelto, fecha)
        
        # Frame principal
        main_frame = ttk.Frame(preview_win, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(
            title_frame,
            text="Venta Procesada Exitosamente",
            font=("Arial", 16, "bold"),
            foreground="#28a745"
        ).pack(side="left")
        
        ttk.Label(
            title_frame,
            text=f"ID: {venta_id}",
            font=("Arial", 10),
            foreground="#666"
        ).pack(side="right")
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=10)
        
        # Frame de vista previa (izquierda) y opciones (derecha)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Vista previa del recibo
        preview_frame = ttk.LabelFrame(content_frame, text="Vista Previa del Recibo", padding=10)
        preview_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Text widget con el contenido del recibo
        preview_text = tk.Text(
        preview_frame,
        font=("Courier New", 11),
        wrap=tk.WORD,
        bg="#ffffff",
        relief="sunken",
        borderwidth=2
    )

        preview_text.pack(fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=preview_text.yview)
        scrollbar.pack(side="right", fill="y")
        preview_text.configure(yscrollcommand=scrollbar.set)
        
        # Insertar contenido del recibo
        receipt_content = self.format_receipt_for_preview(venta_id, total, pagado, vuelto, fecha)
        preview_text.insert("1.0", receipt_content)
        preview_text.configure(state="disabled")
        
        # Panel de opciones (derecha)
        options_frame = ttk.Frame(content_frame)
        options_frame.pack(side="right", fill="y", padx=(10, 0))
        
        # Sección de impresora
        printer_frame = ttk.LabelFrame(options_frame, text="Estado de Impresora", padding=15)
        printer_frame.pack(fill="x", pady=(0, 15))
        
        # Detectar impresora
        printer_detected, printer_name = self.detect_printer()
        
        if printer_detected:
            ttk.Label(
                printer_frame,
                text="Impresora Detectada",
                font=("Arial", 11, "bold"),
                foreground="#28a745"
            ).pack(anchor="w", pady=(0, 5))
            
            ttk.Label(
                printer_frame,
                text=f"{printer_name}",
                font=("Arial", 9)
            ).pack(anchor="w", pady=(0, 10))
            
            # Opciones de tamaño
            ttk.Label(printer_frame, text="Tamaño de Papel:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 3))
            
            self.paper_size_var = tk.StringVar(value="ticket")
            ttk.Radiobutton(
                printer_frame,
                text="Formato Ticket (80mm)",
                variable=self.paper_size_var,
                value="ticket"
            ).pack(anchor="w", padx=10)
            
            ttk.Radiobutton(
                printer_frame,
                text="Formato Carta (Letter)",
                variable=self.paper_size_var,
                value="letter"
            ).pack(anchor="w", padx=10)
            
        else:
            ttk.Label(
                printer_frame,
                text="No se detectó impresora",
                font=("Arial", 11, "bold"),
                foreground="#dc3545"
            ).pack(anchor="w", pady=(0, 10))
            
            ttk.Button(
                printer_frame,
                text="Configurar Impresora",
                command=self.open_printer_settings
            ).pack(fill="x", pady=5)
        
        # Sección de guardar
        save_frame = ttk.LabelFrame(options_frame, text="Configuración de Guardado", padding=15)
        save_frame.pack(fill="x", pady=(0, 15))
        
        # Cargar ruta guardada
        saved_path = self.db.get_config("recibo_save_path", "")
        
        ttk.Label(save_frame, text="Carpeta Actual:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 3))
        
        self.path_label = ttk.Label(
            save_frame,
            text=saved_path if saved_path else "No configurada",
            font=("Arial", 8),
            foreground="#666",
            wraplength=200
        )
        self.path_label.pack(anchor="w", pady=(0, 10))
        
        ttk.Button(
            save_frame,
            text="Cambiar Carpeta",
            command=lambda: self.change_save_folder(preview_win)
        ).pack(fill="x")
        
        # Botones de acción principales
        action_frame = ttk.Frame(options_frame)
        action_frame.pack(fill="x", pady=(15, 0))
        
        if printer_detected:
            ttk.Button(
                action_frame,
                text="Imprimir Recibo",
                command=lambda: self.print_receipt(html_content, preview_win),
                style="Accent.TButton"
            ).pack(fill="x", pady=5)
        
        ttk.Button(
            action_frame,
            text="Guardar Recibo",
            command=lambda: self.save_receipt(html_content, venta_id, preview_win)
        ).pack(fill="x", pady=5)
        
        ttk.Button(
            action_frame,
            text="Cerrar",
            command=preview_win.destroy
        ).pack(fill="x", pady=5)
        
        # Información adicional
        info_frame = ttk.Frame(options_frame)
        info_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Label(
            info_frame,
            text="Consejo",
            font=("Arial", 9, "bold")
        ).pack(anchor="w")
        
        ttk.Label(
            info_frame,
            text="Puede guardar e imprimir el mismo recibo",
            font=("Arial", 8),
            foreground="#666",
            wraplength=200
        ).pack(anchor="w")

    def format_receipt_for_preview(self, venta_id, total, pagado, vuelto, fecha):
        """Formatea el recibo en texto plano para vista previa."""
        lines = []
        lines.append("=" * 40)
        lines.append("MI NEGOCIO ERP".center(40))
        lines.append("=" * 40)
        lines.append("")
        lines.append(f"Venta ID: {venta_id}")
        lines.append(f"Fecha: {fecha}")
        lines.append("")
        lines.append("-" * 40)
        lines.append(f"{'PRODUCTO':<20} {'CANT':<5} {'SUBTOTAL':>10}")
        lines.append("-" * 40)
        
        for data in self.cart.values():
            cant = data["cantidad"]
            precio = data["precio_unitario"]
            desc_pct = data["descuento_porcentaje"]
            desc_monto = (precio * cant) * desc_pct
            subtotal = (precio * cant) - desc_monto
            
            nombre = data["nombre"][:18]
            desc_text = f" (-{int(desc_pct*100)}%)" if desc_pct > 0 else ""
            
            lines.append(f"{nombre+desc_text:<20} {cant:<5} ${subtotal:>9.2f}")
        
        lines.append("-" * 40)
        lines.append("")
        lines.append(f"{'TOTAL A PAGAR:':<25} ${total:>10.2f}")
        lines.append(f"{'MONTO RECIBIDO:':<25} ${pagado:>10.2f}")
        lines.append(f"{'VUELTO:':<25} ${vuelto:>10.2f}")
        lines.append("")
        lines.append("=" * 40)
        lines.append("Gracias por su compra".center(40))
        lines.append("Vuelva pronto".center(40))
        lines.append("=" * 40)
        
        return "\n".join(lines)

    def detect_printer(self):
        """Detecta si hay una impresora disponible."""
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                try:
                    import win32print
                    default_printer = win32print.GetDefaultPrinter()
                    if default_printer:
                        return True, default_printer
                except:
                    pass
            
            elif system == "Darwin":
                try:
                    import subprocess
                    result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout:
                        printer = result.stdout.split(':')[-1].strip()
                        return True, printer
                except:
                    pass
            
            elif system == "Linux":
                try:
                    import subprocess
                    result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout:
                        printer = result.stdout.split(':')[-1].strip()
                        return True, printer
                except:
                    pass
            
            return False, "No detectada"
        except:
            return False, "No detectada"

    def open_printer_settings(self):
        """Abre ventana de configuración de impresora."""
        settings_win = Toplevel(self.app)
        settings_win.title("Configuración de Impresora")
        settings_win.geometry("500x400")
        
        main_frame = ttk.Frame(settings_win, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(
            main_frame,
            text="Configuración de Impresora",
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 20))
        
        ttk.Label(
            main_frame,
            text="No se detectó ninguna impresora conectada",
            font=("Arial", 11),
            foreground="#dc3545"
        ).pack(pady=10)
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        ttk.Label(
            main_frame,
            text="Pasos para configurar su impresora:",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        steps = [
            "1. Conecte físicamente la impresora a su computadora",
            "2. Encienda la impresora",
            "3. Instale los drivers desde el sitio web del fabricante",
            "4. Configure la impresora en su sistema operativo:",
            "   - Windows: Panel de Control > Dispositivos e impresoras",
            "   - macOS: Preferencias del Sistema > Impresoras",
            "   - Linux: Configuración > Impresoras",
            "5. Reinicie esta aplicación para detectar la impresora"
        ]
        
        for step in steps:
            ttk.Label(
                main_frame,
                text=step,
                font=("Arial", 9),
                foreground="#333"
            ).pack(anchor="w", pady=2, padx=20)
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(
            btn_frame,
            text="Reintentar Detección",
            command=lambda: self.retry_printer_detection(settings_win)
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="Cerrar",
            command=settings_win.destroy
        ).pack(side="right", padx=5)

    def retry_printer_detection(self, window):
        """Reintenta detectar la impresora."""
        detected, name = self.detect_printer()
        if detected:
            messagebox.showinfo(
                "Impresora Detectada",
                f"Impresora encontrada:\n{name}\n\nYa puede imprimir sus recibos."
            )
            window.destroy()
        else:
            messagebox.showwarning(
                "No Detectada",
                "No se detectó ninguna impresora.\nVerifique la conexión e instalación de drivers."
            )

    def change_save_folder(self, parent_window):
        """Permite cambiar la carpeta donde se guardan los recibos."""
        folder = filedialog.askdirectory(
            title="Seleccionar carpeta para guardar recibos",
            parent=parent_window
        )
        
        if folder:
            self.db.set_config("recibo_save_path", folder)
            self.path_label.config(text=folder)
            messagebox.showinfo(
                "Carpeta Configurada",
                f"Los recibos se guardarán en:\n{folder}"
            )

    def print_receipt(self, html_content, window):
        """Imprime el recibo."""
        try:
            import tempfile
            import webbrowser
            
            paper_size = getattr(self, 'paper_size_var', None)
            size_text = paper_size.get() if paper_size else "ticket"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open(f'file://{temp_path}')
            
            messagebox.showinfo(
                "Impresión Iniciada",
                f"Se abrió el recibo en su navegador.\n"
                f"Tamaño: {size_text}\n\n"
                f"Use Ctrl+P o Cmd+P para imprimir."
            )
            
            window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error de Impresión", f"No se pudo imprimir: {e}")

    def save_receipt(self, html_content, venta_id, window):
        """Guarda el recibo en la carpeta configurada."""
        saved_path = self.db.get_config("recibo_save_path", "")
        
        if saved_path and os.path.exists(saved_path):
            filename = f"Recibo_{venta_id}.html"
            file_path = os.path.join(saved_path, filename)
        else:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=[("HTML", "*.html"), ("Todos los archivos", "*.*")],
                initialfile=f"Recibo_{venta_id}.html",
                title="Guardar Recibo"
            )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                messagebox.showinfo(
                    "Recibo Guardado",
                    f"Recibo guardado exitosamente en:\n{file_path}"
                )
                
                if messagebox.askyesno("Abrir Recibo", "¿Desea abrir el recibo guardado?"):
                    import webbrowser
                    webbrowser.open(f'file://{file_path}')
                
                window.destroy()
                
            except Exception as e:
                messagebox.showerror("Error al Guardar", f"No se pudo guardar el recibo: {e}")

    def generate_receipt_html(self, venta_id, total, pagado, vuelto, fecha):
        """Genera el contenido HTML del recibo."""
        template = self.db.get_config(
            "recibo_template", self.db.default_receipt_template()
        )

        items_html = ""
        for data in self.cart.values():
            cant = data["cantidad"]
            precio = data["precio_unitario"]
            desc_pct = data["descuento_porcentaje"]
            desc_monto = (precio * cant) * desc_pct
            subtotal = (precio * cant) - desc_monto

            desc_text = f" (-{int(desc_pct*100)}%)" if desc_pct > 0 else ""
            items_html += f'<div class="item"><span>{data["nombre"]}{desc_text}</span><span>{cant} / ${subtotal:.2f}</span></div>\n'

        html_content = template
        html_content = html_content.replace("{{NOMBRE_NEGOCIO}}", "Mi Negocio ERP")
        html_content = html_content.replace("{{ID_VENTA}}", venta_id)
        html_content = html_content.replace("{{FECHA}}", fecha)
        html_content = html_content.replace("{{TOTAL}}", f"{total:.2f}")
        html_content = html_content.replace("{{MONTO_PAGADO}}", f"{pagado:.2f}")
        html_content = html_content.replace("{{VUELTO}}", f"{vuelto:.2f}")
        html_content = html_content.replace("<!-- ITEMS_PLACEHOLDER -->", items_html)
        
        return html_content
