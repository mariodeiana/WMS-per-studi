"""Transactional SQL persistence; PostgreSQL in production, SQLite for local use/tests.

Legacy files are read once by the stores and are never modified during import.
Workflow objects use a versionable JSON representation, not executable pickle.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import MISSING, fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import RLock
from backend.wms_core import models

ENTITIES = ('users', 'groups', 'memberships', 'assignment_policies', 'practice_types', 'clients')
CLIENT_FIELDS = ('name', 'tax_code', 'vat_number', 'gis_company_code', 'accounting_regime', 'vat_settlement_type', 'notes')
CLIENT_REPERTOIRE_FIELDS = ('repertoire_signed_on', 'repertoire_valid_until', 'repertoire_billing_frequency')
TYPES = {name: cls for name, cls in vars(models).items() if isinstance(cls, type) and (is_dataclass(cls) or issubclass(cls, Enum))}


def encode(value):
    if isinstance(value, Enum): return {'$enum': type(value).__name__, 'value': value.value}
    if isinstance(value, datetime): return {'$datetime': value.isoformat()}
    if is_dataclass(value):
        values = {}
        for f in fields(value):
            default = f.default_factory() if f.default_factory is not MISSING else f.default
            values[f.name] = encode(getattr(value, f.name, default))
        return {'$type': type(value).__name__, 'fields': values}
    if isinstance(value, tuple): return {'$tuple': [encode(v) for v in value]}
    if isinstance(value, list): return [encode(v) for v in value]
    if isinstance(value, dict): return {'$dict': [[k, encode(v)] for k, v in value.items()]}
    return value


def decode(value):
    if isinstance(value, list): return [decode(v) for v in value]
    if not isinstance(value, dict): return value
    if '$enum' in value: return TYPES[value['$enum']](value['value'])
    if '$datetime' in value: return datetime.fromisoformat(value['$datetime'])
    if '$tuple' in value: return tuple(decode(v) for v in value['$tuple'])
    if '$dict' in value: return {k: decode(v) for k, v in value['$dict']}
    return TYPES[value['$type']](**{k: decode(v) for k, v in value['fields'].items()})


class Database:
    def __init__(self, location):
        self._lock = RLock()
        self.postgres = str(location).startswith(('postgresql://', 'postgres://'))
        if self.postgres:
            import psycopg
            self.connection = psycopg.connect(str(location))
        else:
            Path(location).parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(str(location), check_same_thread=False)
            self.connection.execute('PRAGMA foreign_keys = ON')
        with self.transaction() as execute:
            execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)')
            applied = {row[0] for row in execute('SELECT version FROM schema_migrations').fetchall()}
            for migration in sorted((Path(__file__).resolve().parents[1] / 'migrations').glob('*.sql')):
                version = int(migration.name.split('_')[0])
                if version in applied: continue
                for statement in migration.read_text().split(';'):
                    if statement.strip(): execute(statement)

    @contextmanager
    def transaction(self):
        with self._lock:
            def execute(sql, params=()):
                return self.connection.execute(sql.replace('?', '%s') if self.postgres else sql, params)
            try:
                yield execute
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise

    def load_config(self):
        with self.transaction() as execute:
            meta = execute("SELECT payload FROM configuration_meta WHERE id='config'").fetchone()
            if meta is None: return None
            data = json.loads(meta[0])
            order = data.pop('_row_order', {})
            for entity in ENTITIES:
                data[entity] = [json.loads(r[0]) for r in execute(f'SELECT payload FROM {entity} ORDER BY id').fetchall()]
                positions = {item_id: i for i, item_id in enumerate(order.get(entity, []))}
                data[entity].sort(key=lambda r: positions.get(r['id'], len(positions)))
            included = {}
            for client, model in execute('SELECT client_id, practice_type_id FROM client_repertoire ORDER BY practice_type_id').fetchall():
                included.setdefault(client, []).append(model)
            dates = {r[0]: r[1:] for r in execute('SELECT id,repertoire_signed_on,repertoire_valid_until,repertoire_billing_frequency FROM clients').fetchall()}
            for client in data['clients']:
                client['repertoire'] = included.get(client['id'], [])
                for key, value in zip(CLIENT_REPERTOIRE_FIELDS, dates[client['id']]):
                    client[key] = str(value) if value is not None else ''
            return data

    def save_config(self, data):
        for entity in ENTITIES:
            if len({row['id'] for row in data[entity]}) != len(data[entity]):
                raise ValueError(f'ID duplicati in {entity}: migrazione interrotta')
        with self.transaction() as execute:
            execute('DELETE FROM client_repertoire')
            for entity in ENTITIES:
                ids = {r['id'] for r in data[entity]}
                for row in data[entity]:
                    payload = json.dumps(row, ensure_ascii=False)
                    if entity == 'clients':
                        names = ('id', *CLIENT_FIELDS, *CLIENT_REPERTOIRE_FIELDS, 'active', 'payload')
                        values = (row['id'], *(row.get(k, '') for k in CLIENT_FIELDS), *(row.get(k) or None for k in CLIENT_REPERTOIRE_FIELDS), int(row.get('active', True)), payload)
                    else:
                        names, values = ('id', 'payload'), (row['id'], payload)
                    execute(f"INSERT INTO {entity} ({','.join(names)}) VALUES ({','.join('?' for _ in names)}) ON CONFLICT (id) DO UPDATE SET " + ','.join(f'{n}=excluded.{n}' for n in names[1:]), values)
                for (existing,) in execute(f'SELECT id FROM {entity}').fetchall():
                    if existing not in ids: execute(f'DELETE FROM {entity} WHERE id=?', (existing,))
            for client in data['clients']:
                for model in client.get('repertoire', []):
                    execute('INSERT INTO client_repertoire VALUES (?,?)', (client['id'], model))
            meta = {k: v for k, v in data.items() if k not in ENTITIES}
            meta['_row_order'] = {entity: [row['id'] for row in data[entity]] for entity in ENTITIES}
            execute("INSERT INTO configuration_meta VALUES ('config',?) ON CONFLICT (id) DO UPDATE SET payload=excluded.payload", (json.dumps(meta),))

    def load_practices(self):
        with self.transaction() as execute:
            marker = execute("SELECT id FROM configuration_meta WHERE id='practices'").fetchone()
            if marker is None: return None
            return {r[0]: decode(json.loads(r[1])) for r in execute('SELECT id,payload FROM practices ORDER BY id').fetchall()}

    def save_practices(self, practices):
        with self.transaction() as execute:
            for p in practices.values():
                execute('INSERT INTO practices VALUES (?,?,?,?,?,?) ON CONFLICT (id) DO UPDATE SET payload=excluded.payload',
                        (p.id, p.client_id, p.practice_type_id, p.origin, p.economic_regime, json.dumps(encode(p))))
            execute("INSERT INTO configuration_meta VALUES ('practices','{}') ON CONFLICT (id) DO NOTHING")


def database_location(data_dir):
    """Explicit environment wins; a local URL file supports the workstation DB."""
    if os.environ.get('WMS_DATABASE_URL'): return os.environ['WMS_DATABASE_URL']
    saved = Path(data_dir) / '.wms-database-url'
    if saved.exists(): return saved.read_text().strip()
    return Path(data_dir) / 'wms.sqlite3'
