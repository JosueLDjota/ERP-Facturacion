from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from database import DBManager
from erp.data.repositories.backup_repository import BackupRepository
from erp.domain.services.access_control import can_manage_backups


@dataclass(slots=True)
class BackupAlertStatus:
    should_alert: bool
    reason: str
    message: str
    last_backup_at: datetime | None = None
    days_since_last_backup: int | None = None


@dataclass(slots=True)
class BackupActionResult:
    ok: bool
    message: str
    backup_type: str
    file_path: str = ""
    created_at: datetime | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def file_name(self) -> str:
        return Path(self.file_path).name if self.file_path else ""


class BackupService:
    MANIFEST_NAME = "manifest.json"
    DATABASE_DIR = "database"
    RECEIPTS_DIR = "receipts"
    APP_DATA_DIR = "app_data"
    REQUIRED_TABLES = {"Configuracion", "Usuarios", "Productos", "Ventas"}
    WEEKDAY_FOLDERS = (
        "Lunes",
        "Martes",
        "Miercoles",
        "Jueves",
        "Viernes",
        "Sabado",
        "Domingo",
    )

    def __init__(self, db: DBManager, repository: BackupRepository | None = None):
        self.db = db
        self.repository = repository or BackupRepository(db)
        self.base_dir = self.db.db_path.parent.resolve()

    def create_backup(
        self,
        backup_type: str = "manual",
        *,
        destination_dir: str | Path | None = None,
        persist_history: bool = True,
    ) -> BackupActionResult:
        created_at = datetime.now()
        file_path = ""
        normalized_type = self._normalize_backup_type(backup_type)

        try:
            settings = self.repository.load_settings()
            base_dir = self._resolve_directory(destination_dir or settings.destination_dir)
            target_dir = self._resolve_backup_directory(base_dir, created_at)
            file_path = str(target_dir / self._build_backup_name(normalized_type, created_at))

            with tempfile.TemporaryDirectory() as temp_dir_name:
                temp_dir = Path(temp_dir_name)
                snapshot_path = temp_dir / self.db.db_path.name
                self._export_database_snapshot(snapshot_path)

                optional_dirs = list(self._collect_optional_directories())
                manifest = {
                    "schema_version": 1,
                    "created_at": created_at.isoformat(timespec="seconds"),
                    "backup_type": normalized_type,
                    "database_entry": f"{self.DATABASE_DIR}/{snapshot_path.name}",
                    "included_directories": [arc_root for arc_root, _source in optional_dirs],
                }

                with zipfile.ZipFile(file_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(self.MANIFEST_NAME, json.dumps(manifest, ensure_ascii=True, indent=2))
                    archive.write(snapshot_path, arcname=manifest["database_entry"])
                    for archive_root, source_dir in optional_dirs:
                        self._add_directory_to_zip(archive, source_dir, archive_root)

            self._apply_retention(target_dir, keep=settings.retention_count, created_at=created_at)

            if persist_history:
                self.repository.record_history(
                    backup_type=normalized_type,
                    file_path=file_path,
                    status="exito",
                    message="Respaldo generado correctamente.",
                    created_at=created_at,
                )
                self.repository.set_last_success_at(created_at)

            return BackupActionResult(
                ok=True,
                message="Respaldo generado correctamente.",
                backup_type=normalized_type,
                file_path=file_path,
                created_at=created_at,
            )
        except Exception as exc:
            error_message = self._friendly_error("crear el respaldo", exc)
            if persist_history:
                self.repository.record_history(
                    backup_type=normalized_type,
                    file_path=file_path,
                    status="error",
                    message=error_message,
                    created_at=created_at,
                )
            return BackupActionResult(
                ok=False,
                message=error_message,
                backup_type=normalized_type,
                file_path=file_path,
                created_at=created_at,
            )

    def restore_backup(self, backup_file: str | Path, *, actor_role: str | None = None) -> BackupActionResult:
        created_at = datetime.now()
        backup_path = Path(backup_file).expanduser()
        normalized_path = str(backup_path)
        preventive_backup: BackupActionResult | None = None

        try:
            if actor_role and not can_manage_backups(actor_role):
                raise PermissionError("Solo los usuarios autorizados pueden restaurar respaldos.")

            with tempfile.TemporaryDirectory() as temp_dir_name:
                temp_dir = Path(temp_dir_name)
                manifest, extracted_db_path = self._extract_backup(backup_path, temp_dir)
                self._validate_database_snapshot(extracted_db_path)

                preventive_backup = self.create_backup("preventivo", persist_history=False)
                warnings: list[str] = []
                if not preventive_backup.ok:
                    warnings.append(
                        "No se pudo crear el respaldo preventivo antes de restaurar."
                    )

                self._restore_database_snapshot(extracted_db_path)
                self.repository.ensure_schema()
                self._restore_optional_directories(temp_dir, manifest)

            if preventive_backup and preventive_backup.ok and preventive_backup.created_at:
                self.repository.record_history(
                    backup_type=preventive_backup.backup_type,
                    file_path=preventive_backup.file_path,
                    status="exito",
                    message="Respaldo preventivo generado antes de restaurar.",
                    created_at=preventive_backup.created_at,
                )
                self.repository.set_last_success_at(preventive_backup.created_at)

            restore_message = "Respaldo restaurado correctamente."
            if warnings:
                restore_message = f"{restore_message} {' '.join(warnings)}".strip()

            self.repository.record_history(
                backup_type="restauracion",
                file_path=normalized_path,
                status="exito",
                message=restore_message,
                created_at=created_at,
            )
            return BackupActionResult(
                ok=True,
                message=restore_message,
                backup_type="restauracion",
                file_path=normalized_path,
                created_at=created_at,
                warnings=tuple(warnings),
            )
        except Exception as exc:
            error_message = self._friendly_error("restaurar el respaldo", exc)
            if preventive_backup and preventive_backup.ok and preventive_backup.created_at:
                self.repository.record_history(
                    backup_type=preventive_backup.backup_type,
                    file_path=preventive_backup.file_path,
                    status="exito",
                    message="Respaldo preventivo generado antes de restaurar.",
                    created_at=preventive_backup.created_at,
                )
                self.repository.set_last_success_at(preventive_backup.created_at)
            self.repository.record_history(
                backup_type="restauracion",
                file_path=normalized_path,
                status="error",
                message=error_message,
                created_at=created_at,
            )
            return BackupActionResult(
                ok=False,
                message=error_message,
                backup_type="restauracion",
                file_path=normalized_path,
                created_at=created_at,
            )

    def get_alert_status(self, *, reference_time: datetime | None = None) -> BackupAlertStatus:
        settings = self.repository.load_settings()
        now = reference_time or datetime.now()
        last_backup = self.repository.get_last_successful_backup()

        if not settings.alerts_enabled:
            if last_backup is None:
                return BackupAlertStatus(
                    should_alert=False,
                    reason="disabled",
                    message="Las alertas de respaldo estan desactivadas.",
                )
            elapsed_days = max(0, (now.date() - last_backup.created_at.date()).days)
            return BackupAlertStatus(
                should_alert=False,
                reason="disabled",
                message=(
                    "Las alertas de respaldo estan desactivadas. "
                    f"Ultimo respaldo exitoso: {last_backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}."
                ),
                last_backup_at=last_backup.created_at,
                days_since_last_backup=elapsed_days,
            )

        if last_backup is None:
            return BackupAlertStatus(
                should_alert=True,
                reason="missing",
                message="No existe ningun respaldo registrado. Se recomienda crear uno ahora.",
            )

        elapsed_days = max(0, (now.date() - last_backup.created_at.date()).days)
        if elapsed_days >= settings.stale_days:
            return BackupAlertStatus(
                should_alert=True,
                reason="stale",
                message=(
                    f"El ultimo respaldo fue hace {elapsed_days} dias. "
                    "Se recomienda generar uno nuevo."
                ),
                last_backup_at=last_backup.created_at,
                days_since_last_backup=elapsed_days,
            )

        return BackupAlertStatus(
            should_alert=False,
            reason="fresh",
            message=(
                f"Ultimo respaldo exitoso: {last_backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}."
            ),
            last_backup_at=last_backup.created_at,
            days_since_last_backup=elapsed_days,
        )

    def run_automatic_backup_if_due(self, *, trigger: str) -> BackupActionResult | None:
        settings = self.repository.load_settings()
        normalized_trigger = str(trigger or "").strip().lower()

        if settings.frequency == "disabled":
            return None

        if settings.frequency == "daily":
            if normalized_trigger != "startup":
                return None
            last_backup = self.repository.get_last_successful_backup()
            if last_backup and last_backup.created_at.date() >= datetime.now().date():
                return None
            return self.create_backup("automatico")

        if settings.frequency == "on_close" and normalized_trigger in {"on_close", "logout"}:
            return self.create_backup("automatico")

        return None

    def _extract_backup(self, backup_path: Path, target_dir: Path) -> tuple[dict, Path]:
        if not backup_path.exists():
            raise FileNotFoundError("El archivo seleccionado no existe.")
        if backup_path.suffix.lower() != ".zip":
            raise ValueError("Seleccione un archivo .zip valido.")
        if not zipfile.is_zipfile(backup_path):
            raise zipfile.BadZipFile("El archivo seleccionado no es un ZIP valido.")

        with zipfile.ZipFile(backup_path, "r") as archive:
            if self.MANIFEST_NAME not in archive.namelist():
                raise ValueError("El respaldo no incluye la estructura esperada.")
            try:
                manifest = json.loads(archive.read(self.MANIFEST_NAME).decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError("El respaldo contiene un manifiesto invalido.") from exc

            database_entry = str(manifest.get("database_entry") or "").strip()
            if not database_entry or database_entry not in archive.namelist():
                raise ValueError("El respaldo no contiene la base de datos esperada.")

            archive.extractall(target_dir)

        extracted_db_path = target_dir / Path(database_entry)
        if not extracted_db_path.exists():
            raise ValueError("No se encontro la base de datos dentro del respaldo.")
        return manifest, extracted_db_path

    def _validate_database_snapshot(self, snapshot_path: Path) -> None:
        conn = None
        try:
            conn = sqlite3.connect(str(snapshot_path))
            tables = {
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        except sqlite3.Error as exc:
            raise ValueError("La base de datos del respaldo esta corrupta o no es valida.") from exc
        finally:
            if conn is not None:
                conn.close()

        missing_tables = sorted(self.REQUIRED_TABLES - tables)
        if missing_tables:
            raise ValueError(
                "El respaldo no contiene la estructura minima esperada: "
                + ", ".join(missing_tables)
            )

    def _export_database_snapshot(self, snapshot_path: Path) -> None:
        self.db.conn.commit()
        target_conn = sqlite3.connect(str(snapshot_path))
        try:
            self.db.conn.backup(target_conn)
            target_conn.commit()
        finally:
            target_conn.close()

    def _restore_database_snapshot(self, snapshot_path: Path) -> None:
        self.db.conn.commit()
        try:
            self.db.cursor.close()
        except Exception:
            pass
        source_conn = sqlite3.connect(str(snapshot_path))
        try:
            source_conn.backup(self.db.conn)
        finally:
            source_conn.close()
        self.db.conn.commit()
        self.db.cursor = self.db.conn.cursor()

    def _collect_optional_directories(self) -> list[tuple[str, Path]]:
        optional_dirs: list[tuple[str, Path]] = []

        receipts_dir = self._resolve_receipt_directory(create_if_missing=False)
        if receipts_dir and receipts_dir.exists() and receipts_dir.is_dir():
            optional_dirs.append((self.RECEIPTS_DIR, receipts_dir))

        app_data_dir = self.base_dir / "data"
        if app_data_dir.exists() and app_data_dir.is_dir():
            optional_dirs.append((self.APP_DATA_DIR, app_data_dir))

        return optional_dirs

    def _restore_optional_directories(self, extracted_root: Path, manifest: dict) -> None:
        included_directories = set(manifest.get("included_directories") or [])

        if self.RECEIPTS_DIR in included_directories:
            extracted_receipts = extracted_root / self.RECEIPTS_DIR
            if extracted_receipts.exists():
                target_receipts = self._resolve_receipt_directory(create_if_missing=True)
                if target_receipts is None:
                    raise ValueError("No se pudo resolver la carpeta de recibos restaurados.")
                shutil.copytree(extracted_receipts, target_receipts, dirs_exist_ok=True)

        if self.APP_DATA_DIR in included_directories:
            extracted_app_data = extracted_root / self.APP_DATA_DIR
            if extracted_app_data.exists():
                target_app_data = self.base_dir / "data"
                target_app_data.mkdir(parents=True, exist_ok=True)
                shutil.copytree(extracted_app_data, target_app_data, dirs_exist_ok=True)

    def _resolve_receipt_directory(self, *, create_if_missing: bool) -> Path | None:
        configured = str(self.db.get_config("recibo_save_path", "") or "").strip()
        if not configured:
            return None

        receipt_dir = Path(configured).expanduser()
        if not receipt_dir.is_absolute():
            receipt_dir = (self.base_dir / receipt_dir).resolve()

        if create_if_missing:
            receipt_dir.mkdir(parents=True, exist_ok=True)
        return receipt_dir

    def _resolve_directory(self, raw_path: str | Path) -> Path:
        if not str(raw_path or "").strip():
            raise ValueError("Configure una carpeta valida para guardar los respaldos.")

        target_dir = Path(raw_path).expanduser()
        if not target_dir.is_absolute():
            target_dir = (self.base_dir / target_dir).resolve()

        if target_dir.exists() and not target_dir.is_dir():
            raise ValueError("La ruta configurada no corresponde a una carpeta.")

        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def _resolve_backup_directory(self, base_dir: Path, created_at: datetime) -> Path:
        self._ensure_weekday_directories(base_dir)
        weekday_dir = base_dir / self.WEEKDAY_FOLDERS[created_at.weekday()]
        weekday_dir.mkdir(parents=True, exist_ok=True)
        return weekday_dir

    def _ensure_weekday_directories(self, base_dir: Path) -> None:
        for folder_name in self.WEEKDAY_FOLDERS:
            (base_dir / folder_name).mkdir(parents=True, exist_ok=True)

    def _add_directory_to_zip(self, archive: zipfile.ZipFile, source_dir: Path, archive_root: str) -> None:
        for file_path in sorted(source_dir.rglob("*")):
            if not file_path.is_file():
                continue
            relative_path = file_path.relative_to(source_dir).as_posix()
            archive.write(file_path, arcname=f"{archive_root}/{relative_path}")

    def _apply_retention(self, target_dir: Path, *, keep: int, created_at: datetime) -> None:
        keep = max(1, int(keep or 1))
        date_token = created_at.strftime("%Y-%m-%d")
        backup_files = [
            path
            for path in target_dir.iterdir()
            if (
                path.is_file()
                and path.suffix.lower() == ".zip"
                and path.name.startswith("backup_erp_")
                and date_token in path.name
            )
        ]
        backup_files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        for obsolete_path in backup_files[keep:]:
            obsolete_path.unlink(missing_ok=True)

    def _build_backup_name(self, backup_type: str, created_at: datetime) -> str:
        timestamp = created_at.strftime("%Y-%m-%d_%H-%M-%S")
        if backup_type == "manual":
            return f"backup_erp_{timestamp}.zip"
        suffix = {
            "automatico": "auto",
            "preventivo": "preventivo",
            "restauracion": "restauracion",
        }.get(backup_type, backup_type)
        return f"backup_erp_{suffix}_{timestamp}.zip"

    def _normalize_backup_type(self, backup_type: str) -> str:
        normalized = str(backup_type or "").strip().lower()
        if normalized in {"manual", "automatico", "preventivo", "restauracion"}:
            return normalized
        return "manual"

    def _friendly_error(self, action: str, exc: Exception) -> str:
        if isinstance(exc, PermissionError):
            return str(exc) or f"No tiene permisos suficientes para {action}."
        if isinstance(exc, FileNotFoundError):
            return str(exc) or f"No se encontro la ruta necesaria para {action}."
        if isinstance(exc, zipfile.BadZipFile):
            return "El archivo seleccionado no es un respaldo ZIP valido."
        if isinstance(exc, sqlite3.Error):
            return f"Ocurrio un error con la base de datos al {action}: {exc}"
        if isinstance(exc, ValueError):
            return str(exc)
        return f"No se pudo {action}: {exc}"
