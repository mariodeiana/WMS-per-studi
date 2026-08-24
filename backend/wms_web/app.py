from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from backend.wms_core import Role, WorkflowError, close_practice, complete_task, operator_work_queue, reopen_task, validate_practice
from backend.wms_core.models import EvidenceInput, Practice
from backend.wms_core.views import manager_practice_view, task_detail, validator_view
from backend.wms_web.render import evidence_list, page, result_fields, task_row
from backend.wms_web.store import PracticeStore, demo_store


STORE = demo_store()


def _jsonable(value):
    if isinstance(value, (datetime, Enum)):
        return value.isoformat() if isinstance(value, datetime) else value.value
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _attachments(form: dict[str, list[str]]) -> list[EvidenceInput]:
    names, refs = form.get("evidence_name", []), form.get("evidence_ref", [])
    return [EvidenceInput(name, refs[index] if index < len(refs) else "") for index, name in enumerate(names) if name.strip()]


class WMSHandler(BaseHTTPRequestHandler):
    store: PracticeStore = STORE

    def _send(self, body: str | bytes, status=HTTPStatus.OK, content_type="text/html; charset=utf-8"):
        payload = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _redirect(self, path: str):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", path)
        self.end_headers()

    def _form(self):
        length = int(self.headers.get("Content-Length", "0"))
        return parse_qs(self.rfile.read(length).decode(), keep_blank_values=True)

    def _practice(self, practice_id: str) -> Practice:
        try:
            return self.store.get(practice_id)
        except KeyError as error:
            raise WorkflowError("Pratica inesistente") from error

    def do_GET(self):
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                return self._work_queue(query.get("actor", ["mario"])[0])
            if parts[:1] == ["api"]:
                return self._api(parts, query)
            if len(parts) == 4 and parts[0] == "practices" and parts[2] == "tasks":
                return self._task_card(self._practice(parts[1]), parts[3])
            if len(parts) == 2 and parts[0] == "validate":
                return self._validator(self._practice(parts[1]))
            if len(parts) == 2 and parts[0] == "practices":
                return self._manager(self._practice(parts[1]))
            self._send(page("Non trovato", "<p>Risorsa non trovata.</p>"), HTTPStatus.NOT_FOUND)
        except WorkflowError as error:
            self._send(page("Errore", f"<p>{error}</p>"), HTTPStatus.BAD_REQUEST)

    def do_POST(self):
        parts = [part for part in urlparse(self.path).path.split("/") if part]
        form = self._form()
        try:
            if len(parts) == 5 and parts[0] == "practices" and parts[2] == "tasks" and parts[4] == "complete":
                practice = self._practice(parts[1])
                complete_task(practice, parts[3], form.get("actor", ["mario"])[0], form.get("outcome", [""])[0], form.get("note", [""])[0], _attachments(form))
                return self._redirect(f"/practices/{practice.id}/tasks/{parts[3]}")
            if len(parts) == 3 and parts[0] == "validate" and parts[2] == "submit":
                practice = self._practice(parts[1])
                validate_practice(practice, form.get("actor", ["valeria"])[0], outcome=form.get("outcome", [""])[0], note=form.get("note", [""])[0], attachments=_attachments(form))
                return self._redirect(f"/validate/{practice.id}")
            if len(parts) == 3 and parts[0] == "practices" and parts[2] == "close":
                practice = self._practice(parts[1])
                close_practice(practice, form.get("actor", ["manager"])[0], outcome=form.get("outcome", [""])[0], note=form.get("note", [""])[0], attachments=_attachments(form))
                return self._redirect(f"/practices/{practice.id}")
            if len(parts) == 5 and parts[0] == "practices" and parts[2] == "tasks" and parts[4] == "reopen":
                practice = self._practice(parts[1])
                reopen_task(practice, parts[3], form.get("actor", ["manager"])[0], Role.MANAGER)
                return self._redirect(f"/practices/{practice.id}")
            self._send(page("Non trovato", "<p>Azione non trovata.</p>"), HTTPStatus.NOT_FOUND)
        except WorkflowError as error:
            self._send(page("Operazione rifiutata", f"<p>{error}</p>"), HTTPStatus.CONFLICT)

    def _work_queue(self, actor: str):
        rows = "".join(f"<tr><td>{practice.client_name}</td><td>{task.title}</td><td>{practice.due_date}</td><td><a class='button' href='/practices/{practice.id}/tasks/{task.code}'>Apri</a></td></tr>" for practice, task in operator_work_queue(self.store.all(), actor))
        body = f"<div class='card'><p>Operatore: <strong>{actor}</strong></p><p><a href='/?actor=mario'>Mario</a> · <a href='/?actor=anna'>Anna</a></p><table><thead><tr><th>Cliente</th><th>Attività</th><th>Scadenza</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>"
        self._send(page("Work Queue personale", body))

    def _task_card(self, practice, code):
        task = next((item for item in practice.tasks if item.code == code), None)
        if task is None: raise WorkflowError("Task inesistente")
        dependencies = ", ".join(task.depends_on) or "Nessuna"
        previous = [item for item in practice.dossier if item.task_code != code]
        result = task.result
        if result:
            result_area = f"<p><strong>Outcome:</strong> {result.outcome}</p><p><strong>Nota:</strong> {result.note}</p>{evidence_list(result.attachments)}"
        else:
            result_area = result_fields(f"/practices/{practice.id}/tasks/{code}/complete", "Completa attività").replace(
                ">\n<label for='outcome'>", f"><input type='hidden' name='actor' value='{task.assigned_to or 'mario'}'>\n<label for='outcome'>", 1
            )
        body = f"<section class='card'><h2>Cosa devi fare</h2><p>{task.title}</p></section><div class='grid'><section class='card'><h2>Cliente e pratica</h2><p>{practice.client_name} · {practice.id}</p><p>Scadenza {task.due_date or practice.due_date} · Priorità {task.priority or 'ordinaria'}</p></section><section class='card'><h2>Contesto pratica</h2><p>{practice.context}</p><p>Dipendenze: {dependencies}</p></section></div><section class='card instructions'><h2>Istruzioni operative</h2><p>{task.instructions}</p></section><section class='card'><h2>Materiale precedente</h2>{evidence_list(previous)}</section><section class='card'><h2>Risultato attività</h2>{result_area}</section>"
        self._send(page(f"Scheda Task · {code}", body))

    def _validator(self, practice):
        rows = "".join(task_row(practice, task) for task in practice.tasks if task.completed_by)
        if practice.validation_result is None:
            form = result_fields(f"/validate/{practice.id}/submit", "Valida pratica")
        else:
            result = practice.validation_result
            form = f"<p><strong>Outcome:</strong> {result.outcome}</p><p><strong>Nota:</strong> {result.note}</p>{evidence_list(result.attachments)}"
        self._send(page("Vista Validatore", f"<section class='card'><h2>{practice.client_name} · {practice.id}</h2><p>Stato: {practice.status.value}</p></section><section class='card'><h2>Task completati</h2><table><tr><th>Task</th><th>Assegnato</th><th>Stato</th><th>Completato da</th><th>Risultato / nota</th><th>Evidenze</th></tr>{rows}</table></section><section class='card'><h2>Esito validazione</h2>{form}</section>"))

    def _manager(self, practice):
        rows = "".join(task_row(practice, task, True) for task in practice.tasks)
        validation = practice.validation_result
        closure = practice.closure_result
        close_form = result_fields(f"/practices/{practice.id}/close", "Chiudi pratica") if closure is None else f"<p><strong>Outcome:</strong> {closure.outcome}</p><p><strong>Nota:</strong> {closure.note}</p>{evidence_list(closure.attachments)}"
        audit = "".join(f"<div class='audit'>{event.at.isoformat()} · {event.event_type} · {event.actor}</div>" for event in practice.audit)
        self._send(page("Scheda Pratica Manager", f"<section class='card'><h2>{practice.client_name} · {practice.id}</h2><p>Stato: {practice.status.value}</p></section><section class='card'><h2>Task e risultati</h2><table><tr><th>Task</th><th>Assegnato</th><th>Stato</th><th>Completato da</th><th>Risultato / nota</th><th>Evidenze</th></tr>{rows}</table></section><div class='grid'><section class='card'><h2>Risultato validazione</h2><p>{validation.outcome if validation else 'Non disponibile'}</p><p>{validation.note if validation else ''}</p>{evidence_list(validation.attachments) if validation else ''}</section><section class='card'><h2>Chiusura manageriale</h2>{close_form}</section></div><section class='card'><h2>Fascicolo</h2>{evidence_list(practice.dossier)}</section><section class='card'><h2>Audit (separato dal fascicolo)</h2>{audit or '<p>Nessun evento.</p>'}</section>"))

    def _api(self, parts, query):
        if parts == ["api", "work-queue"]:
            actor = query.get("actor", ["mario"])[0]
            data = [{"practice_id": p.id, "task": task_detail(p, t.code)} for p, t in operator_work_queue(self.store.all(), actor)]
        elif len(parts) == 5 and parts[1] == "practices" and parts[3] == "tasks":
            data = task_detail(self._practice(parts[2]), parts[4])
        elif len(parts) == 4 and parts[1] == "practices" and parts[3] == "validation":
            data = validator_view(self._practice(parts[2]))
        elif len(parts) == 3 and parts[1] == "practices":
            data = manager_practice_view(self._practice(parts[2]))
        else:
            return self._send(json.dumps({"error": "not found"}), HTTPStatus.NOT_FOUND, "application/json")
        self._send(json.dumps(_jsonable(data)), content_type="application/json")


def main():
    parser = argparse.ArgumentParser(description="WMS web demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"WMS v0.3 disponibile su http://{args.host}:{args.port}")
    try:
        ThreadingHTTPServer((args.host, args.port), WMSHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nWMS arrestato")


if __name__ == "__main__":
    main()
