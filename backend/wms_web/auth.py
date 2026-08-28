from __future__ import annotations

import secrets
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class Group:
    id: str
    name: str
    role: str


GROUPS = {
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
    def __init__(self):
        self._lock = RLock()
        self._sessions: dict[str, dict[str, str]] = {}

    def login(self, username: str, password: str):
        account = DEMO_ACCOUNTS.get(username)
        if account is None or account.password != password:
            raise PermissionError("Credenziali non valide")
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = {"username": account.username, "membership_id": account.default_membership_id}
        return token, self.describe(token)

    def logout(self, token: str | None):
        if token:
            with self._lock:
                self._sessions.pop(token, None)

    def principal(self, token: str | None):
        account, membership = self._resolve(token)
        group = membership.group
        return {
            "username": account.username,
            "display_name": account.display_name,
            "membership_id": membership.id,
            "group_id": group.id,
            "group": group.name,
            "role": group.role,
        }

    def describe(self, token: str | None):
        account, membership = self._resolve(token)
        return {
            "authenticated": True,
            "user": {"username": account.username, "display_name": account.display_name},
            "active": self._membership_payload(membership),
            "memberships": [self._membership_payload(item) for item in account.memberships],
        }

    def switch(self, token: str | None, membership_id: str):
        account, _ = self._resolve(token)
        if not any(item.id == membership_id for item in account.memberships):
            raise PermissionError("Il contesto operativo selezionato non appartiene all'utente")
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
            account = DEMO_ACCOUNTS[state["username"]]
            membership = next(item for item in account.memberships if item.id == state["membership_id"])
            return account, membership

    @staticmethod
    def _membership_payload(membership: Membership):
        group = membership.group
        return {"id": membership.id, "group_id": group.id, "group": group.name, "role": group.role, "label": membership.label}


AUTH = SessionRegistry()
