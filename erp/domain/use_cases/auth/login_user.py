from __future__ import annotations

from dataclasses import dataclass

from erp.data.repositories.user_repository import UserRepository


@dataclass(slots=True)
class LoginResponse:
    status: str
    user: tuple[int, str, str] | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "success" and self.user is not None


@dataclass(slots=True)
class LoginUser:
    users: UserRepository

    def execute(self, username: str, password: str) -> LoginResponse:
        username = str(username or "").strip()

        if not username or password in (None, ""):
            return LoginResponse(
                status="missing_credentials",
                message="Ingrese usuario y contrasena para iniciar sesion.",
            )

        if not self.users.has_users():
            return LoginResponse(
                status="missing_users",
                message="La base actual no tiene usuarios registrados. Se requiere crear uno antes de iniciar sesion.",
            )

        user = self.users.authenticate(username, password)
        if not user:
            return LoginResponse(
                status="invalid_credentials",
                message="Usuario o contrasena incorrectos.",
            )

        return LoginResponse(status="success", user=user)
