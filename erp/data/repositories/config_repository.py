from __future__ import annotations

from dataclasses import dataclass

from database import DBManager


class RepositoryError(RuntimeError):
    pass


@dataclass(slots=True)
class ConfigRepository:
    db: DBManager

    def list_discounts(self) -> list[tuple[int, str, str, float]]:
        rows = self.db.fetch("SELECT id, nombre, tipo, porcentaje FROM Descuentos ORDER BY nombre")
        return [
            (int(row[0]), str(row[1] or ""), str(row[2] or ""), float(row[3] or 0))
            for row in rows
        ]

    def save_discount(self, discount_id: str | None, nombre: str, tipo: str, porcentaje: float) -> int:
        if discount_id:
            self.db.execute_checked(
                "UPDATE Descuentos SET nombre=?, tipo=?, porcentaje=? WHERE id=?",
                (nombre, tipo, porcentaje, int(discount_id)),
            )
            return int(discount_id)

        new_id = self.db.execute_checked(
            "INSERT INTO Descuentos (nombre, tipo, porcentaje) VALUES (?, ?, ?)",
            (nombre, tipo, porcentaje),
        )
        if new_id is None:
            raise RepositoryError("No se pudo crear descuento.")
        return int(new_id)

    def delete_discount(self, discount_id: int) -> None:
        self.db.execute_checked("DELETE FROM Descuentos WHERE id=?", (discount_id,))

    def get_receipt_template(self) -> str:
        return self.db.get_config("recibo_template", self.db.default_receipt_template())

    def set_receipt_template(self, template: str) -> None:
        self.db.set_config("recibo_template", template)

    def default_receipt_template(self) -> str:
        return self.db.default_receipt_template()
