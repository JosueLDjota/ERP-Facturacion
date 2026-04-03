from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from database import DBManager


@dataclass(slots=True)
class BackupSettings:
    destination_dir: str
    frequency: str = "daily"
    retention_count: int = 7
    alerts_enabled: bool = True
    stale_days: int = 3


@dataclass(slots=True)
class BackupHistoryEntry:
    created_at: datetime
    backup_type: str
    file_name: str
    file_path: str
    status: str
    message: str


@dataclass(slots=True)
class BackupRepository:
    db: DBManager

    DESTINATION_KEY = "backup_destination_dir"
    FREQUENCY_KEY = "backup_frequency"
    RETENTION_KEY = "backup_retention_count"
    ALERTS_ENABLED_KEY = "backup_alerts_enabled"
    STALE_DAYS_KEY = "backup_stale_days"
    LAST_SUCCESS_KEY = "backup_last_success_at"

    def __post_init__(self) -> None:
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS HistorialRespaldos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,
                archivo_nombre TEXT,
                archivo_ruta TEXT,
                estado TEXT NOT NULL,
                mensaje TEXT
            )
            """
        )
        self.db.conn.commit()

    def load_settings(self) -> BackupSettings:
        default_dir = str((self.db.db_path.parent / "backups").resolve())
        destination_dir = str(self.db.get_config(self.DESTINATION_KEY, default_dir) or default_dir)
        frequency = self._normalize_frequency(self.db.get_config(self.FREQUENCY_KEY, "daily"))
        retention_count = self._parse_positive_int(self.db.get_config(self.RETENTION_KEY, "7"), fallback=7)
        alerts_enabled = self._parse_bool(self.db.get_config(self.ALERTS_ENABLED_KEY, "1"), fallback=True)
        stale_days = self._parse_positive_int(self.db.get_config(self.STALE_DAYS_KEY, "3"), fallback=3)
        return BackupSettings(
            destination_dir=destination_dir,
            frequency=frequency,
            retention_count=retention_count,
            alerts_enabled=alerts_enabled,
            stale_days=stale_days,
        )

    def save_settings(self, settings: BackupSettings) -> BackupSettings:
        normalized = BackupSettings(
            destination_dir=str(settings.destination_dir or (self.db.db_path.parent / "backups")),
            frequency=self._normalize_frequency(settings.frequency),
            retention_count=max(1, int(settings.retention_count or 7)),
            alerts_enabled=bool(settings.alerts_enabled),
            stale_days=max(1, int(settings.stale_days or 3)),
        )
        self.db.set_config(self.DESTINATION_KEY, normalized.destination_dir)
        self.db.set_config(self.FREQUENCY_KEY, normalized.frequency)
        self.db.set_config(self.RETENTION_KEY, str(normalized.retention_count))
        self.db.set_config(self.ALERTS_ENABLED_KEY, "1" if normalized.alerts_enabled else "0")
        self.db.set_config(self.STALE_DAYS_KEY, str(normalized.stale_days))
        return normalized

    def list_history(self, limit: int = 50) -> list[BackupHistoryEntry]:
        rows = self.db.fetch(
            """
            SELECT fecha, tipo, archivo_nombre, archivo_ruta, estado, mensaje
            FROM HistorialRespaldos
            ORDER BY fecha DESC, id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [self._row_to_entry(row) for row in rows]

    def record_history(
        self,
        *,
        backup_type: str,
        file_path: str = "",
        status: str = "exito",
        message: str = "",
        created_at: datetime | None = None,
    ) -> BackupHistoryEntry:
        created_at = created_at or datetime.now()
        file_name = Path(file_path).name if file_path else ""
        self.db.execute(
            """
            INSERT INTO HistorialRespaldos (fecha, tipo, archivo_nombre, archivo_ruta, estado, mensaje)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                created_at.isoformat(timespec="seconds"),
                str(backup_type or "").strip() or "manual",
                file_name,
                str(file_path or ""),
                str(status or "exito"),
                str(message or ""),
            ),
        )
        return BackupHistoryEntry(
            created_at=created_at,
            backup_type=str(backup_type or "").strip() or "manual",
            file_name=file_name,
            file_path=str(file_path or ""),
            status=str(status or "exito"),
            message=str(message or ""),
        )

    def get_last_successful_backup(self) -> BackupHistoryEntry | None:
        rows = self.db.fetch(
            """
            SELECT fecha, tipo, archivo_nombre, archivo_ruta, estado, mensaje
            FROM HistorialRespaldos
            WHERE estado = 'exito' AND tipo IN ('manual', 'automatico', 'preventivo')
            ORDER BY fecha DESC, id DESC
            LIMIT 1
            """
        )
        if not rows:
            return None
        return self._row_to_entry(rows[0])

    def set_last_success_at(self, created_at: datetime) -> None:
        self.db.set_config(self.LAST_SUCCESS_KEY, created_at.isoformat(timespec="seconds"))

    def get_last_success_at(self) -> datetime | None:
        value = self.db.get_config(self.LAST_SUCCESS_KEY, "")
        if not value:
            entry = self.get_last_successful_backup()
            return entry.created_at if entry else None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            entry = self.get_last_successful_backup()
            return entry.created_at if entry else None

    def _row_to_entry(self, row: tuple) -> BackupHistoryEntry:
        created_at = datetime.fromisoformat(str(row[0]))
        return BackupHistoryEntry(
            created_at=created_at,
            backup_type=str(row[1] or ""),
            file_name=str(row[2] or ""),
            file_path=str(row[3] or ""),
            status=str(row[4] or ""),
            message=str(row[5] or ""),
        )

    def _normalize_frequency(self, value: str | None) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"daily", "disabled", "on_close"}:
            return normalized
        return "daily"

    def _parse_bool(self, value: str | None, *, fallback: bool) -> bool:
        normalized = str(value or "").strip().lower()
        if normalized in {"1", "true", "yes", "si", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return fallback

    def _parse_positive_int(self, value: str | None, *, fallback: int) -> int:
        try:
            parsed = int(str(value or "").strip())
        except (TypeError, ValueError):
            return fallback
        return parsed if parsed > 0 else fallback
