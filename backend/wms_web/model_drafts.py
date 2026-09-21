"""Private, durable model-editor drafts. Never modifies published models."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import UUID, uuid4

class ModelDraftStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self._lock = RLock()

    def _folder(self, username):
        return self.directory / hashlib.sha256(username.encode()).hexdigest()

    def _path(self, username, draft_id):
        try: key = str(UUID(str(draft_id)))
        except (ValueError, TypeError, AttributeError) as error: raise ValueError("Identificativo bozza non valido") from error
        return self._folder(username) / (key + ".json")

    def list(self, username):
        with self._lock:
            return sorted([json.loads(p.read_text()) for p in self._folder(username).glob("*.json")], key=lambda d:d["updated_at"], reverse=True)

    def save(self, username, body):
        if body.get("owner") is not None and body["owner"] != username: raise PermissionError("Riaccedi con lo stesso utente che ha aperto questa bozza")
        path = self._path(username, body.get("id"))
        snapshot = body.get("snapshot")
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("tasks"), list) or not isinstance(snapshot.get("draft"), dict):
            raise ValueError("Contenuto bozza non valido")
        if len(snapshot["tasks"]) > 200 or len(json.dumps(snapshot).encode()) > 2_000_000:
            raise ValueError("Bozza troppo grande")
        revision = body.get("revision", 0)
        if type(revision) is not int or revision < 0: raise ValueError("Revisione bozza non valida")
        with self._lock:
            previous = json.loads(path.read_text()) if path.exists() else None
            if revision != (previous["revision"] if previous else 0):
                raise ValueError("La bozza è stata modificata in un’altra scheda. Salva una copia per conservare queste modifiche.")
            value = {"id":path.stem,"revision":revision+1,"updated_at":datetime.now(timezone.utc).isoformat(),"snapshot":snapshot}
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary = path.with_suffix('.'+uuid4().hex+'.tmp')
            try:
                with temporary.open('x', encoding='utf-8') as f:
                    os.chmod(temporary, 0o600)
                    json.dump(value, f, ensure_ascii=False)
                    f.flush(); os.fsync(f.fileno())
                os.replace(temporary,path)
                fd=os.open(path.parent, os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
            finally:
                temporary.unlink(missing_ok=True)
            return value

    def delete(self, username, body):
        path = self._path(username, body.get("id"))
        with self._lock:
            if path.exists():
                current=json.loads(path.read_text())
                if body.get("revision") != current["revision"]: raise ValueError("La bozza è cambiata: ricarica l’elenco prima di eliminarla")
                path.unlink()
            return {"ok":True}
