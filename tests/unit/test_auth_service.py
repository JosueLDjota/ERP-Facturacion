import os
import shutil
import unittest
from pathlib import Path

from database import DBManager
from erp.domain.services.security import is_password_hashed
from erp.domain.use_cases.auth_use_case import AuthService


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path("tests_runtime") / "auth_service"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = os.path.join(str(self.temp_dir), "auth_test.db")
        self.db = DBManager(self.db_path)
        self.auth = AuthService(self.db)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def test_authenticate_migrates_legacy_plaintext_password(self):
        self.db.execute_checked(
            "INSERT INTO Usuarios (nombre, usuario, contrasena, rol) VALUES (?, ?, ?, ?)",
            ("Operador", "operador", "secreta", "Cajero"),
        )

        user = self.auth.authenticate("operador", "secreta")

        self.assertEqual(user[1], "Operador")
        stored = self.db.fetch_one("SELECT contrasena FROM Usuarios WHERE usuario = ?", ("operador",))
        self.assertTrue(is_password_hashed(stored[0]))


if __name__ == "__main__":
    unittest.main()
