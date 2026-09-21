from __future__ import annotations

import json
import colorsys
from pathlib import Path
from threading import RLock
from backend.wms_core.templates import PRACTICE_TEMPLATES
from backend.wms_web.config_models import validate_model
from backend.wms_web.passwords import hash_password

ROLES = ["AMMINISTRATORE", "DECISORE", "MANAGER", "VALIDATORE", "OPERATORE"]
ENTITIES = {"users", "groups", "memberships", "assignment_policies", "practice_types", "clients"}

def next_group_color(groups):
    used = {g.get("color") for g in groups}
    index = 0
    while True:
        hue = (index * 0.618033988749895) % 1
        rgb = colorsys.hls_to_rgb(hue, 0.86, 0.65)
        color = "#" + "".join(f"{round(c * 255):02x}" for c in rgb)
        if color not in used:
            return color
        index += 1


DEFAULT_DATA = {
    "groups": [
        {"id": "amministratori-wms", "name": "Amministratori WMS", "role": "AMMINISTRATORE", "active": True},
        {"id": "manager", "name": "Supervisore", "role": "MANAGER", "active": True},
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
        {"id": "mario-manager", "user_id": "mario.demo", "group_id": "manager", "label": "Supervisore", "active": True},
        {"id": "mario-contabili", "user_id": "mario.demo", "group_id": "contabili", "label": "Operatore · Contabili", "active": True},
        {"id": "mario-amministratore", "user_id": "mario.demo", "group_id": "amministratori-wms", "label": "Amministratore WMS", "active": True},
        {"id": "valeria-validatori", "user_id": "valeria.demo", "group_id": "validatori-contabili", "label": "Validatore · Contabili", "active": True},
        {"id": "luca-contabili", "user_id": "luca.demo", "group_id": "contabili", "label": "Operatore · Contabili", "active": True},
        {"id": "sara-segreteria", "user_id": "sara.demo", "group_id": "segreteria", "label": "Operatore · Segreteria", "active": True},
    ],
    "assignment_policies": [
        {"id": "self-pick", "name": "Presa in carico volontaria", "strategy": "SELF_PICK", "description": "Il task resta al gruppo finché un membro lo prende in carico.", "active": True}
    ],
    "clients": [],
    "practice_types": [
        {"id": "lipe", "code": "LIPE", "name": "LIPE", "description": "Modello dimostrativo LIPE", "active": True}
    ],
}


class AdminConfigStore:
    def __init__(self, path: Path, seed_demo: bool = True, database=None):
        self.database = database
        self._importing = True
        self.path = path
        self._lock = RLock()
        self._seed_demo = seed_demo
        stored = database.load_config() if database else None
        self._data = self._load() if stored is None else self._upgrade(stored)
        self._importing = False
        if database: self._persist()

    def _load(self):
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                for key in ENTITIES:
                    raw.setdefault(key, [])
                data = self._upgrade(raw)
                if self._seed_demo:
                    self._seed_demo_passwords(data)
                return data
            except (OSError, json.JSONDecodeError) as error:
                raise RuntimeError("Configurazione illeggibile: importazione interrotta senza sostituire i dati") from error
        if self._seed_demo:
            data = json.loads(json.dumps(DEFAULT_DATA))
            data = self._upgrade(data)
            self._seed_demo_passwords(data)
            return data
        data = {key: [] for key in ENTITIES}
        data["catalog_version"] = 1
        self._persist(data)
        return data

    def _seed_demo_passwords(self, data):
        changed = False
        for user in data["users"]:
            if user.get("username", "").endswith(".demo") and not user.get("password_hash"):
                user["password_hash"] = hash_password("demo", enforce_policy=False)
                changed = True
        if changed:
            self._persist(data)

    def _upgrade(self, data):
        if data.get("catalog_version", 0) < 1:
            for code, tasks in PRACTICE_TEMPLATES.items():
                row = next((r for r in data["practice_types"] if r.get("code") == code), None)
                if row is None:
                    row = {"id": code, "code": code, "name": {"LIPE_TRIM":"LIPE trimestrale", "F24_MENSILE":"F24 mensile", "RICONC_BANCA":"Riconciliazione bancaria", "CU_ANNUALE":"Certificazione Unica annuale", "BILANCIO_VER":"Verifica di bilancio"}[code], "active": True}
                    data["practice_types"].append(row)
                row.setdefault("tasks", [{"code": c, "title": t, "instructions": i, "assigned_group": "contabili", "required": True, "depends_on": [], "days_before_due": 0} for c, t, i in tasks])
                row.setdefault("requires_validation", True)
            # Preserve the older LIPE entry and make its existing editor usable too.
            for row in data["practice_types"]:
                if row.get("code") == "LIPE" and "tasks" not in row:
                    row["tasks"] = [{"code": c, "title": t, "instructions": i, "assigned_group": "contabili", "required": True, "depends_on": [], "days_before_due": 0} for c, t, i in PRACTICE_TEMPLATES["LIPE_TRIM"]]
                    row.setdefault("requires_validation", True)
            data["catalog_version"] = 1
            self._persist(data)
        if data.get("workflow_version", 0) < 1:
            for row in data["practice_types"]:
                tasks = row.get("tasks", [])
                if row.get("code") in {*PRACTICE_TEMPLATES, "LIPE"} and not any(t.get("transitions") or t.get("depends_on") for t in tasks):
                    for index, task in enumerate(tasks):
                        task["transitions"] = {"*": [tasks[index + 1]["code"]] if index + 1 < len(tasks) else ["@END"]}
                for task in tasks:
                    task.setdefault("outcomes", [])
            for entity, field in (("groups", "name"), ("memberships", "label")):
                for row in data[entity]:
                    if row.get(field) == "Manager": row[field] = "Supervisore"
            data["workflow_version"] = 1
            self._persist(data)
        if data.get("initial_nodes_version", 0) < 1:
            from backend.wms_web.config_models import model_graph_issues
            for row in data["practice_types"]:
                model_graph_issues(row.get("tasks", []))
            data["initial_nodes_version"] = 1
            self._persist(data)
        changed = False
        for group in data["groups"]:
            if not group.get("color"):
                group["color"] = next_group_color(data["groups"])
                changed = True
        if changed:
            self._persist(data)
        return data

    def sync_clients(self, client_ids, client_names=None):
        client_names = client_names or {}
        with self._lock:
            existing = {r["id"] for r in self._data["clients"]}
            missing = sorted(set(client_ids) - existing)
            for code in missing:
                self._data["clients"].append({
                    "id": code,
                    "name": client_names.get(code, code),
                    "tax_code": "",
                    "vat_number": "",
                    "email": "",
                    "active": True,
                })
            if missing:
                self._persist()

    def _persist(self, data=None):
        data = data if data is not None else self._data
        if self.database:
            if not self._importing: self.database.save_config(data)
            return
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def snapshot(self):
        with self._lock:
            data = json.loads(json.dumps({**self._data, "roles": ROLES}))
            for user in data["users"]:
                user.pop("password_hash", None)
            return data

    def list(self, entity: str):
        self._check_entity(entity)
        with self._lock:
            rows = json.loads(json.dumps(self._data[entity]))
            if entity == "users":
                for row in rows:
                    row.pop("password_hash", None)
            return rows

    def authentication_data(self):
        with self._lock:
            return json.loads(json.dumps({
                "users": self._data["users"],
                "groups": self._data["groups"],
                "memberships": self._data["memberships"],
            }))

    def set_password_hash(self, user_id: str, password_hash: str):
        with self._lock:
            user = next((u for u in self._data["users"] if u["id"] == user_id), None)
            if user is None:
                raise KeyError(user_id)
            user["password_hash"] = password_hash
            self._persist()

    def save(self, entity: str, item: dict):
        self._check_entity(entity)
        with self._lock:
            previous = next((r for r in self._data[entity] if r["id"] == item.get("id")), {})
            merged = {**previous, **item}
            if entity == "groups":
                merged["color"] = previous.get("color") or next_group_color(self._data["groups"])
            if entity == "users":
                if previous.get("password_hash"):
                    merged["password_hash"] = previous["password_hash"]
                else:
                    merged.pop("password_hash", None)
            clean = self._validate(entity, merged)
            backup = json.loads(json.dumps(self._data))
            rows = self._data[entity]
            index = next((i for i, row in enumerate(rows) if row["id"] == clean["id"]), None)
            if index is None:
                rows.append(clean)
            else:
                rows[index] = clean
            try: self._persist()
            except Exception:
                self._data = backup
                raise
            result = json.loads(json.dumps(clean))
            if entity == "users":
                result.pop("password_hash", None)
            return result

    def delete(self, entity: str, item_id: str):
        self._check_entity(entity)
        with self._lock:
            if entity == "groups" and any(m["group_id"] == item_id for m in self._data["memberships"]):
                raise ValueError("Il gruppo è utilizzato da una o più appartenenze: disattivarlo invece di eliminarlo")
            if entity == "users" and any(m["user_id"] == item_id for m in self._data["memberships"]):
                raise ValueError("L'utente possiede appartenenze: disattivarlo invece di eliminarlo")
            if entity == "groups" and any(t.get("assigned_group") == item_id for m in self._data["practice_types"] for t in m.get("tasks", [])):
                raise ValueError("Il gruppo è utilizzato da un modello di pratica")
            if entity == "practice_types" and any(item_id in c.get("repertoire", []) for c in self._data["clients"]):
                raise ValueError("Tipo pratica incluso in un repertorio: rimuoverlo dal repertorio o disattivarlo")
            backup = json.loads(json.dumps(self._data))
            before = len(self._data[entity])
            self._data[entity] = [row for row in self._data[entity] if row["id"] != item_id]
            if len(self._data[entity]) == before:
                raise KeyError(item_id)
            try: self._persist()
            except Exception:
                self._data = backup
                raise
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
            if not item["username"]: raise ValueError("Il login è obbligatorio")
            if any(r["id"] != item_id and r.get("username") == item["username"] for r in self._data["users"]):
                raise ValueError("Login già utilizzato")
            if not str(item.get("display_name") or "").strip(): raise ValueError("Il nome visualizzato è obbligatorio")
            default_membership = str(item.get("default_membership_id") or "").strip()
            if default_membership and not any(
                m["id"] == default_membership and m.get("user_id") == item_id
                for m in self._data["memberships"]
            ):
                raise ValueError("Appartenenza predefinita non valida")
            item["default_membership_id"] = default_membership
        elif entity == "memberships":
            if not any(u["id"] == item.get("user_id") for u in self._data["users"]): raise ValueError("Utente inesistente")
            if not any(g["id"] == item.get("group_id") for g in self._data["groups"]): raise ValueError("Gruppo inesistente")
            if not str(item.get("label") or "").strip(): raise ValueError("L'etichetta dell'appartenenza è obbligatoria")
        elif entity == "assignment_policies":
            if not str(item.get("name") or "").strip(): raise ValueError("Il nome della politica è obbligatorio")
            if not str(item.get("strategy") or "").strip(): raise ValueError("La strategia è obbligatoria")
        elif entity == "clients":
            if not str(item.get("name") or "").strip(): raise ValueError("Il nome del cliente è obbligatorio")
            for key in ("name", "tax_code", "vat_number", "gis_company_code", "accounting_regime", "vat_settlement_type", "notes"):
                value = item.get(key, "")
                if not isinstance(value, str) or len(value) > (10000 if key == "notes" else 250):
                    raise ValueError(f"Campo cliente non valido: {key}")
                item[key] = value.strip()
            repertoire = item.get("repertoire", [])
            if not isinstance(repertoire, list) or not all(isinstance(v, str) for v in repertoire):
                raise ValueError("Repertorio non valido")
            if len(repertoire) != len(set(repertoire)):
                raise ValueError("Tipi pratica duplicati nel repertorio")
            if set(repertoire) - {m["id"] for m in self._data["practice_types"]}:
                raise ValueError("Tipo pratica inesistente nel repertorio")
            item["repertoire"] = sorted(repertoire)
        elif entity == "practice_types":
            if not str(item.get("code") or "").strip(): raise ValueError("Il codice pratica è obbligatorio")
            if not str(item.get("name") or "").strip(): raise ValueError("Il nome del tipo pratica è obbligatorio")
            if any(r["id"] != item_id and r.get("code") == item["code"] for r in self._data[entity]): raise ValueError("Codice tipo pratica già utilizzato")
            validate_model(item, self._data["groups"])
        return item
