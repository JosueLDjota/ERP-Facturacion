from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from database import DBManager


logger = logging.getLogger(__name__)


class ReceiptStorageError(RuntimeError):
    pass


@dataclass(slots=True)
class ReceiptStorageService:
    db: DBManager

    def default_receipt_dir(self) -> Path:
        local_appdata = os.getenv("LOCALAPPDATA") or str(Path.home())
        return Path(local_appdata) / "ERP-Facturacion" / "Recibos"

    def candidate_receipt_dirs(self) -> list[Path]:
        configured_path = (self.db.get_config("recibo_save_path", "") or "").strip()
        candidates: list[Path] = []
        if configured_path:
            candidates.append(Path(configured_path).expanduser())

        fallback_dir = self.default_receipt_dir()
        if fallback_dir not in candidates:
            candidates.append(fallback_dir)
        return candidates

    def write_receipt_file(self, output_dir: Path, venta_id: str, html_content: str) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"Recibo_{venta_id}.html"
        file_path.write_text(html_content, encoding="utf-8")
        return file_path

    def save_receipt(self, html_content: str, venta_id: str) -> str:
        configured_path = (self.db.get_config("recibo_save_path", "") or "").strip()
        last_error: OSError | None = None

        for output_dir in self.candidate_receipt_dirs():
            try:
                file_path = self.write_receipt_file(output_dir, venta_id, html_content)
            except OSError as exc:
                logger.warning("No se pudo guardar recibo en '%s': %s", output_dir, exc)
                last_error = exc
                continue

            resolved_dir = str(output_dir)
            if resolved_dir != configured_path:
                self.db.set_config("recibo_save_path", resolved_dir)

            return str(file_path)

        raise ReceiptStorageError(
            "No se pudo guardar el recibo en la ruta configurada ni en la ruta local predeterminada."
        ) from last_error
