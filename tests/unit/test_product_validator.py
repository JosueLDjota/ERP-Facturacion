import unittest

from erp.domain.validators.product_validator import validate_product_payload


class ProductValidatorTests(unittest.TestCase):
    def test_rejects_empty_name(self):
        result = validate_product_payload("", "10", "1", "1")
        self.assertFalse(result.valid)

    def test_rejects_non_numeric_price(self):
        result = validate_product_payload("Mouse", "abc", "1", "1")
        self.assertFalse(result.valid)

    def test_accepts_valid_payload(self):
        result = validate_product_payload("Mouse", "12.50", "10", "1")
        self.assertTrue(result.valid)


if __name__ == "__main__":
    unittest.main()
