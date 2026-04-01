from __future__ import annotations

# Contexto del archivo:
# Repositorio principal de productos. Centraliza lecturas, busquedas, detalle,
# exportacion, importacion por lote y ajustes masivos de precios para evitar
# que la UI manipule SQL directo sobre `Productos`.

from dataclasses import dataclass
from typing import Iterable

from database import DBManager
from erp.domain.entities.product import Product


class RepositoryError(RuntimeError):
    pass


@dataclass(slots=True)
class ProductRepository:
    db: DBManager

    @staticmethod
    def _optional_int(value) -> int | None:
        return int(value) if value is not None else None

    def _row_to_product(self, row) -> Product:
        return Product(
            id=int(row[0]),
            nombre=str(row[1]),
            descripcion=str(row[2] or ""),
            precio=float(row[3] or 0),
            stock=int(row[4] or 0),
            proveedor_id=int(row[5] or 0),
            codigo_producto=str(row[6] or "") or None,
            categoria_id=self._optional_int(row[7]),
            marca_id=self._optional_int(row[8]),
        )

    def list_all(self) -> list[Product]:
        rows = self.db.fetch(
            """
            SELECT
                id,
                nombre,
                descripcion,
                precio,
                stock,
                proveedor_id,
                COALESCE(codigo_producto, ''),
                categoria_id,
                marca_id
            FROM Productos
            ORDER BY id DESC
            """
        )
        return [self._row_to_product(row) for row in rows]

    def search_by_name(self, term: str) -> list[Product]:
        token = f"%{(term or '').strip().lower()}%"
        rows = self.db.fetch(
            """
            SELECT
                id,
                nombre,
                descripcion,
                precio,
                stock,
                proveedor_id,
                COALESCE(codigo_producto, ''),
                categoria_id,
                marca_id
            FROM Productos
            WHERE LOWER(nombre) LIKE ?
               OR LOWER(COALESCE(codigo_producto, '')) LIKE ?
            ORDER BY id DESC
            """,
            (token, token),
        )
        return [self._row_to_product(row) for row in rows]

    def list_for_ui(self, search_term: str = "") -> list[dict]:
        token = str(search_term or "").strip().lower()
        query = """
            SELECT
                p.id,
                p.nombre,
                p.precio,
                p.stock,
                COALESCE(pr.nombre, 'Sin proveedor') AS proveedor_nombre,
                COALESCE(p.codigo_producto, '') AS codigo_producto,
                COALESCE(c.nombre, 'Sin categoria') AS categoria_nombre,
                COALESCE(m.nombre, 'Sin marca') AS marca_nombre
            FROM Productos p
            LEFT JOIN Proveedores pr ON pr.id = p.proveedor_id
            LEFT JOIN Categorias c ON c.id = p.categoria_id
            LEFT JOIN Marcas m ON m.id = p.marca_id
        """
        params = ()
        if token:
            query += """
                WHERE LOWER(p.nombre) LIKE ?
                   OR LOWER(COALESCE(p.codigo_producto, '')) LIKE ?
                   OR LOWER(COALESCE(c.nombre, '')) LIKE ?
                   OR LOWER(COALESCE(m.nombre, '')) LIKE ?
            """
            params = (f"%{token}%", f"%{token}%", f"%{token}%", f"%{token}%")
        query += " ORDER BY p.id DESC"
        rows = self.db.fetch(query, params)
        return [
            {
                "id": int(row[0]),
                "nombre": str(row[1] or ""),
                "precio": float(row[2] or 0),
                "stock": int(row[3] or 0),
                "proveedor_nombre": str(row[4] or "Sin proveedor"),
                "codigo_producto": str(row[5] or ""),
                "categoria_nombre": str(row[6] or "Sin categoria"),
                "marca_nombre": str(row[7] or "Sin marca"),
            }
            for row in rows
        ]

    def get_detail(self, product_id: int) -> dict | None:
        rows = self.db.fetch(
            """
            SELECT
                id,
                nombre,
                precio,
                stock,
                descripcion,
                proveedor_id,
                COALESCE(codigo_producto, ''),
                categoria_id,
                marca_id
            FROM Productos
            WHERE id = ?
            LIMIT 1
            """,
            (int(product_id),),
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "id": int(row[0]),
            "nombre": str(row[1] or ""),
            "precio": float(row[2] or 0),
            "stock": int(row[3] or 0),
            "descripcion": str(row[4] or ""),
            "proveedor_id": int(row[5] or 0),
            "codigo_producto": str(row[6] or ""),
            "categoria_id": self._optional_int(row[7]),
            "marca_id": self._optional_int(row[8]),
        }

    def export_rows(self) -> list[tuple]:
        return self.db.fetch(
            """
            SELECT id, nombre, descripcion, precio, stock, proveedor_id, COALESCE(codigo_producto, '')
            FROM Productos
            ORDER BY id
            """
        )

    def codigo_exists(self, codigo_producto: str, exclude_product_id: int | None = None) -> bool:
        codigo_producto = str(codigo_producto or "").strip()
        if not codigo_producto:
            return False
        query = "SELECT 1 FROM Productos WHERE codigo_producto = ?"
        params = [codigo_producto]
        if exclude_product_id not in (None, ""):
            query += " AND id <> ?"
            params.append(int(exclude_product_id))
        query += " LIMIT 1"
        return bool(self.db.fetch(query, tuple(params)))

    def save(self, product: Product) -> int:
        if product.id:
            self.db.execute(
                """
                UPDATE Productos
                SET nombre=?, descripcion=?, precio=?, stock=?, proveedor_id=?, codigo_producto=?, categoria_id=?, marca_id=?
                WHERE id=?
                """,
                (
                    product.nombre,
                    product.descripcion,
                    product.precio,
                    product.stock,
                    product.proveedor_id,
                    product.codigo_producto,
                    product.categoria_id,
                    product.marca_id,
                    product.id,
                ),
            )
            if self.db.last_error:
                raise RepositoryError(str(self.db.last_error))
            return int(product.id)

        new_id = self.db.execute(
            """
            INSERT INTO Productos (
                nombre,
                descripcion,
                precio,
                stock,
                proveedor_id,
                codigo_producto,
                categoria_id,
                marca_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product.nombre,
                product.descripcion,
                product.precio,
                product.stock,
                product.proveedor_id,
                product.codigo_producto,
                product.categoria_id,
                product.marca_id,
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
        try:
            with self.db.transaction() as cursor:
                for product in products:
                    cursor.execute(
                        """
                        INSERT INTO Productos (
                            nombre,
                            descripcion,
                            precio,
                            stock,
                            proveedor_id,
                            codigo_producto,
                            categoria_id,
                            marca_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            product.nombre,
                            product.descripcion,
                            product.precio,
                            product.stock,
                            product.proveedor_id,
                            product.codigo_producto,
                            product.categoria_id,
                            product.marca_id,
                        ),
                    )
                    count += 1
            return count
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc

    def get_price_stats(self) -> dict[str, float]:
        rows = self.db.fetch("SELECT COUNT(*), COALESCE(AVG(precio), 0) FROM Productos")
        total_products = int(rows[0][0] or 0) if rows else 0
        average_price = float(rows[0][1] or 0) if rows else 0.0
        return {
            "total_products": total_products,
            "average_price": average_price,
        }

    def adjust_prices(self, *, pct: float, step: float, adjuster) -> int:
        rows = self.db.fetch("SELECT id, precio FROM Productos")
        updated = 0
        try:
            with self.db.transaction() as cursor:
                for product_id, old_price in rows:
                    adjusted_price = adjuster.normalize(float(old_price or 0), pct=float(pct), step=float(step))
                    cursor.execute(
                        "UPDATE Productos SET precio = ? WHERE id = ?",
                        (adjusted_price, int(product_id)),
                    )
                    updated += 1
            return updated
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
