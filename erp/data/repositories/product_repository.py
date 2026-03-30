from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from database import DBManager
from erp.domain.entities.product import Product


class RepositoryError(RuntimeError):
    pass


@dataclass(slots=True)
class ProductRepository:
    db: DBManager

    def list_all(self) -> list[Product]:
        rows = self.db.fetch(
            "SELECT id, nombre, descripcion, precio, stock, proveedor_id FROM Productos ORDER BY id DESC"
        )
        return [
            Product(
                id=int(row[0]),
                nombre=str(row[1]),
                descripcion=str(row[2] or ""),
                precio=float(row[3] or 0),
                stock=int(row[4] or 0),
                proveedor_id=int(row[5] or 0),
            )
            for row in rows
        ]

    def search_by_name(self, term: str) -> list[Product]:
        token = f"%{(term or '').strip().lower()}%"
        rows = self.db.fetch(
            "SELECT id, nombre, descripcion, precio, stock, proveedor_id FROM Productos WHERE LOWER(nombre) LIKE ? ORDER BY id DESC",
            (token,),
        )
        return [
            Product(
                id=int(row[0]),
                nombre=str(row[1]),
                descripcion=str(row[2] or ""),
                precio=float(row[3] or 0),
                stock=int(row[4] or 0),
                proveedor_id=int(row[5] or 0),
            )
            for row in rows
        ]

    def save(self, product: Product) -> int:
        if product.id:
            self.db.execute(
                """
                UPDATE Productos
                SET nombre=?, descripcion=?, precio=?, stock=?, proveedor_id=?
                WHERE id=?
                """,
                (
                    product.nombre,
                    product.descripcion,
                    product.precio,
                    product.stock,
                    product.proveedor_id,
                    product.id,
                ),
            )
            if self.db.last_error:
                raise RepositoryError(str(self.db.last_error))
            return int(product.id)

        new_id = self.db.execute(
            """
            INSERT INTO Productos (nombre, descripcion, precio, stock, proveedor_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product.nombre,
                product.descripcion,
                product.precio,
                product.stock,
                product.proveedor_id,
            ),
        )
        if self.db.last_error or new_id is None:
            raise RepositoryError(str(self.db.last_error or "No se pudo insertar producto."))
        return int(new_id)

    def delete(self, product_id: int) -> None:
        self.db.execute("DELETE FROM Productos WHERE id = ?", (product_id,))
        if self.db.last_error:
            raise RepositoryError(str(self.db.last_error))

    def import_many(self, products: Iterable[Product]) -> int:
        count = 0
        for product in products:
            self.save(product)
            count += 1
        return count
