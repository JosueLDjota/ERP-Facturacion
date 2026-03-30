import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from frames.sales import UnifiedPOSFrame


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


class POSReceiptPathTests(unittest.TestCase):
    def test_save_receipt_falls_back_to_default_dir_when_configured_path_is_denied(self):
        frame = object.__new__(UnifiedPOSFrame)
        frame.db = DummyDB(r"C:\Users\elqui")

        broken_dir = Path(r"C:\Users\elqui")

        with tempfile.TemporaryDirectory() as temp_dir:
            fallback_dir = Path(temp_dir) / "Recibos"

            def fake_write(output_dir, venta_id, html_content):
                if output_dir == broken_dir:
                    raise PermissionError("[WinError 5] Acceso denegado")

                output_dir.mkdir(parents=True, exist_ok=True)
                file_path = output_dir / f"Recibo_{venta_id}.html"
                file_path.write_text(html_content, encoding="utf-8")
                return file_path

            with patch.object(
                UnifiedPOSFrame,
                "_candidate_receipt_dirs",
                return_value=[broken_dir, fallback_dir],
            ), patch.object(UnifiedPOSFrame, "_write_receipt_file", side_effect=fake_write):
                saved_path = UnifiedPOSFrame.save_receipt(frame, "<html>ok</html>", "VENTA-001")

            expected_path = fallback_dir / "Recibo_VENTA-001.html"
            self.assertEqual(saved_path, str(expected_path))
            self.assertEqual(frame.last_receipt_path, str(expected_path))
            self.assertTrue(expected_path.exists())
            self.assertEqual(frame.db.saved_values, [("recibo_save_path", str(fallback_dir))])


if __name__ == "__main__":
    unittest.main()
