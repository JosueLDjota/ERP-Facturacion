from __future__ import annotations

import logging
from dataclasses import dataclass

from database import DBManager
from erp.domain.services.security import hash_password, is_password_hashed, verify_password


logger = logging.getLogger(__name__)


class AuthenticationError(RuntimeError):
    pass


@dataclass(slots=True)
class AuthService:
    db: DBManager

    def authenticate(self, username: str, password: str) -> tuple[int, str, str] | None:
        rows = self.db.fetch(
            """
            SELECT id, nombre, usuario, contrasena, rol
            FROM Usuarios
            WHERE usuario = ?
            LIMIT 1
            """,
            (username.strip(),),
        )
        if not rows:
            return None

        user_id, nombre, usuario, stored_password, rol = rows[0]
        if not verify_password(password, stored_password):
            return None

        if not is_password_hashed(stored_password):
            logger.warning("Migrando contrasena legada en texto plano para el usuario '%s'.", usuario)
            self.db.execute_checked(
                "UPDATE Usuarios SET contrasena = ? WHERE id = ?",
                (hash_password(password), user_id),
            )

        return int(user_id), str(nombre), str(rol)
