from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

ROLES = ["AMMINISTRATORE", "DECISORE", "MANAGER", "VALIDATORE", "OPERATORE"]
ENTITIES = {"users", "groups", "memberships", "assignment_policies", "practice_types"}

DEFAULT_DATA = {
    "groups": [
        {"id": "amministratori-wms", "name": "Amministratori WMS", "role": "AMMINISTRATORE", "active": True},
        {"id": "manager", "name": "Manager", "role": "MANAGER", "active": True},
        {"id": "contabili", "name": "Contabili", "role": "OPERATORE", "active": True},
        {"id": "segreteria", "name": "Segreteria", "role": "OPERATORE", "active": True},
        {"id": "validatori-contabili", "name": "Validatori contabili", "role": "VALIDATORE", "active": True},
    ],
    "users": [
        {"id": "mario.demo", "username": "mario.demo", "display_name": "Mario Demo", "active": True, "default_membership_id": "mario-manager"},
        {"id": "valeria.demo", "username": "valeria.demo", "display_name": "Valeria Demo", "active": True, "default_membership_id": "valeria-validatori"},
        {"id": "luca.demo", "username": "luca.demo", "display_name": "Luca Demo", "active": True, "default_membership_id": "luca-contabili"},
        {"id": "sara.demo", "username": "sara.demo", "display_name": "Sara Demo", "active": True, "default_membership_id": "sara-segreteria"},
    ],
    "memberships": [
        {"id": "mario-manager", "user_id": "mario.demo", "group_id": "manager", "label": "Manager", "active": True},
        {"id": "mario-contabili", "user_id": "mario.demo", "group_id": "contabili", "label": "Operatore · Contabili", "active": True},
        {"id": "mario-amministratore", "user_id": "mario.demo", "group_id": "amministratori-wms", "label": "Amministratore WMS", "active": True},
        {"id": "valeria-validatori", "user_id": "valeria.demo", "group_id": "validatori-contabili", "label": "Validatore · Contabili", "active": True},
        {"id": "luca-contabili", "user_id": "luca.demo", "group_id": "contabili", "label": "Operatore · Contabili", "active": True},
        {"id": "sara-segreteria", "user_id": "sara.demo", "group_id": "segreteria", "label": "Operatore · Segreteria", "active": True},
    ],
    "assignment_policies": [
        {"id": "self-pick", "name": "Presa in carico volontaria", "strategy": "SELF_PICK", "description": "Il task resta al gruppo finché un membro lo prende in carico.", "active": True}
    ],
    "practice_types": [
        {"id": "lipe", "code": "LIPE", "name": "LIPE", "description": "Modello dimostrativo LIPE", "active": True}
    ],
}


class AdminConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = RLock()
        self._data = self._load()

    def _load(self):
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                for key in ENTITIES:
                    raw.setdefault(key, [])
                return raw
            except (OSError, json.JSONDecodeError):
                pass
        data = json.loads(json.dumps(DEFAULT_DATA))
        self._persist(data)
        return data

    def _persist(self, data=None):
        data = data if data is not None else self._data
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def snapshot(self):
        with self._lock:
            return json.loads(json.dumps({**self._data, "roles": ROLES}))

    def list(self, entity: str):
        self._check_entity(entity)
        with self._lock:
            return json.loads(json.dumps(self._data[entity]))

    def save(self, entity: str, item: dict):
        self._check_entity(entity)
        clean = self._validate(entity, item)
        with self._lock:
            rows = self._data[entity]
            index = next((i for i, row in enumerate(rows) if row["id"] == clean["id"]), None)
            if index is None:
                rows.append(clean)
            else:
                rows[index] = clean
            self._persist()
            return json.loads(json.dumps(clean))

    def delete(self, entity: str, item_id: str):
        self._check_entity(entity)
        with self._lock:
            if entity == "groups" and any(m["group_id"] == item_id for m in self._data["memberships"]):
                raise ValueError("Il gruppo è utilizzato da una o più appartenenze: disattivarlo invece di eliminarlo")
            if entity == "users" and any(m["user_id"] == item_id for m in self._data["memberships"]):
                raise ValueError("L'utente possiede appartenenze: disattivarlo invece di eliminarlo")
            before = len(self._data[entity])
            self._data[entity] = [row for row in self._data[entity] if row["id"] != item_id]
            if len(self._data[entity]) == before:
                raise KeyError(item_id)
            self._persist()
            return {"ok": True, "id": item_id}

    @staticmethod
    def _check_entity(entity: str):
        if entity not in ENTITIES:
            raise KeyError(entity)

    def _validate(self, entity: str, item: dict):
        item = dict(item or {})
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            raise ValueError("Il codice/ID è obbligatorio")
        item["id"] = item_id
        item["active"] = bool(item.get("active", True))
        if entity == "groups":
            if not str(item.get("name") or "").strip(): raise ValueError("Il nome del gruppo è obbligatorio")
            if item.get("role") not in ROLES: raise ValueError("Ruolo non valido")
        elif entity == "users":
            item["username"] = str(item.get("username") or item_id).strip()
            if not str(item.get("display_name") or "").strip(): raise ValueError("Il nome visualizzato è obbligatorio")
        elif entity == "memberships":
            if not any(u["id"] == item.get("user_id") for u in self._data["users"]): raise ValueError("Utente inesistente")
            if not any(g["id"] == item.get("group_id") for g in self._data["groups"]): raise ValueError("Gruppo inesistente")
            if not str(item.get("label") or "").strip(): raise ValueError("L'etichetta dell'appartenenza è obbligatoria")
        elif entity == "assignment_policies":
            if not str(item.get("name") or "").strip(): raise ValueError("Il nome della politica è obbligatorio")
            if not str(item.get("strategy") or "").strip(): raise ValueError("La strategia è obbligatoria")
        elif entity == "practice_types":
            if not str(item.get("code") or "").strip(): raise ValueError("Il codice pratica è obbligatorio")
            if not str(item.get("name") or "").strip(): raise ValueError("Il nome del tipo pratica è obbligatorio")
        return item
