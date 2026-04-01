from __future__ import annotations

from dataclasses import dataclass

from database import DBManager


@dataclass(slots=True)
class UserRepository:
    db: DBManager

    def has_users(self) -> bool:
        return bool(self.db.has_users())

    def authenticate(self, username: str, password: str) -> tuple[int, str, str] | None:
        user = self.db.authenticate_user(username, password)
        if not user:
            return None
        return int(user[0]), str(user[1]), str(user[2])
