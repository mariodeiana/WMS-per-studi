from __future__ import annotations

import secrets
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class Membership:
    id: str
    group: str
    role: str
    actor: str
    label: str


@dataclass(frozen=True)
class Account:
    username: str
    password: str
    display_name: str
    default_membership_id: str
    memberships: tuple[Membership, ...]


DEMO_ACCOUNTS = {
    "mario.demo": Account(
        username="mario.demo",
        password="demo",
        display_name="Mario Demo",
        default_membership_id="manager",
        memberships=(
            Membership("manager", "Manager", "MANAGER", "marta.manager", "Manager"),
            Membership("contabili", "Contabili", "OPERATORE", "anna.operatore", "Operatore · Contabili"),
        ),
    ),
    "valeria.demo": Account(
        username="valeria.demo",
        password="demo",
        display_name="Valeria Demo",
        default_membership_id="validatori",
        memberships=(
            Membership("validatori", "Validatori contabili", "VALIDATORE", "valeria.validatore", "Validatore · Contabili"),
        ),
    ),
    "luca.demo": Account(
        username="luca.demo",
        password="demo",
        display_name="Luca Demo",
        default_membership_id="contabili",
        memberships=(
            Membership("contabili", "Contabili", "OPERATORE", "luca.operatore", "Operatore · Contabili"),
        ),
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
            self._sessions[token] = {
                "username": account.username,
                "membership_id": account.default_membership_id,
            }
        return token, self.describe(token)

    def logout(self, token: str | None):
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def describe(self, token: str | None):
        account, membership = self._resolve(token)
        return {
            "authenticated": True,
            "user": {
                "username": account.username,
                "display_name": account.display_name,
            },
            "active": self._membership_payload(membership),
            "memberships": [self._membership_payload(item) for item in account.memberships],
        }

    def actor(self, token: str | None) -> str:
        _, membership = self._resolve(token)
        return membership.actor

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
            membership = next(
                item for item in account.memberships if item.id == state["membership_id"]
            )
            return account, membership

    @staticmethod
    def _membership_payload(membership: Membership):
        return {
            "id": membership.id,
            "group": membership.group,
            "role": membership.role,
            "actor": membership.actor,
            "label": membership.label,
        }


AUTH = SessionRegistry()
