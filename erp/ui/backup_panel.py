from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from erp.data.repositories.backup_repository import BackupSettings
from erp.domain.services.backup_service import BackupService


class BackupSettingsPanel(ttk.Frame):
    FREQUENCY_LABELS = {
        "Diario al iniciar": "daily",
        "Al cerrar sesion o la app": "on_close",
        "Desactivado": "disabled",
    }

    TYPE_LABELS = {
        "manual": "Manual",
        "automatico": "Automático",
        "preventivo": "Preventivo",
        "restauracion": "Restauración",
    }

    STATUS_LABELS = {
        "exito": "Éxito",
        "error": "Error",
    }

    def __init__(self, parent, app, backup_service: BackupService):
        super().__init__(parent, padding=12, style="App.TFrame")
        self.app = app
        self.backup_service = backup_service

        settings = self.backup_service.repository.load_settings()
        self.destination_var = tk.StringVar(value=settings.destination_dir)
        self.frequency_var = tk.StringVar(value=self._label_from_frequency(settings.frequency))
        self.retention_var = tk.StringVar(value=str(settings.retention_count))
        self.alerts_enabled_var = tk.BooleanVar(value=settings.alerts_enabled)
        self.stale_days_var = tk.StringVar(value=str(settings.stale_days))
        self.status_var = tk.StringVar(value="")

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Respaldos del sistema", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text=(
                "Crea respaldos manuales, configura la automatizacion minima y revisa el historial local."
            ),
            style="Muted.TLabel",
            wraplength=860,
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        actions = ttk.LabelFrame(self, text="Acciones", style="Card.TLabelframe")
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)
        actions.columnconfigure(3, weight=1)

        self.create_backup_button = ttk.Button(
            actions,
            text="Crear respaldo ahora",
            style="Primary.TButton",
            command=self.create_manual_backup,
        )
        self.create_backup_button.grid(row=0, column=0, sticky="ew", padx=(8, 6), pady=10)

        ttk.Button(
            actions,
            text="Restaurar desde ZIP",
            style="Danger.TButton",
            command=self.restore_backup,
        ).grid(row=0, column=1, sticky="ew", padx=6, pady=10)

        ttk.Button(
            actions,
            text="Guardar configuracion",
            style="Secondary.TButton",
            command=self.save_settings,
        ).grid(row=0, column=2, sticky="ew", padx=6, pady=10)

        ttk.Button(
            actions,
            text="Actualizar historial",
            style="Secondary.TButton",
            command=self.refresh_all,
        ).grid(row=0, column=3, sticky="ew", padx=(6, 8), pady=10)

        history_frame = ttk.LabelFrame(self, text="Historial basico", style="Card.TLabelframe")
        history_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(1, weight=1)

        ttk.Label(
            history_frame,
            text="Se muestran los eventos recientes de respaldo y restauracion.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 8))

        columns = ("fecha", "tipo", "archivo", "estado", "mensaje")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=14)
        headings = {
            "fecha": "Fecha",
            "tipo": "Tipo",
            "archivo": "Archivo",
            "estado": "Estado",
            "mensaje": "Mensaje",
        }
        widths = {
            "fecha": 155,
            "tipo": 105,
            "archivo": 220,
            "estado": 90,
            "mensaje": 310,
        }
        for column in columns:
            self.history_tree.heading(column, text=headings[column])
            self.history_tree.column(column, width=widths[column], anchor="w")

        history_scroll = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)

        self.history_tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
        history_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 12))

        settings_frame = ttk.LabelFrame(self, text="Configuracion minima", style="Card.TLabelframe")
        settings_frame.grid(row=2, column=1, sticky="nsew")
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="Estado actual", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="nw", padx=12, pady=(12, 6)
        )
        ttk.Label(
            settings_frame,
            textvariable=self.status_var,
            style="Muted.TLabel",
            wraplength=360,
            justify="left",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 6))

        ttk.Label(settings_frame, text="Carpeta destino", style="FormLabel.TLabel").grid(
            row=1, column=0, sticky="w", padx=12, pady=6
        )
        destination_row = ttk.Frame(settings_frame, style="Surface.TFrame")
        destination_row.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)
        destination_row.columnconfigure(0, weight=1)
        ttk.Entry(destination_row, textvariable=self.destination_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(
            destination_row,
            text="Examinar",
            style="Secondary.TButton",
            command=self.select_destination_directory,
        ).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(settings_frame, text="Frecuencia automatica", style="FormLabel.TLabel").grid(
            row=2, column=0, sticky="w", padx=12, pady=6
        )
        ttk.Combobox(
            settings_frame,
            textvariable=self.frequency_var,
            values=list(self.FREQUENCY_LABELS.keys()),
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=6)

        ttk.Label(settings_frame, text="Maximo de respaldos por dia", style="FormLabel.TLabel").grid(
            row=3, column=0, sticky="w", padx=12, pady=6
        )
        ttk.Spinbox(settings_frame, from_=1, to=60, textvariable=self.retention_var, width=8).grid(
            row=3, column=1, sticky="w", padx=(0, 12), pady=6
        )

        ttk.Checkbutton(
            settings_frame,
            text="Activar alertas por respaldo desactualizado",
            variable=self.alerts_enabled_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=6)

        ttk.Label(settings_frame, text="Dias sin respaldo reciente", style="FormLabel.TLabel").grid(
            row=5, column=0, sticky="w", padx=12, pady=6
        )
        ttk.Spinbox(settings_frame, from_=1, to=30, textvariable=self.stale_days_var, width=8).grid(
            row=5, column=1, sticky="w", padx=(0, 12), pady=6
        )

        ttk.Label(
            settings_frame,
            text=(
                "La frecuencia diaria se ejecuta al iniciar. La opcion al cerrar intenta generar "
                "el respaldo cuando se cierra sesion o se cierra la aplicacion."
            ),
            style="Muted.TLabel",
            wraplength=360,
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 12))

    def focus_primary_action(self) -> None:
        self.create_backup_button.focus_set()

    def refresh_all(self) -> None:
        self.refresh_status()
        self.refresh_history()

    def refresh_status(self) -> None:
        alert_status = self.backup_service.get_alert_status()
        self.status_var.set(alert_status.message)

    def refresh_history(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for entry in self.backup_service.repository.list_history(limit=100):
            self.history_tree.insert(
                "",
                "end",
                values=(
                    entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    self.TYPE_LABELS.get(entry.backup_type, entry.backup_type.title()),
                    entry.file_name or entry.file_path,
                    self.STATUS_LABELS.get(entry.status, entry.status.title()),
                    entry.message,
                ),
            )

    def save_settings(self, *, show_success_message: bool = True) -> bool:
        try:
            settings = self._build_settings()
            normalized = self.backup_service.repository.save_settings(settings)
        except ValueError as exc:
            messagebox.showerror("Respaldos", str(exc), parent=self.winfo_toplevel())
            return False

        self.destination_var.set(normalized.destination_dir)
        self.frequency_var.set(self._label_from_frequency(normalized.frequency))
        self.retention_var.set(str(normalized.retention_count))
        self.alerts_enabled_var.set(normalized.alerts_enabled)
        self.stale_days_var.set(str(normalized.stale_days))
        self.refresh_status()
        if show_success_message:
            messagebox.showinfo(
                "Respaldos",
                "La configuracion de respaldos se guardo correctamente.",
                parent=self.winfo_toplevel(),
            )
        return True

    def create_manual_backup(self) -> None:
        if not self.save_settings(show_success_message=False):
            return

        result = self.backup_service.create_backup("manual")
        self.refresh_all()

        if result.ok:
            messagebox.showinfo(
                "Respaldos",
                f"Respaldo creado correctamente.\n\n{result.file_path}",
                parent=self.winfo_toplevel(),
            )
            return

        messagebox.showerror(
            "Respaldos",
            result.message,
            parent=self.winfo_toplevel(),
        )

    def restore_backup(self) -> None:
        backup_file = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Seleccionar respaldo ZIP",
            filetypes=[("Respaldos ZIP", "*.zip"), ("Todos los archivos", "*.*")],
        )
        if not backup_file:
            return

        if not messagebox.askyesno(
            "Confirmar restauracion",
            (
                "Se intentara restaurar la base de datos y los archivos respaldados.\n\n"
                "Si es posible, el sistema generara un respaldo preventivo antes de sobrescribir.\n"
                "Desea continuar?"
            ),
            parent=self.winfo_toplevel(),
        ):
            return

        current_role = None
        current_user = getattr(self.app, "current_user", None)
        if current_user and len(current_user) >= 3:
            current_role = current_user[2]

        result = self.backup_service.restore_backup(backup_file, actor_role=current_role)
        self.refresh_all()

        if result.ok:
            message = (
                f"{result.message}\n\n"
                "Se recomienda reabrir los modulos abiertos para recargar la informacion restaurada."
            )
            messagebox.showinfo("Restauracion", message, parent=self.winfo_toplevel())
            return

        messagebox.showerror("Restauracion", result.message, parent=self.winfo_toplevel())

    def select_destination_directory(self) -> None:
        selected_dir = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Seleccionar carpeta de respaldos",
            initialdir=self.destination_var.get() or os.getcwd(),
            mustexist=False,
        )
        if selected_dir:
            self.destination_var.set(selected_dir)

    def _build_settings(self) -> BackupSettings:
        destination_dir = self.destination_var.get().strip()
        if not destination_dir:
            raise ValueError("Indique una carpeta valida para guardar respaldos.")

        frequency_label = self.frequency_var.get().strip()
        frequency = self.FREQUENCY_LABELS.get(frequency_label)
        if not frequency:
            raise ValueError("Seleccione una frecuencia valida para los respaldos automaticos.")

        try:
            retention_count = int(self.retention_var.get().strip())
        except ValueError as exc:
            raise ValueError("El maximo de respaldos por dia debe ser numerico.") from exc
        if retention_count <= 0:
            raise ValueError("El maximo de respaldos por dia debe ser mayor que cero.")

        try:
            stale_days = int(self.stale_days_var.get().strip())
        except ValueError as exc:
            raise ValueError("Los dias de vigencia del respaldo deben ser numericos.") from exc
        if stale_days <= 0:
            raise ValueError("Los dias de vigencia del respaldo deben ser mayores que cero.")

        return BackupSettings(
            destination_dir=str(Path(destination_dir).expanduser()),
            frequency=frequency,
            retention_count=retention_count,
            alerts_enabled=bool(self.alerts_enabled_var.get()),
            stale_days=stale_days,
        )

    def _label_from_frequency(self, frequency: str) -> str:
        for label, value in self.FREQUENCY_LABELS.items():
            if value == frequency:
                return label
        return "Diario al iniciar"

