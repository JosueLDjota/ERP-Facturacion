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
            """
            SELECT id, nombre, descripcion, precio, stock, COALESCE(codigo_producto, '')
            FROM Productos
            ORDER BY nombre
            """
        )
        return [
            {
                "id": int(row[0]),
                "nombre": str(row[1] or ""),
                "descripcion": str(row[2] or ""),
                "precio": float(row[3] or 0),
                "stock": int(row[4] or 0),
                "codigo_producto": str(row[5] or ""),
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
        metodo_pago: str,
        usuario_id: int,
        cliente_id: int | None,
        tipo_recibo: str,
        items: dict,
    ) -> None:
        try:
            self.db.create_pos_sale(
                sale_id=sale_id,
                fecha=fecha,
                total=total,
                pagado=pagado,
                vuelto=vuelto,
                metodo_pago=metodo_pago,
                usuario_id=usuario_id,
                cliente_id=cliente_id,
                tipo_recibo=tipo_recibo,
                cart_data=items,
            )
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
