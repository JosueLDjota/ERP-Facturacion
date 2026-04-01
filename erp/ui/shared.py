"""
Utilidades visuales compartidas para la UI del ERP.
"""

# Contexto del archivo:
# Este modulo concentra helpers visuales transversales: tema ttk, colores,
# fuentes, modales, formateo monetario y resolucion de recursos. Debe ser el
# punto unico para comportamiento visual compartido entre pantallas legacy y la
# futura UI reorganizada bajo `erp.ui`.

from pathlib import Path
import tkinter as tk
from tkinter import ttk


PALETTE = {
    "blue_dark": "#1E2A44",
    "blue_primary": "#1D4ED8",
    "blue_light": "#DBEAFE",
    "blue_soft": "#F4F7FC",
    "white": "#FFFFFF",
    "black": "#0F172A",
    "gray_text": "#475569",
    "gray_border": "#D5DEE9",
    "danger": "#B91C1C",
    "success": "#0F766E",
    "surface_alt": "#EEF3FA",
    "sidebar_bg": "#0F1D36",
    "sidebar_text": "#E5EDF9",
}

FONTS = {
    "family": "Segoe UI",
    "base": ("Segoe UI", 10),
    "body": ("Segoe UI", 10),
    "title": ("Segoe UI Semibold", 24),
    "header": ("Segoe UI Semibold", 18),
    "subheader": ("Segoe UI Semibold", 12),
    "small": ("Segoe UI", 9),
}

HNL_PREFIX = "L"


def normalize_hnl_amount(value) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return round(number, 2)


def parse_hnl(value, default: float = 0.0) -> float:
    if value is None:
        return default
    cleaned = str(value).strip().upper()
    cleaned = cleaned.replace("HNL", "").replace(HNL_PREFIX, "").replace(",", "")
    if not cleaned:
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def format_hnl(value) -> str:
    amount = normalize_hnl_amount(value)
    return f"{HNL_PREFIX} {amount:,.2f}"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_resource_path(*parts: str) -> Path:
    return project_root().joinpath(*parts)


def center_window(window, width: int, height: int, parent=None):
    window.update_idletasks()
    base = parent if parent is not None else window
    x = base.winfo_rootx() + max(0, (base.winfo_width() - width) // 2)
    y = base.winfo_rooty() + max(0, (base.winfo_height() - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def create_modal(parent, title: str, width: int = 560, height: int = 420):
    popup = tk.Toplevel(parent)
    popup.title(title)
    popup.transient(parent)
    popup.grab_set()
    popup.configure(bg=PALETTE["blue_soft"])
    center_window(popup, width, height, parent=parent)
    return popup


def apply_app_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", font=FONTS["base"])
    style.configure("TFrame", background=PALETTE["blue_soft"])
    style.configure("App.TFrame", background=PALETTE["blue_soft"])
    style.configure("Surface.TFrame", background=PALETTE["white"])
    style.configure("AltSurface.TFrame", background=PALETTE["surface_alt"])
    style.configure("Topbar.TFrame", background=PALETTE["white"])
    style.configure("Sidebar.TFrame", background=PALETTE["sidebar_bg"])

    style.configure(
        "TLabel",
        background=PALETTE["blue_soft"],
        foreground=PALETTE["black"],
        font=FONTS["body"],
    )
    style.configure(
        "Header.TLabel",
        background=PALETTE["blue_soft"],
        foreground=PALETTE["black"],
        font=FONTS["header"],
    )
    style.configure(
        "Title.TLabel",
        background=PALETTE["blue_soft"],
        foreground=PALETTE["black"],
        font=FONTS["title"],
    )
    style.configure(
        "Subheader.TLabel",
        background=PALETTE["white"],
        foreground=PALETTE["blue_dark"],
        font=FONTS["subheader"],
    )
    style.configure(
        "Muted.TLabel",
        background=PALETTE["white"],
        foreground=PALETTE["gray_text"],
        font=FONTS["small"],
    )
    style.configure(
        "FormLabel.TLabel",
        background=PALETTE["white"],
        foreground=PALETTE["black"],
        font=FONTS["body"],
    )
    style.configure(
        "SidebarTitle.TLabel",
        background=PALETTE["sidebar_bg"],
        foreground=PALETTE["white"],
        font=FONTS["subheader"],
    )
    style.configure(
        "SidebarText.TLabel",
        background=PALETTE["sidebar_bg"],
        foreground=PALETTE["sidebar_text"],
        font=FONTS["small"],
    )
    style.configure(
        "IntroTitle.TLabel",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["black"],
        font=FONTS["title"],
    )
    style.configure(
        "IntroBody.TLabel",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["black"],
        font=FONTS["body"],
    )
    style.configure(
        "IntroMuted.TLabel",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["gray_text"],
        font=FONTS["small"],
    )

    style.configure(
        "Card.TLabelframe",
        background=PALETTE["white"],
        bordercolor=PALETTE["gray_border"],
        relief="solid",
        borderwidth=1,
        padding=14,
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=PALETTE["white"],
        foreground=PALETTE["blue_dark"],
        font=FONTS["subheader"],
    )

    style.configure(
        "TEntry",
        fieldbackground=PALETTE["white"],
        foreground=PALETTE["black"],
        bordercolor=PALETTE["gray_border"],
        lightcolor=PALETTE["gray_border"],
        darkcolor=PALETTE["gray_border"],
        insertcolor=PALETTE["black"],
        padding=8,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", PALETTE["blue_primary"])],
        lightcolor=[("focus", PALETTE["blue_primary"])],
        darkcolor=[("focus", PALETTE["blue_primary"])],
    )

    style.configure(
        "TCombobox",
        fieldbackground=PALETTE["white"],
        foreground=PALETTE["black"],
        bordercolor=PALETTE["gray_border"],
        lightcolor=PALETTE["gray_border"],
        darkcolor=PALETTE["gray_border"],
        padding=7,
    )
    style.map(
        "TCombobox",
        bordercolor=[("focus", PALETTE["blue_primary"])],
        lightcolor=[("focus", PALETTE["blue_primary"])],
        darkcolor=[("focus", PALETTE["blue_primary"])],
    )

    style.configure(
        "Primary.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(14, 9),
        relief="flat",
        borderwidth=0,
        background=PALETTE["blue_primary"],
        foreground=PALETTE["white"],
    )
    style.map("Primary.TButton", background=[("active", "#1E40AF")])

    style.configure(
        "Secondary.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(14, 9),
        relief="flat",
        borderwidth=0,
        background=PALETTE["surface_alt"],
        foreground=PALETTE["blue_dark"],
    )
    style.map("Secondary.TButton", background=[("active", "#E2E8F0")])

    style.configure(
        "Danger.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(14, 9),
        relief="flat",
        borderwidth=0,
        background=PALETTE["danger"],
        foreground=PALETTE["white"],
    )
    style.map("Danger.TButton", background=[("active", "#991B1B")])

    style.configure(
        "Success.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(14, 9),
        relief="flat",
        borderwidth=0,
        background=PALETTE["success"],
        foreground=PALETTE["white"],
    )
    style.map("Success.TButton", background=[("active", "#0F5F59")])

    style.configure(
        "Treeview",
        background=PALETTE["white"],
        foreground=PALETTE["black"],
        fieldbackground=PALETTE["white"],
        bordercolor=PALETTE["gray_border"],
        rowheight=30,
    )
    style.map(
        "Treeview",
        background=[("selected", PALETTE["blue_light"])],
        foreground=[("selected", PALETTE["black"])],
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["blue_dark"],
        relief="flat",
        font=("Segoe UI Semibold", 10),
        padding=8,
    )
    style.map("Treeview.Heading", background=[("active", "#E5EDF8")])

    return style
