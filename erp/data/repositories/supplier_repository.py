from __future__ import annotations

# Contexto del archivo:
# Repositorio de proveedores utilizado por formularios de productos,
# importaciones y pantallas administrativas. Su funcion es encapsular catalogos
# y validaciones basicas de existencia sin exponer SQL a la capa visual.

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
            self.db.execute(
                "UPDATE Proveedores SET nombre=?, contacto=?, telefono=? WHERE id=?",
                (nombre, contacto, telefono, int(supplier_id)),
            )
            if self.db.last_error:
                raise RepositoryError(str(self.db.last_error))
            return int(supplier_id)

        new_id = self.db.execute(
            "INSERT INTO Proveedores (nombre, contacto, telefono) VALUES (?, ?, ?)",
            (nombre, contacto, telefono),
        )
        if self.db.last_error or new_id is None:
            raise RepositoryError(str(self.db.last_error or "No se pudo crear proveedor."))
        return int(new_id)

    def delete(self, supplier_id: int) -> None:
        self.db.execute("DELETE FROM Proveedores WHERE id=?", (supplier_id,))
        if self.db.last_error:
            raise RepositoryError(str(self.db.last_error))

    def list_choices(self) -> list[dict]:
        rows = self.db.fetch("SELECT id, nombre FROM Proveedores ORDER BY nombre")
        return [
            {"id": int(row[0]), "nombre": str(row[1] or "")}
            for row in rows
        ]

    def search_by_name(self, term: str = "", limit: int = 8) -> list[dict]:
        token = str(term or "").strip().lower()
        query = "SELECT id, nombre FROM Proveedores"
        params = []
        if token:
            query += " WHERE LOWER(nombre) LIKE ?"
            params.append(f"%{token}%")
        query += " ORDER BY nombre LIMIT ?"
        params.append(int(limit))
        rows = self.db.fetch(query, tuple(params))
        return [
            {"id": int(row[0]), "nombre": str(row[1] or "")}
            for row in rows
        ]

    def exists(self, supplier_id: int) -> bool:
        rows = self.db.fetch("SELECT 1 FROM Proveedores WHERE id = ? LIMIT 1", (int(supplier_id),))
        return bool(rows)
