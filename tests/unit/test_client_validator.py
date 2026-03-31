import unittest

from erp.domain.validators.client_validator import validate_client_payload


class ClientValidatorTests(unittest.TestCase):
    def test_rejects_invalid_dni(self):
        result = validate_client_payload("Juan", "Perez", "123", "")
        self.assertFalse(result.valid)

    def test_rejects_invalid_email(self):
        result = validate_client_payload("Juan", "Perez", "", "bad-email")
        self.assertFalse(result.valid)

    def test_accepts_valid_payload(self):
        result = validate_client_payload("Juan", "Perez", "0801199901234", "juan@mail.com")
        self.assertTrue(result.valid)


if __name__ == "__main__":
    unittest.main()
