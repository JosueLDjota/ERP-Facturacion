"""
frames/dashboard.py
Dashboard ejecutivo con KPIs y graficas de negocio.
"""

# Contexto del archivo:
# El dashboard consolida informacion operativa para lectura gerencial:
# indicadores de ventas, stock y comportamiento comercial. No es un modulo
# transaccional, pero sirve como consumidor agregado de datos del sistema.

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from .ui import PALETTE, format_hnl


class DashboardFrame(ttk.Frame):
    """Dashboard con resumen financiero, tendencia y alertas de inventario."""

    MONTH_LABELS = {
        "01": "Ene",
        "02": "Feb",
        "03": "Mar",
        "04": "Abr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Ago",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dic",
    }

    def __init__(self, parent, app):
        super().__init__(parent, padding=0, style="App.TFrame")
        self.app = app
        self.db = app.db

        self.total_sales = 0.0
        self.daily_sales = 0.0
        self.monthly_sales = 0.0
        self.low_stock = []
        self.best_seller = ("N/A", 0)
        self.total_products = 0
        self.ventas_por_mes = []
        self.ventas_por_dia = []

        self.month_canvas = None
        self.daily_canvas = None

        self._configure_styles()
        self._build_layout()
        self.refresh_dashboard()

    def destroy(self):
        if hasattr(self, "scroll_canvas"):
            self.scroll_canvas.unbind_all("<MouseWheel>")
        super().destroy()

    def _configure_styles(self):
        style = ttk.Style()
        style.configure(
            "DashCard.TFrame",
            background=PALETTE["white"],
            borderwidth=1,
            relief="solid",
            bordercolor=PALETTE["gray_border"],
        )
        style.configure(
            "DashCardTitle.TLabel",
            background=PALETTE["white"],
            foreground=PALETTE["gray_text"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "DashCardValue.TLabel",
            background=PALETTE["white"],
            foreground=PALETTE["black"],
            font=("Segoe UI Semibold", 20),
        )
        style.configure(
            "DashCardNote.TLabel",
            background=PALETTE["white"],
            foreground=PALETTE["gray_text"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "DashPanel.TLabelframe",
            background=PALETTE["white"],
            borderwidth=1,
            relief="solid",
            bordercolor=PALETTE["gray_border"],
            padding=12,
        )
        style.configure(
            "DashPanel.TLabelframe.Label",
            background=PALETTE["white"],
            foreground=PALETTE["blue_dark"],
            font=("Segoe UI Semibold", 12),
        )

    def _build_layout(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.scroll_canvas = tk.Canvas(self, highlightthickness=0, bg=PALETTE["blue_soft"])
        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(self, orient="vertical", command=self.scroll_canvas.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        self.scroll_canvas.configure(yscrollcommand=y_scroll.set)

        self.content = ttk.Frame(self.scroll_canvas, padding=12, style="App.TFrame")
        self._scroll_window_id = self.scroll_canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind(
            "<Configure>",
            lambda _event: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")),
        )
        self.scroll_canvas.bind("<Configure>", self._on_canvas_resize)
        self.scroll_canvas.bind("<Enter>", self._bind_mousewheel)
        self.scroll_canvas.bind("<Leave>", self._unbind_mousewheel)

        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(2, weight=1)

        header = ttk.Frame(self.content, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Resumen operativo", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Indicadores de ventas, inventario y tendencia para decisiones rapidas.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Button(header, text="Actualizar", style="Primary.TButton", command=self.refresh_dashboard).grid(
            row=0, column=1, rowspan=2, sticky="e"
        )

        self.kpi_row = ttk.Frame(self.content, style="App.TFrame")
        self.kpi_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for col in range(2):
            self.kpi_row.columnconfigure(col, weight=1)

        self.panels = ttk.Frame(self.content, style="App.TFrame")
        self.panels.grid(row=2, column=0, sticky="nsew")
        self.panels.columnconfigure(0, weight=5)
        self.panels.columnconfigure(1, weight=3)
        self.panels.rowconfigure(0, weight=1)
        self.panels.rowconfigure(1, weight=1)

        self.month_chart_frame = ttk.LabelFrame(self.panels, text="Ventas mensuales (12 meses)", style="DashPanel.TLabelframe")
        self.month_chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        self.daily_chart_frame = ttk.LabelFrame(self.panels, text="Ventas del mes por dia", style="DashPanel.TLabelframe")
        self.daily_chart_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        self.stock_panel = ttk.LabelFrame(self.panels, text="Alertas de stock bajo", style="DashPanel.TLabelframe")
        self.stock_panel.grid(row=0, column=1, rowspan=2, sticky="nsew")
        self.stock_panel.columnconfigure(0, weight=1)
        self.stock_panel.rowconfigure(1, weight=1)

        self.stock_count_var = tk.StringVar(value="0 productos en alerta")
        ttk.Label(self.stock_panel, textvariable=self.stock_count_var, style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        stock_table_host = ttk.Frame(self.stock_panel, style="Surface.TFrame")
        stock_table_host.grid(row=1, column=0, sticky="nsew")
        stock_table_host.columnconfigure(0, weight=1)
        stock_table_host.rowconfigure(0, weight=1)

        self.stock_tree = ttk.Treeview(stock_table_host, columns=("Producto", "Stock"), show="headings", height=18)
        self.stock_tree.heading("Producto", text="Producto")
        self.stock_tree.heading("Stock", text="Stock")
        self.stock_tree.column("Producto", width=340, anchor="w")
        self.stock_tree.column("Stock", width=110, anchor="center")

        stock_scroll = ttk.Scrollbar(stock_table_host, orient="vertical", command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=stock_scroll.set)

        self.stock_tree.grid(row=0, column=0, sticky="nsew")
        stock_scroll.grid(row=0, column=1, sticky="ns")

    def _bind_mousewheel(self, _event=None):
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None):
        self.scroll_canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_resize(self, event):
        self.scroll_canvas.itemconfig(self._scroll_window_id, width=event.width)

    def _render_kpis(self):
        for widget in self.kpi_row.winfo_children():
            widget.destroy()

        cards = [
            ("Ventas totales", format_hnl(self.total_sales), "Historico acumulado", PALETTE["blue_primary"]),
            ("Ventas del mes", format_hnl(self.monthly_sales), "Rendimiento mensual", PALETTE["success"]),
            ("Ventas del dia", format_hnl(self.daily_sales), "Operacion actual", "#B45309"),
            ("Producto mas vendido", str(self.best_seller[0]), f"{int(self.best_seller[1])} unidades", PALETTE["blue_dark"]),
            ("Total de productos", f"{self.total_products}", "Inventario registrado", PALETTE["blue_primary"]),
            ("Stock bajo", f"{len(self.low_stock)}", "Productos <= 10 unidades", PALETTE["danger"]),
        ]

        for idx, (title, value, note, color) in enumerate(cards):
            row = idx // 2
            col = idx % 2
            card = ttk.Frame(self.kpi_row, style="DashCard.TFrame", padding=14)
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

            ttk.Label(card, text=title, style="DashCardTitle.TLabel").pack(anchor="w")
            value_label = ttk.Label(card, text=value, style="DashCardValue.TLabel")
            value_label.pack(anchor="w", pady=(8, 3))
            value_label.configure(foreground=color)
            ttk.Label(card, text=note, style="DashCardNote.TLabel").pack(anchor="w")

    def _draw_month_chart(self):
        for widget in self.month_chart_frame.winfo_children():
            widget.destroy()

        if not self.ventas_por_mes:
            ttk.Label(self.month_chart_frame, text="No hay datos para mostrar", style="Muted.TLabel").pack(anchor="w")
            return

        labels = []
        totals = []
        for year_month, total in self.ventas_por_mes:
            year = year_month[:4]
            month = year_month[5:7]
            labels.append(f"{self.MONTH_LABELS.get(month, month)} {year[2:]}")
            totals.append(float(total or 0))

        fig = Figure(figsize=(9.0, 3.6), dpi=100)
        ax = fig.add_subplot(111)
        ax.bar(labels, totals, color="#2563EB", alpha=0.9)
        ax.set_xlabel("Mes")
        ax.set_ylabel("Monto (HNL)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _pos: f"L {x:,.0f}"))
        ax.tick_params(axis="x", rotation=20)
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        fig.tight_layout()

        self.month_canvas = FigureCanvasTkAgg(fig, master=self.month_chart_frame)
        self.month_canvas.draw()
        self.month_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _draw_daily_chart(self):
        for widget in self.daily_chart_frame.winfo_children():
            widget.destroy()

        if not self.ventas_por_dia:
            ttk.Label(self.daily_chart_frame, text="No hay datos para mostrar", style="Muted.TLabel").pack(anchor="w")
            return

        days = [d for d, _ in self.ventas_por_dia]
        totals = [float(v or 0) for _, v in self.ventas_por_dia]

        fig = Figure(figsize=(9.0, 3.6), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(days, totals, marker="o", linewidth=2.5, color="#0F766E")
        ax.set_xlabel("Dia")
        ax.set_ylabel("Monto (HNL)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _pos: f"L {x:,.0f}"))
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        fig.tight_layout()

        self.daily_canvas = FigureCanvasTkAgg(fig, master=self.daily_chart_frame)
        self.daily_canvas.draw()
        self.daily_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _render_stock_table(self):
        self.stock_tree.delete(*self.stock_tree.get_children())

        for nombre, stock in self.low_stock:
            self.stock_tree.insert("", "end", values=(nombre, int(stock or 0)))

        self.stock_count_var.set(f"{len(self.low_stock)} productos en alerta")

    def _load_data(self):
        self.total_sales = float(self.db.fetch("SELECT COALESCE(SUM(total), 0) FROM Ventas")[0][0] or 0)
        self.daily_sales = float(
            self.db.fetch("SELECT COALESCE(SUM(total), 0) FROM Ventas WHERE DATE(fecha)=DATE('now', 'localtime')")[0][0]
            or 0
        )
        self.monthly_sales = float(
            self.db.fetch(
                "SELECT COALESCE(SUM(total), 0) FROM Ventas WHERE strftime('%Y-%m', fecha)=strftime('%Y-%m','now','localtime')"
            )[0][0]
            or 0
        )

        self.low_stock = self.db.fetch(
            "SELECT nombre, stock FROM Productos WHERE stock <= 10 ORDER BY stock ASC, nombre ASC"
        )

        best_seller_data = self.db.fetch(
            """
            SELECT nombre_producto, SUM(cantidad)
            FROM DetalleVenta
            GROUP BY nombre_producto
            ORDER BY SUM(cantidad) DESC
            LIMIT 1
            """
        )
        self.best_seller = best_seller_data[0] if best_seller_data else ("N/A", 0)

        self.total_products = int(self.db.fetch("SELECT COALESCE(COUNT(*), 0) FROM Productos")[0][0] or 0)

        monthly_rows = self.db.fetch(
            """
            SELECT strftime('%Y-%m', fecha) AS ym, SUM(total)
            FROM Ventas
            GROUP BY ym
            ORDER BY ym DESC
            LIMIT 12
            """
        )
        self.ventas_por_mes = list(reversed(monthly_rows))

        self.ventas_por_dia = self.db.fetch(
            """
            SELECT strftime('%d', fecha), SUM(total)
            FROM Ventas
            WHERE strftime('%Y-%m', fecha)=strftime('%Y-%m','now','localtime')
            GROUP BY strftime('%d', fecha)
            ORDER BY strftime('%d', fecha)
            """
        )

    def refresh_dashboard(self):
        self._load_data()
        self._render_kpis()
        self._draw_month_chart()
        self._draw_daily_chart()
        self._render_stock_table()
