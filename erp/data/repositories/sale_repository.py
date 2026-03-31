from __future__ import annotations

from dataclasses import dataclass

from database import DBManager


class RepositoryError(RuntimeError):
    pass


@dataclass(slots=True)
class SaleRepository:
    db: DBManager

    def get_sales_totals(self) -> dict[str, float]:
        total = self.db.fetch("SELECT SUM(total) FROM Ventas")[0][0] or 0
        daily = self.db.fetch("SELECT SUM(total) FROM Ventas WHERE DATE(fecha)=DATE('now')")[0][0] or 0
        monthly = self.db.fetch(
            "SELECT SUM(total) FROM Ventas WHERE strftime('%m', fecha)=strftime('%m','now')"
        )[0][0] or 0
        return {
            "total": float(total),
            "daily": float(daily),
            "monthly": float(monthly),
        }

    def list_products(self) -> list[dict]:
        rows = self.db.fetch(
            "SELECT id, nombre, descripcion, precio, stock FROM Productos ORDER BY nombre"
        )
        return [
            {
                "id": int(row[0]),
                "nombre": str(row[1] or ""),
                "descripcion": str(row[2] or ""),
                "precio": float(row[3] or 0),
                "stock": int(row[4] or 0),
            }
            for row in rows
        ]

    def list_clients(self) -> list[dict]:
        rows = self.db.fetch(
            """
            SELECT id, nombre, apellido, COALESCE(mayorista, 0)
            FROM Clientes
            WHERE activo = 1
            ORDER BY apellido, nombre
            """
        )
        return [
            {
                "id": int(row[0]),
                "nombre": str(row[1] or ""),
                "apellido": str(row[2] or ""),
                "mayorista": bool(row[3]),
            }
            for row in rows
        ]

    def get_client_detail(self, client_id: int) -> dict | None:
        rows = self.db.fetch(
            "SELECT nombre, apellido, dni, telefono, direccion FROM Clientes WHERE id = ?",
            (client_id,),
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "nombre": row[0],
            "apellido": row[1],
            "dni": row[2],
            "telefono": row[3],
            "direccion": row[4],
        }

    def list_discounts(self) -> list[dict]:
        rows = self.db.fetch("SELECT id, nombre, tipo, porcentaje FROM Descuentos ORDER BY nombre")
        return [
            {
                "id": int(row[0]),
                "nombre": str(row[1] or ""),
                "tipo": str(row[2] or ""),
                "porcentaje": float(row[3] or 0),
            }
            for row in rows
        ]

    def create_sale(
        self,
        sale_id: str,
        fecha: str,
        total: float,
        pagado: float,
        vuelto: float,
        usuario_id: int,
        cliente_id: int | None,
        tipo_recibo: str,
        items: list[dict],
    ) -> None:
        try:
            with self.db.transaction():
                self.db.execute_checked(
                    """
                    INSERT INTO Ventas (id, fecha, total, monto_pagado, vuelto, usuario_id, id_cliente, tipo_recibo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sale_id, fecha, total, pagado, vuelto, usuario_id, cliente_id, tipo_recibo),
                )

                for item in items:
                    producto_id = int(item["producto_id"])
                    cantidad = int(item["cantidad"])
                    precio = float(item["precio_unitario"])
                    pct = float(item.get("descuento_porcentaje", 0))
                    discount_amount = (precio * cantidad) * pct
                    subtotal = (precio * cantidad) - discount_amount

                    stock_row = self.db.fetch_one(
                        "SELECT stock FROM Productos WHERE id = ?",
                        (producto_id,),
                    )
                    if not stock_row:
                        raise RepositoryError(f"Producto {producto_id} no existe.")
                    if int(stock_row[0]) < cantidad:
                        raise RepositoryError(f"Stock insuficiente para producto {producto_id}.")

                    self.db.execute_checked(
                        """
                        INSERT INTO DetalleVenta (venta_id, producto_id, nombre_producto, cantidad, precio_unitario, descuento, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sale_id,
                            producto_id,
                            str(item["nombre"]),
                            cantidad,
                            precio,
                            discount_amount,
                            subtotal,
                        ),
                    )
                    self.db.execute_checked(
                        "UPDATE Productos SET stock = stock - ? WHERE id = ?",
                        (cantidad, producto_id),
                    )
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
