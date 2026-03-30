from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from database import DBManager
from erp.domain.entities.client import Client


class RepositoryError(RuntimeError):
    pass


@dataclass(slots=True)
class ClientRepository:
    db: DBManager

    def list_all(self, status: str = "todos") -> list[Client]:
        if status == "activos":
            where = "WHERE activo = 1"
        elif status == "inactivos":
            where = "WHERE activo = 0"
        else:
            where = ""

        rows = self.db.fetch(
            f"""
            SELECT id, nombre, apellido, dni, telefono, email, direccion, activo, COALESCE(mayorista, 0)
            FROM Clientes
            {where}
            ORDER BY apellido, nombre
            """
        )
        return [
            Client(
                id=int(row[0]),
                nombre=str(row[1]),
                apellido=str(row[2]),
                dni=row[3],
                telefono=row[4],
                email=row[5],
                direccion=row[6],
                activo=bool(row[7]),
                mayorista=bool(row[8]),
            )
            for row in rows
        ]

    def search(self, term: str) -> list[Client]:
        token = f"%{(term or '').strip().lower()}%"
        rows = self.db.fetch(
            """
            SELECT id, nombre, apellido, dni, telefono, email, direccion, activo, COALESCE(mayorista, 0)
            FROM Clientes
            WHERE LOWER(nombre) LIKE ?
               OR LOWER(apellido) LIKE ?
               OR LOWER(COALESCE(dni, '')) LIKE ?
               OR LOWER(COALESCE(telefono, '')) LIKE ?
               OR LOWER(COALESCE(email, '')) LIKE ?
            ORDER BY apellido, nombre
            """,
            (token, token, token, token, token),
        )
        return [
            Client(
                id=int(row[0]),
                nombre=str(row[1]),
                apellido=str(row[2]),
                dni=row[3],
                telefono=row[4],
                email=row[5],
                direccion=row[6],
                activo=bool(row[7]),
                mayorista=bool(row[8]),
            )
            for row in rows
        ]

    def save(self, client: Client) -> int:
        if client.id:
            self.db.execute(
                """
                UPDATE Clientes
                SET nombre=?, apellido=?, dni=?, telefono=?, email=?, direccion=?, activo=?, mayorista=?
                WHERE id=?
                """,
                (
                    client.nombre,
                    client.apellido,
                    client.dni,
                    client.telefono,
                    client.email,
                    client.direccion,
                    1 if client.activo else 0,
                    1 if client.mayorista else 0,
                    client.id,
                ),
            )
            if self.db.last_error:
                raise RepositoryError(str(self.db.last_error))
            return int(client.id)

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_id = self.db.execute(
            """
            INSERT INTO Clientes (nombre, apellido, dni, telefono, email, direccion, fecha_registro, activo, mayorista)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client.nombre,
                client.apellido,
                client.dni,
                client.telefono,
                client.email,
                client.direccion,
                created_at,
                1 if client.activo else 0,
                1 if client.mayorista else 0,
            ),
        )
        if self.db.last_error or new_id is None:
            raise RepositoryError(str(self.db.last_error or "No se pudo insertar cliente."))
        return int(new_id)

    def delete(self, client_id: int) -> None:
        self.db.execute("DELETE FROM Clientes WHERE id = ?", (client_id,))
        if self.db.last_error:
            raise RepositoryError(str(self.db.last_error))

    def has_sales(self, client_id: int) -> bool:
        rows = self.db.fetch("SELECT COUNT(*) FROM Ventas WHERE id_cliente = ?", (client_id,))
        if not rows:
            return False
        return int(rows[0][0]) > 0

    def deactivate(self, client_id: int) -> None:
        self.db.execute("UPDATE Clientes SET activo = 0 WHERE id = ?", (client_id,))
        if self.db.last_error:
            raise RepositoryError(str(self.db.last_error))
