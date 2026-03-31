from __future__ import annotations

from dataclasses import dataclass

from database import DBManager


class RepositoryError(RuntimeError):
    pass


@dataclass(slots=True)
class SupplierRepository:
    db: DBManager

    def list_all(self) -> list[tuple[int, str, str, str]]:
        rows = self.db.fetch(
            "SELECT id, nombre, contacto, telefono FROM Proveedores ORDER BY id DESC"
        )
        return [
            (int(row[0]), str(row[1] or ""), str(row[2] or ""), str(row[3] or ""))
            for row in rows
        ]

    def save(self, supplier_id: str | None, nombre: str, contacto: str, telefono: str) -> int:
        if supplier_id:
            self.db.execute_checked(
                "UPDATE Proveedores SET nombre=?, contacto=?, telefono=? WHERE id=?",
                (nombre, contacto, telefono, int(supplier_id)),
            )
            return int(supplier_id)

        new_id = self.db.execute_checked(
            "INSERT INTO Proveedores (nombre, contacto, telefono) VALUES (?, ?, ?)",
            (nombre, contacto, telefono),
        )
        if new_id is None:
            raise RepositoryError("No se pudo crear proveedor.")
        return int(new_id)

    def delete(self, supplier_id: int) -> None:
        self.db.execute_checked("DELETE FROM Proveedores WHERE id=?", (supplier_id,))
