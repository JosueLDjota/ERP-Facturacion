import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import zipfile

from database import DBManager
from erp.data.repositories.backup_repository import BackupRepository, BackupSettings
from erp.domain.services.backup_service import BackupService


class BackupServiceTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.db_path = self.root / "erp_backup_test.db"
        self.db = DBManager(str(self.db_path))
        self.repository = BackupRepository(self.db)
        self.service = BackupService(self.db, self.repository)

        self.receipts_dir = self.root / "receipts"
        self.receipts_dir.mkdir()
        (self.receipts_dir / "ticket_demo.txt").write_text("recibo", encoding="utf-8")
        self.db.set_config("recibo_save_path", str(self.receipts_dir))

        self.data_dir = self.root / "data"
        self.data_dir.mkdir()
        (self.data_dir / "notifications_state.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.db.close()
        self._temp_dir.cleanup()

    def test_create_manual_backup_successfully_and_record_history(self):
        result = self.service.create_backup("manual")

        self.assertTrue(result.ok)
        self.assertTrue(Path(result.file_path).exists())

        with zipfile.ZipFile(result.file_path, "r") as archive:
            names = set(archive.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn(f"database/{self.db_path.name}", names)
            self.assertIn("receipts/ticket_demo.txt", names)

        history = self.repository.list_history(limit=10)
        self.assertEqual(history[0].backup_type, "manual")
        self.assertEqual(history[0].status, "exito")
        self.assertIsNotNone(self.repository.get_last_success_at())

    def test_create_backup_uses_weekday_folder_structure(self):
        frozen_now = datetime(2026, 4, 6, 9, 30, 0)  # Lunes
        with patch("erp.domain.services.backup_service.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = frozen_now
            mocked_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            result = self.service.create_backup("manual")

        self.assertTrue(result.ok)
        backup_path = Path(result.file_path)
        self.assertEqual(backup_path.parent.name, "Lunes")
        for folder_name in self.service.WEEKDAY_FOLDERS:
            self.assertTrue((self.root / "backups" / folder_name).is_dir())

    def test_retention_keeps_only_latest_backups_for_the_same_day(self):
        target_root = self.root / "weekly_backups"
        self.repository.save_settings(
            BackupSettings(
                destination_dir=str(target_root),
                frequency="daily",
                retention_count=2,
                alerts_enabled=True,
                stale_days=3,
            )
        )

        monday_times = (
            datetime(2026, 4, 6, 8, 0, 0),
            datetime(2026, 4, 6, 9, 0, 0),
            datetime(2026, 4, 6, 10, 0, 0),
        )
        for frozen_now in monday_times:
            with patch("erp.domain.services.backup_service.datetime") as mocked_datetime:
                mocked_datetime.now.return_value = frozen_now
                mocked_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                result = self.service.create_backup("automatico")
                self.assertTrue(result.ok)

        next_monday = datetime(2026, 4, 13, 8, 0, 0)
        with patch("erp.domain.services.backup_service.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = next_monday
            mocked_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            result = self.service.create_backup("automatico")
            self.assertTrue(result.ok)

        monday_dir = target_root / "Lunes"
        monday_backups = sorted(monday_dir.glob("backup_erp_*.zip"))
        same_day_backups = [path for path in monday_backups if "2026-04-06" in path.name]
        self.assertEqual(len(same_day_backups), 2)
        self.assertEqual(len([path for path in monday_backups if "2026-04-13" in path.name]), 1)
        self.assertTrue((target_root / "Martes").is_dir())
        self.assertEqual(list((target_root / "Martes").glob("backup_erp_*.zip")), [])

    def test_on_close_frequency_runs_when_user_logs_out(self):
        self.repository.save_settings(
            BackupSettings(
                destination_dir=str(self.root / "logout_backups"),
                frequency="on_close",
                retention_count=2,
                alerts_enabled=True,
                stale_days=3,
            )
        )

        result = self.service.run_automatic_backup_if_due(trigger="logout")

        self.assertIsNotNone(result)
        self.assertTrue(result.ok)
        self.assertEqual(result.backup_type, "automatico")
        self.assertTrue(Path(result.file_path).exists())

    def test_recent_backup_does_not_trigger_alert(self):
        result = self.service.create_backup("manual")

        status = self.service.get_alert_status(
            reference_time=result.created_at + timedelta(days=1)
        )

        self.assertFalse(status.should_alert)
        self.assertEqual(status.reason, "fresh")

    def test_no_backups_triggers_missing_alert(self):
        status = self.service.get_alert_status()

        self.assertTrue(status.should_alert)
        self.assertEqual(status.reason, "missing")
        self.assertIn("No existe ningun respaldo registrado", status.message)

    def test_stale_backup_triggers_alert(self):
        result = self.service.create_backup("manual")

        status = self.service.get_alert_status(
            reference_time=result.created_at + timedelta(days=5)
        )

        self.assertTrue(status.should_alert)
        self.assertEqual(status.reason, "stale")
        self.assertIn("hace 5 dias", status.message)

    def test_restore_valid_backup(self):
        self.db.set_config("empresa_nombre", "ANTES")
        backup = self.service.create_backup("manual")
        self.db.set_config("empresa_nombre", "DESPUES")

        result = self.service.restore_backup(backup.file_path, actor_role="Administrador")

        self.assertTrue(result.ok)
        self.assertEqual(self.db.get_config("empresa_nombre"), "ANTES")
        history_types = [entry.backup_type for entry in self.repository.list_history(limit=10)]
        self.assertIn("restauracion", history_types)

    def test_invalid_destination_path_returns_error(self):
        invalid_target = self.root / "ruta_invalida.txt"
        invalid_target.write_text("no_es_carpeta", encoding="utf-8")
        self.repository.save_settings(
            BackupSettings(
                destination_dir=str(invalid_target),
                frequency="daily",
                retention_count=7,
                alerts_enabled=True,
                stale_days=3,
            )
        )

        result = self.service.create_backup("manual")

        self.assertFalse(result.ok)
        self.assertIn("no corresponde a una carpeta", result.message.lower())

    def test_compression_failure_returns_error(self):
        with patch(
            "erp.domain.services.backup_service.zipfile.ZipFile.writestr",
            side_effect=OSError("fallo de compresion"),
        ):
            result = self.service.create_backup("manual")

        self.assertFalse(result.ok)
        self.assertIn("fallo de compresion", result.message.lower())

    def test_invalid_zip_restore_returns_error(self):
        invalid_zip = self.root / "invalido.zip"
        invalid_zip.write_text("esto no es un zip", encoding="utf-8")

        result = self.service.restore_backup(invalid_zip, actor_role="Administrador")

        self.assertFalse(result.ok)
        self.assertIn("zip valido", result.message.lower())


if __name__ == "__main__":
    unittest.main()
