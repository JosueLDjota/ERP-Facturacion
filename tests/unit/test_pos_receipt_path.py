import unittest
from pathlib import Path
import shutil
from unittest.mock import patch

from erp.domain.use_cases.receipt_use_case import ReceiptStorageService


class DummyDB:
    def __init__(self, receipt_path):
        self.receipt_path = receipt_path
        self.saved_values = []

    def get_config(self, key, default=None):
        if key == "recibo_save_path":
            return self.receipt_path
        return default

    def set_config(self, key, value):
        self.saved_values.append((key, value))
        if key == "recibo_save_path":
            self.receipt_path = value


class ReceiptStorageServiceTests(unittest.TestCase):
    def test_save_receipt_falls_back_to_default_dir_when_configured_path_is_denied(self):
        broken_dir = Path(r"C:\Users\elqui")
        temp_dir = Path("tests_runtime") / "receipt_path"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        fallback_dir = temp_dir / "Recibos"
        db = DummyDB(str(broken_dir))
        service = ReceiptStorageService(db)

        def fake_candidates(self):
            return [broken_dir, fallback_dir]

        def fake_write(self, output_dir, venta_id, html_content):
            if output_dir == broken_dir:
                raise PermissionError("[WinError 5] Acceso denegado")

            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / f"Recibo_{venta_id}.html"
            file_path.write_text(html_content, encoding="utf-8")
            return file_path

        with patch.object(ReceiptStorageService, "candidate_receipt_dirs", fake_candidates), patch.object(
            ReceiptStorageService,
            "write_receipt_file",
            fake_write,
        ):
            saved_path = service.save_receipt("<html>ok</html>", "VENTA-001")

        expected_path = fallback_dir / "Recibo_VENTA-001.html"
        self.assertEqual(saved_path, str(expected_path))
        self.assertTrue(expected_path.exists())
        self.assertEqual(db.saved_values, [("recibo_save_path", str(fallback_dir))])
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
