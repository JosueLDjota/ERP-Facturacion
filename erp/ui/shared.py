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


THEMES = {
    "light": {
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
    },
    "dark": {
        "blue_dark": "#E2E8F0",
        "blue_primary": "#60A5FA",
        "blue_light": "#1D4ED8",
        "blue_soft": "#0F172A",
        "white": "#111827",
        "black": "#F8FAFC",
        "gray_text": "#CBD5E1",
        "gray_border": "#334155",
        "danger": "#F87171",
        "success": "#34D399",
        "surface_alt": "#1E293B",
        "sidebar_bg": "#020617",
        "sidebar_text": "#E2E8F0",
    },
}

THEME_LABELS = {
    "light": "Tema claro",
    "dark": "Tema oscuro",
}

DEFAULT_THEME = "light"
PALETTE = dict(THEMES[DEFAULT_THEME])

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


def normalize_theme_name(theme_name: str | None) -> str:
    candidate = str(theme_name or DEFAULT_THEME).strip().lower()
    if candidate not in THEMES:
        return DEFAULT_THEME
    return candidate


def get_available_themes() -> list[tuple[str, str]]:
    return [(key, THEME_LABELS.get(key, key.title())) for key in THEMES]


def set_active_theme(theme_name: str | None) -> str:
    active_theme = normalize_theme_name(theme_name)
    PALETTE.clear()
    PALETTE.update(THEMES[active_theme])
    return active_theme


def _palette_token_for_color(color_value):
    candidate = str(color_value or "").strip().lower()
    if not candidate:
        return None
    for token_name in PALETTE:
        for theme_palette in THEMES.values():
            theme_value = str(theme_palette.get(token_name, "")).strip().lower()
            if theme_value and theme_value == candidate:
                return token_name
    return None


def _map_theme_color(color_value, fallback_token=None):
    token_name = _palette_token_for_color(color_value)
    if token_name:
        return PALETTE[token_name]
    if fallback_token:
        return PALETTE[fallback_token]
    return color_value


def _apply_widget_theme_recursive(widget):
    try:
        if isinstance(widget, (tk.Tk, tk.Toplevel)):
            widget.configure(bg=PALETTE["blue_soft"])
        elif isinstance(widget, (tk.Frame, tk.LabelFrame)):
            current_bg = widget.cget("bg")
            widget.configure(bg=_map_theme_color(current_bg, "blue_soft"))
        elif isinstance(widget, tk.Canvas):
            widget.configure(
                bg=_map_theme_color(widget.cget("bg"), "surface_alt"),
                highlightbackground=PALETTE["gray_border"],
            )
        elif isinstance(widget, tk.Text):
            widget.configure(
                bg=PALETTE["white"],
                fg=PALETTE["black"],
                insertbackground=PALETTE["black"],
                highlightbackground=PALETTE["gray_border"],
            )
        elif isinstance(widget, tk.Entry):
            widget.configure(
                bg=PALETTE["white"],
                fg=PALETTE["black"],
                insertbackground=PALETTE["black"],
                highlightbackground=PALETTE["gray_border"],
            )
        elif isinstance(widget, tk.Label):
            parent_bg = widget.master.cget("bg") if widget.master else PALETTE["white"]
            widget.configure(
                bg=_map_theme_color(parent_bg, "white"),
                fg=_map_theme_color(widget.cget("fg"), "black"),
            )
        elif isinstance(widget, tk.Button):
            widget.configure(
                bg=_map_theme_color(widget.cget("bg"), "blue_primary"),
                fg=_map_theme_color(widget.cget("fg"), "white"),
                activebackground=PALETTE["blue_light"],
                activeforeground=PALETTE["black"],
            )
        elif isinstance(widget, (tk.Radiobutton, tk.Checkbutton)):
            parent_bg = widget.master.cget("bg") if widget.master else PALETTE["blue_soft"]
            widget.configure(
                bg=_map_theme_color(parent_bg, "blue_soft"),
                fg=_map_theme_color(widget.cget("fg"), "black"),
                activebackground=PALETTE["surface_alt"],
                activeforeground=PALETTE["black"],
                selectcolor=PALETTE["white"],
            )
    except tk.TclError:
        pass

    for child in widget.winfo_children():
        _apply_widget_theme_recursive(child)


def apply_app_theme(root, theme_name: str | None = None):
    active_theme = set_active_theme(theme_name)
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
        "TopbarTitle.TLabel",
        background=PALETTE["white"],
        foreground=PALETTE["blue_dark"],
        font=("Segoe UI Semibold", 11),
    )
    style.configure(
        "TopbarInfo.TLabel",
        background=PALETTE["white"],
        foreground=PALETTE["gray_text"],
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
        "Nav.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(12, 10),
        relief="flat",
        borderwidth=0,
        background=PALETTE["sidebar_bg"],
        foreground=PALETTE["sidebar_text"],
    )
    style.map(
        "Nav.TButton",
        background=[("active", PALETTE["surface_alt"])],
        foreground=[("active", PALETTE["blue_dark"])],
    )
    style.configure(
        "NavAccent.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(12, 10),
        relief="flat",
        borderwidth=0,
        background=PALETTE["blue_primary"],
        foreground=PALETTE["white"],
    )
    style.map("NavAccent.TButton", background=[("active", PALETTE["blue_light"])])
    style.configure(
        "TopbarNav.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(12, 7),
        relief="flat",
        borderwidth=1,
        bordercolor=PALETTE["gray_border"],
        background=PALETTE["white"],
        foreground=PALETTE["blue_dark"],
    )
    style.map(
        "TopbarNav.TButton",
        background=[("active", PALETTE["surface_alt"])],
        foreground=[("active", PALETTE["blue_primary"])],
        bordercolor=[("active", PALETTE["blue_primary"])],
    )
    style.configure(
        "TopbarNavAccent.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(12, 7),
        relief="flat",
        borderwidth=1,
        bordercolor=PALETTE["blue_primary"],
        background=PALETTE["blue_primary"],
        foreground=PALETTE["white"],
    )
    style.map(
        "TopbarNavAccent.TButton",
        background=[("active", "#1E40AF")],
        bordercolor=[("active", "#1E40AF")],
    )
    style.configure(
        "TopbarAction.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(10, 7),
        relief="flat",
        borderwidth=1,
        bordercolor=PALETTE["gray_border"],
        background=PALETTE["surface_alt"],
        foreground=PALETTE["blue_dark"],
    )
    style.map(
        "TopbarAction.TButton",
        background=[("active", PALETTE["blue_light"])],
        foreground=[("active", PALETTE["blue_dark"])],
        bordercolor=[("active", PALETTE["blue_primary"])],
    )
    style.configure(
        "TopbarDanger.TButton",
        font=("Segoe UI Semibold", 10),
        padding=(10, 7),
        relief="flat",
        borderwidth=1,
        bordercolor=PALETTE["danger"],
        background=PALETTE["white"],
        foreground=PALETTE["danger"],
    )
    style.map(
        "TopbarDanger.TButton",
        background=[("active", PALETTE["danger"])],
        foreground=[("active", PALETTE["white"])],
        bordercolor=[("active", PALETTE["danger"])],
    )

    style.configure(
        "TNotebook",
        background=PALETTE["blue_soft"],
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["blue_dark"],
        padding=(14, 8),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", PALETTE["white"]), ("active", PALETTE["blue_light"])],
        foreground=[("selected", PALETTE["black"])],
    )

    style.configure(
        "TRadiobutton",
        background=PALETTE["white"],
        foreground=PALETTE["black"],
        font=FONTS["body"],
    )
    style.configure(
        "TCheckbutton",
        background=PALETTE["white"],
        foreground=PALETTE["black"],
        font=FONTS["body"],
    )
    style.map(
        "TRadiobutton",
        background=[("active", PALETTE["white"])],
        foreground=[("active", PALETTE["blue_primary"])],
    )
    style.map(
        "TCheckbutton",
        background=[("active", PALETTE["white"])],
        foreground=[("active", PALETTE["blue_primary"])],
    )

    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=PALETTE["surface_alt"],
        background=PALETTE["success"],
        bordercolor=PALETTE["gray_border"],
        lightcolor=PALETTE["success"],
        darkcolor=PALETTE["success"],
    )

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

    try:
        root.configure(bg=PALETTE["blue_soft"])
    except tk.TclError:
        pass
    _apply_widget_theme_recursive(root)
    setattr(root, "_active_theme_name", active_theme)
    return style
