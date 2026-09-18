from __future__ import annotations

import secrets
from threading import RLock

from backend.wms_web.passwords import verify_password


class SessionRegistry:
    def __init__(self, config):
        self._lock = RLock()
        self._sessions: dict[str, dict[str, str]] = {}
        self._config = config

    def login(self, username: str, password: str):
        account = self._account(username)

        if account is None or not self._password_valid(account, password):
            raise PermissionError("Credenziali non valide")

        memberships = account["memberships"]
        default_membership_id = account.get("default_membership_id")

        if not memberships:
            raise PermissionError("Utente senza appartenenze attive")

        if not any(m["id"] == default_membership_id for m in memberships):
            raise PermissionError("Appartenenza predefinita non valida")

        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = {
                "username": account["username"],
                "membership_id": default_membership_id,
            }
        return token, self.describe(token)

    def logout(self, token: str | None):
        if token:
            with self._lock:
                self._sessions.pop(token, None)

    def principal(self, token: str | None):
        account, membership = self._resolve(token)
        group = membership["group"]
        return {
            "username": account["username"],
            "display_name": account["display_name"],
            "membership_id": membership["id"],
            "group_id": group["id"],
            "group": group["name"],
            "role": group["role"],
        }

    def describe(self, token: str | None):
        account, membership = self._resolve(token)
        return {
            "authenticated": True,
            "user": {
                "username": account["username"],
                "display_name": account["display_name"],
            },
            "active": self._membership_payload(membership),
            "memberships": [
                self._membership_payload(item)
                for item in account["memberships"]
            ],
        }

    def switch(self, token: str | None, membership_id: str):
        account, _ = self._resolve(token)

        if not any(item["id"] == membership_id for item in account["memberships"]):
            raise PermissionError(
                "Il contesto operativo selezionato non appartiene all'utente"
            )

        with self._lock:
            self._sessions[token]["membership_id"] = membership_id

        return self.describe(token)

    def _resolve(self, token: str | None):
        if not token:
            raise PermissionError("Sessione non autenticata")

        with self._lock:
            state = self._sessions.get(token)

        if state is None:
            raise PermissionError("Sessione non autenticata")

        account = self._account(state["username"])
        if account is None:
            raise PermissionError("Sessione non autenticata")

        membership = next(
            (
                item
                for item in account["memberships"]
                if item["id"] == state["membership_id"]
            ),
            None,
        )

        if membership is None:
            raise PermissionError("Contesto operativo non più disponibile")

        return account, membership

    def _account(self, username: str):
        data = self._config.authentication_data()

        user = next(
            (
                u for u in data["users"]
                if u.get("username") == username and u.get("active", True)
            ),
            None,
        )
        if user is None:
            return None

        groups = {
            g["id"]: g
            for g in data["groups"]
            if g.get("active", True)
        }

        memberships = []
        for membership in data["memberships"]:
            if membership.get("user_id") != user["id"]:
                continue
            if not membership.get("active", True):
                continue
            group = groups.get(membership.get("group_id"))
            if group is None:
                continue
            memberships.append({**membership, "group": group})

        return {**user, "memberships": memberships}

    def _password_valid(self, account: dict, password: str):
        encoded = account.get("password_hash")
        return bool(encoded) and verify_password(password, encoded)

    @staticmethod
    def _membership_payload(membership: dict):
        group = membership["group"]
        return {
            "id": membership["id"],
            "group_id": group["id"],
            "group": group["name"],
            "role": group["role"],
            "label": membership["label"],
        }
