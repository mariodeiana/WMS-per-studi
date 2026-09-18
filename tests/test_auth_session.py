import tempfile
import unittest
from pathlib import Path

from backend.wms_web.admin_config import AdminConfigStore
from backend.wms_web.auth import SessionRegistry


class SessionRegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = AdminConfigStore(
            Path(self.tmp.name) / "config.json",
            seed_demo=True,
        )
        self.auth = SessionRegistry(self.config)

    def tearDown(self):
        self.tmp.cleanup()

    def test_login_uses_default_membership(self):
        token, session = self.auth.login("mario.demo", "demo")
        self.assertTrue(token)
        self.assertEqual(session["user"]["username"], "mario.demo")
        self.assertEqual(session["active"]["role"], "MANAGER")
        self.assertEqual(session["active"]["group"], "Manager")
        self.assertEqual(len(session["memberships"]), 3)

    def test_user_can_switch_membership_without_new_login(self):
        token, _ = self.auth.login("mario.demo", "demo")
        session = self.auth.switch(token, "mario-contabili")
        self.assertEqual(session["active"]["role"], "OPERATORE")
        self.assertEqual(session["active"]["group"], "Contabili")
        self.assertEqual(self.auth.describe(token)["active"]["id"], "mario-contabili")

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


class ConfiguredSessionRegistryTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        from backend.wms_web.admin_config import AdminConfigStore

        self.tmp = tempfile.TemporaryDirectory()
        self.config = AdminConfigStore(Path(self.tmp.name) / "config.json", seed_demo=True)
        self.auth = SessionRegistry(self.config)

    def tearDown(self):
        self.tmp.cleanup()

    def test_login_uses_configured_credentials(self):
        token, session = self.auth.login("mario.demo", "demo")
        self.assertTrue(session["authenticated"])
        self.assertEqual(session["active"]["id"], "mario-manager")
        self.auth.logout(token)

    def test_wrong_password_is_rejected_from_config(self):
        with self.assertRaises(PermissionError):
            self.auth.login("mario.demo", "wrong")

    def test_inactive_user_cannot_login(self):
        user = next(u for u in self.config.list("users") if u["id"] == "mario.demo")
        user["active"] = False
        self.config.save("users", user)
        with self.assertRaises(PermissionError):
            self.auth.login("mario.demo", "demo")

    def test_inactive_group_removes_membership_context(self):
        group = next(g for g in self.config.list("groups") if g["id"] == "manager")
        group["active"] = False
        self.config.save("groups", group)
        with self.assertRaises(PermissionError):
            self.auth.login("mario.demo", "demo")
