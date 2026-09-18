from __future__ import annotations

import secrets
from dataclasses import dataclass
from threading import RLock

from backend.wms_web.passwords import verify_password


@dataclass(frozen=True)
class Group:
    id: str
    name: str
    role: str


GROUPS = {
    "amministratori-wms": Group("amministratori-wms", "Amministratori WMS", "AMMINISTRATORE"),
    "manager": Group("manager", "Manager", "MANAGER"),
    "contabili": Group("contabili", "Contabili", "OPERATORE"),
    "segreteria": Group("segreteria", "Segreteria", "OPERATORE"),
    "validatori-contabili": Group("validatori-contabili", "Validatori contabili", "VALIDATORE"),
}


@dataclass(frozen=True)
class Membership:
    id: str
    group_id: str
    label: str

    @property
    def group(self) -> Group:
        return GROUPS[self.group_id]


@dataclass(frozen=True)
class Account:
    username: str
    password: str
    display_name: str
    default_membership_id: str
    memberships: tuple[Membership, ...]


DEMO_ACCOUNTS = {
    "mario.demo": Account(
        "mario.demo", "demo", "Mario Demo", "mario-manager",
        (
            Membership("mario-manager", "manager", "Manager"),
            Membership("mario-contabili", "contabili", "Operatore · Contabili"),
            Membership("mario-amministratore", "amministratori-wms", "Amministratore WMS"),
        ),
    ),
    "valeria.demo": Account(
        "valeria.demo", "demo", "Valeria Demo", "valeria-validatori",
        (Membership("valeria-validatori", "validatori-contabili", "Validatore · Contabili"),),
    ),
    "luca.demo": Account(
        "luca.demo", "demo", "Luca Demo", "luca-contabili",
        (Membership("luca-contabili", "contabili", "Operatore · Contabili"),),
    ),
    "sara.demo": Account(
        "sara.demo", "demo", "Sara Demo", "sara-segreteria",
        (Membership("sara-segreteria", "segreteria", "Operatore · Segreteria"),),
    ),
}


class SessionRegistry:
    def __init__(self, config=None):
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
        if self._config is None:
            demo = DEMO_ACCOUNTS.get(username)
            if demo is None:
                return None
            return {
                "id": demo.username,
                "username": demo.username,
                "display_name": demo.display_name,
                "active": True,
                "default_membership_id": demo.default_membership_id,
                "password": demo.password,
                "memberships": [
                    {
                        "id": m.id,
                        "group_id": m.group_id,
                        "label": m.label,
                        "active": True,
                        "group": {
                            "id": m.group.id,
                            "name": m.group.name,
                            "role": m.group.role,
                            "active": True,
                        },
                    }
                    for m in demo.memberships
                ],
            }

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
        if self._config is None:
            return secrets.compare_digest(account["password"], password)

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


AUTH = SessionRegistry()
