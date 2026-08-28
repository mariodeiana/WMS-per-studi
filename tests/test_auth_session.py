import unittest

from backend.wms_web.auth import SessionRegistry


class SessionRegistryTest(unittest.TestCase):
    def setUp(self):
        self.auth = SessionRegistry()

    def test_login_uses_default_membership(self):
        token, session = self.auth.login("mario.demo", "demo")
        self.assertTrue(token)
        self.assertEqual(session["user"]["username"], "mario.demo")
        self.assertEqual(session["active"]["role"], "MANAGER")
        self.assertEqual(session["active"]["group"], "Manager")
        self.assertEqual(len(session["memberships"]), 2)

    def test_user_can_switch_membership_without_new_login(self):
        token, _ = self.auth.login("mario.demo", "demo")
        session = self.auth.switch(token, "contabili")
        self.assertEqual(session["active"]["role"], "OPERATORE")
        self.assertEqual(session["active"]["group"], "Contabili")
        self.assertEqual(self.auth.describe(token)["active"]["id"], "contabili")

    def test_user_cannot_switch_to_foreign_membership(self):
        token, _ = self.auth.login("luca.demo", "demo")
        with self.assertRaises(PermissionError):
            self.auth.switch(token, "manager")

    def test_invalid_credentials_are_rejected(self):
        with self.assertRaises(PermissionError):
            self.auth.login("mario.demo", "wrong")

    def test_logout_invalidates_session(self):
        token, _ = self.auth.login("mario.demo", "demo")
        self.auth.logout(token)
        with self.assertRaises(PermissionError):
            self.auth.describe(token)


if __name__ == "__main__":
    unittest.main()
