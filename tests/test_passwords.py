import unittest

from backend.wms_web.passwords import hash_password, verify_password


class PasswordTest(unittest.TestCase):
    def test_hash_is_salted_and_verifiable(self):
        first = hash_password("Password-123")
        second = hash_password("Password-123")
        self.assertNotEqual(first, second)
        self.assertNotIn("Password-123", first)
        self.assertTrue(verify_password("Password-123", first))
        self.assertFalse(verify_password("wrong-password", first))

    def test_short_password_is_rejected(self):
        with self.assertRaises(ValueError):
            hash_password("short")

    def test_invalid_hash_is_rejected(self):
        self.assertFalse(verify_password("Password-123", "invalid"))
        self.assertFalse(verify_password("Password-123", ""))


if __name__ == "__main__":
    unittest.main()
