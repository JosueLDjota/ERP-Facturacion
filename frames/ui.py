"""
frames/ui.py
Sistema visual compartido para la UI del ERP.
"""

from pathlib import Path
import tkinter as tk
from tkinter import ttk


PALETTE = {
    "blue_dark": "#123A6B",
    "blue_primary": "#1F5EA8",
    "blue_light": "#DDEBFF",
    "blue_soft": "#EDF4FF",
    "white": "#FFFFFF",
    "black": "#111827",
    "gray_text": "#4B5563",
    "gray_border": "#D0D7E2",
    "danger": "#B42318",
    "success": "#067647",
}

FONTS = {
    "family": "Segoe UI",
    "base": ("Segoe UI", 10),
    "body": ("Segoe UI", 11),
    "title": ("Segoe UI", 22, "bold"),
    "header": ("Segoe UI", 17, "bold"),
    "subheader": ("Segoe UI", 13, "bold"),
    "small": ("Segoe UI", 9),
}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


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

    style.configure(
        "Header.TLabel",
        background=PALETTE["blue_soft"],
        foreground=PALETTE["blue_dark"],
        font=FONTS["header"],
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
        "TLabel",
        background=PALETTE["blue_soft"],
        foreground=PALETTE["black"],
        font=FONTS["body"],
    )

    style.configure(
        "Card.TLabelframe",
        background=PALETTE["white"],
        bordercolor=PALETTE["gray_border"],
        relief="solid",
        borderwidth=1,
        padding=12,
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
        lightcolor=PALETTE["blue_light"],
        darkcolor=PALETTE["gray_border"],
        insertcolor=PALETTE["black"],
        padding=8,
    )
    style.map("TEntry", bordercolor=[("focus", PALETTE["blue_primary"])])

    style.configure(
        "TCombobox",
        fieldbackground=PALETTE["white"],
        foreground=PALETTE["black"],
        bordercolor=PALETTE["gray_border"],
        lightcolor=PALETTE["blue_light"],
        darkcolor=PALETTE["gray_border"],
        padding=7,
    )
    style.map("TCombobox", bordercolor=[("focus", PALETTE["blue_primary"])])

    style.configure(
        "Primary.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(14, 8),
        relief="flat",
        borderwidth=0,
        background=PALETTE["blue_primary"],
        foreground=PALETTE["white"],
    )
    style.map("Primary.TButton", background=[("active", PALETTE["blue_dark"])])

    style.configure(
        "Secondary.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(14, 8),
        relief="flat",
        borderwidth=0,
        background=PALETTE["blue_light"],
        foreground=PALETTE["blue_dark"],
    )
    style.map("Secondary.TButton", background=[("active", "#C9DFFF")])

    style.configure(
        "Danger.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(14, 8),
        relief="flat",
        borderwidth=0,
        background=PALETTE["danger"],
        foreground=PALETTE["white"],
    )
    style.map("Danger.TButton", background=[("active", "#8F1C13")])

    style.configure(
        "Success.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(14, 8),
        relief="flat",
        borderwidth=0,
        background=PALETTE["success"],
        foreground=PALETTE["white"],
    )
    style.map("Success.TButton", background=[("active", "#055A3B")])

    style.configure(
        "Nav.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(12, 10),
        relief="flat",
        borderwidth=0,
        background=PALETTE["blue_soft"],
        foreground=PALETTE["blue_dark"],
    )
    style.map("Nav.TButton", background=[("active", PALETTE["blue_light"])])

    style.configure(
        "NavAccent.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(12, 10),
        relief="flat",
        borderwidth=0,
        background=PALETTE["blue_primary"],
        foreground=PALETTE["white"],
    )
    style.map("NavAccent.TButton", background=[("active", PALETTE["blue_dark"])])

    style.configure(
        "Treeview",
        background=PALETTE["white"],
        fieldbackground=PALETTE["white"],
        foreground=PALETTE["black"],
        rowheight=30,
        bordercolor=PALETTE["gray_border"],
    )
    style.configure(
        "Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        background=PALETTE["blue_light"],
        foreground=PALETTE["blue_dark"],
        relief="flat",
    )
    style.map("Treeview", background=[("selected", "#CDE0FF")], foreground=[("selected", PALETTE["black"])])

    style.configure("TNotebook", background=PALETTE["blue_soft"], borderwidth=0)
    style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(12, 7))
    style.map(
        "TNotebook.Tab",
        background=[("selected", PALETTE["white"]), ("!selected", PALETTE["blue_light"])],
        foreground=[("selected", PALETTE["blue_dark"]), ("!selected", PALETTE["gray_text"])],
    )

    root.configure(bg=PALETTE["blue_soft"])
    return style
