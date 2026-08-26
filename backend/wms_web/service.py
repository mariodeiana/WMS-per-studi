from __future__ import annotations

import base64
import pickle
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import RLock

from backend.wms_core.models import Practice, UserRole
from backend.wms_core.templates import PRACTICE_TEMPLATES, build_lipe_trim_tasks, build_tasks
from backend.wms_core.workflow import (
    assign_task,
    close_practice,
    complete_task,
    reopen_task,
    save_task_progress,
    validate_practice,
)

DEMO_PRACTICE_ID = "P-2026-LIPE-001"
RECENT_COMPLETED_HOURS = 8
DEMO_USERS = {
    "anna.operatore": UserRole.OPERATORE,
    "luca.operatore": UserRole.OPERATORE,
    "valeria.validatore": UserRole.VALIDATORE,
    "marta.manager": UserRole.MANAGER,
}

DEMO_CLIENTS = ["CLIENT-001", "CLIENT-002", "CLIENT-003", "CLIENT-004", "CLIENT-005"]
DEMO_PRACTICE_TYPES = ["LIPE_TRIM", "F24_MENSILE", "RICONC_BANCA", "CU_ANNUALE", "BILANCIO_VER"]
DEMO_TYPE_ID = {
    "LIPE_TRIM": "LIPE",
    "F24_MENSILE": "F24",
    "RICONC_BANCA": "RICONC",
    "CU_ANNUALE": "CU",
    "BILANCIO_VER": "BIL",
}


def build_demo_practice() -> Practice:
    practice = Practice(
        id=DEMO_PRACTICE_ID,
        practice_type_code="LIPE_TRIM",
        client_id="CLIENT-001",
        period_start="2026-04-01",
        period_end="2026-06-30",
        due_date="2026-09-30",
        tasks=build_lipe_trim_tasks(),
    )
    practice.record("PRACTICE_CREATED", "sistema", source="demo-locale")
    _assign_demo_tasks(practice)
    return practice


def _assign_demo_tasks(practice: Practice) -> None:
    assignees = ("anna.operatore", "luca.operatore")
    for index, task in enumerate(practice.tasks):
        assign_task(practice, task.code, assignees[index % 2], "marta.manager", UserRole.MANAGER)


def _demo_attachment(filename: str, text: str) -> list[dict[str, str]]:
    return [{
        "filename": filename,
        "content_type": "text/plain",
        "document_type": "DOCUMENTO",
        "description": "Documento dimostrativo",
        "content_base64": base64.b64encode(text.encode("utf-8")).decode("ascii"),
    }]


def _complete_demo_task(practice: Practice, index: int, *, warning: bool = False) -> None:
    task = practice.tasks[index]
    outcome = "CON_RILIEVI" if warning else "POSITIVO"
    note = "Verifica completata con anomalia da monitorare" if warning else "Verifica completata"
    complete_task(
        practice,
        task.code,
        task.assignee or "anna.operatore",
        UserRole.OPERATORE,
        outcome=outcome,
        note=note,
        attachments=_demo_attachment(
            f"{practice.id}-{task.code}.txt",
            f"Evidenza demo per {practice.id} / {task.code}",
        ),
    )


def _stage_demo_practice(practice: Practice, stage: int, sequence: int) -> None:
    # 0 DA_FARE, 1 IN_LAVORAZIONE, 2 DA_VALIDARE, 3 NON_VALIDATA, 4 VALIDATA
    if stage == 0:
        return
    if stage == 1:
        completed = min(2, max(0, len(practice.tasks) - 1))
        for index in range(completed):
            _complete_demo_task(practice, index, warning=(sequence % 4 == 0 and index == 1))
        current = practice.tasks[completed]
        save_task_progress(
            practice,
            current.code,
            current.assignee or "anna.operatore",
            UserRole.OPERATORE,
            note="Lavorazione avviata, in attesa di completamento",
            attachments=_demo_attachment(
                f"{practice.id}-{current.code}-parziale.txt",
                "Documento acquisito durante la lavorazione",
            ),
        )
        return

    for index in range(len(practice.tasks)):
        _complete_demo_task(
            practice,
            index,
            warning=(index == 1 and sequence % 3 == 0),
        )

    if stage == 2:
        return
    if stage == 3:
        validate_practice(
            practice,
            "valeria.validatore",
            UserRole.VALIDATORE,
            outcome="NON_VALIDATA",
            note="Quadrature non sufficientemente documentate: verifica richiesta al manager.",
            attachments=_demo_attachment(
                f"{practice.id}-rilievo-validazione.txt",
                "Rilievo del validatore: la pratica richiede intervento manageriale.",
            ),
        )
        return
    validate_practice(
        practice,
        "valeria.validatore",
        UserRole.VALIDATORE,
        outcome="VALIDATA_CON_RILIEVI" if sequence % 2 == 0 else "VALIDATA",
        note="Validata con osservazioni non bloccanti." if sequence % 2 == 0 else "",
    )


def build_rich_demo_practices() -> dict[str, Practice]:
    practices: dict[str, Practice] = {}
    sequence = 0
    for client_index, client_id in enumerate(DEMO_CLIENTS, start=1):
        for type_index, practice_type in enumerate(DEMO_PRACTICE_TYPES):
            sequence += 1
            if client_index == 1 and practice_type == "LIPE_TRIM":
                continue
            practice_id = f"P-2026-{DEMO_TYPE_ID[practice_type]}-{client_index:03}"
            due = date(2026, 8, 18) + timedelta(days=((client_index - 1) * 7 + type_index * 5))
            period_start = "2026-07-01" if practice_type != "CU_ANNUALE" else "2025-01-01"
            period_end = "2026-07-31" if practice_type != "CU_ANNUALE" else "2025-12-31"
            practice = Practice(
                id=practice_id,
                practice_type_code=practice_type,
                client_id=client_id,
                period_start=period_start,
                period_end=period_end,
                due_date=due.isoformat(),
                tasks=build_tasks(practice_type),
            )
            practice.record("PRACTICE_CREATED", "sistema", source="demo-riepilogo")
            _assign_demo_tasks(practice)
            stage = (sequence - 1) % 5
            _stage_demo_practice(practice, stage, sequence)
            practices[practice.id] = practice
    return practices


def _date(value):
    return value.isoformat() if value else None


def _task(task):
    return {
        "code": task.code,
        "title": task.title,
        "instructions": task.instructions,
        "required": task.required,
        "status": task.status.value,
        "assignee": task.assignee,
        "completed_by": task.completed_by,
        "depends_on": list(task.depends_on),
        "result_id": task.result_id,
        "work_note": task.work_note,
        "work_notes": [{"actor": n.actor, "note": n.note, "at": _date(n.at)} for n in task.work_notes],
        "progress_evidence_ids": list(task.progress_evidence_ids),
        "reopen_reason": task.reopen_reason,
    }


def _event(event):
    return {"event_type": event.event_type, "actor": event.actor, "at": _date(event.at), "details": event.details}


def _result(result):
    return {
        "id": result.id,
        "actor": result.actor,
        "actor_role": result.actor_role.value,
        "timestamp": _date(result.timestamp),
        "outcome": result.outcome,
        "note": result.note,
        "evidence_ids": list(result.evidence_ids),
        "related_practice_id": result.related_practice_id,
        "related_task_code": result.related_task_code,
        "action": result.action,
    }


def _evidence(item):
    return {
        "id": item.id,
        "filename": item.filename,
        "content_type": item.content_type,
        "description": item.description,
        "document_type": item.document_type,
        "size_bytes": item.size_bytes,
        "actor": item.actor,
        "actor_role": item.actor_role.value,
        "created_at": _date(item.created_at),
        "source": item.source,
        "related_practice_id": item.related_practice_id,
        "related_task_code": item.related_task_code,
        "preview_url": f"/api/evidence/{item.id}?disposition=inline",
        "download_url": f"/api/evidence/{item.id}?disposition=attachment",
    }


def serialize_practice(practice):
    completed = sum(task.status.value == "COMPLETATO" for task in practice.tasks)
    return {
        "id": practice.id,
        "practice_type_code": practice.practice_type_code,
        "client_id": practice.client_id,
        "period_start": practice.period_start,
        "period_end": practice.period_end,
        "due_date": practice.due_date,
        "requires_validation": practice.requires_validation,
        "status": practice.status.value,
        "tasks": [_task(task) for task in practice.tasks],
        "progress": {"completed": completed, "total": len(practice.tasks)},
        "audit": [_event(event) for event in reversed(practice.audit)],
        "validated_by": practice.validated_by,
        "validated_at": _date(practice.validated_at),
        "results": [_result(result) for result in reversed(practice.results)],
        "evidence": [_evidence(item) for item in reversed(practice.evidence)],
        "validation_result_id": practice.validation_result_id,
        "closure_result_id": practice.closure_result_id,
        "roles": {"validator": "valeria.validatore", "manager": "marta.manager"},
    }


def _summary(practice):
    total = len(practice.tasks)
    completed = sum(task.status.value == "COMPLETATO" for task in practice.tasks)
    reopened = sum(bool(task.reopen_reason) and task.status.value != "COMPLETATO" for task in practice.tasks)
    in_progress = sum(task.status.value == "IN_LAVORAZIONE" for task in practice.tasks)
    warnings = sum("RILIEVI" in str(result.outcome) for result in practice.results if result.action == "TASK")
    if practice.status.value == "NON_VALIDATA":
        validation = next((r for r in reversed(practice.results) if r.action == "VALIDATION"), None)
        situation = {"code": "NOT_VALIDATED", "label": "Non validata", "detail": validation.note if validation else ""}
    elif reopened:
        situation = {"code": "REOPENED", "label": f"{reopened} task riaperto" if reopened == 1 else f"{reopened} task riaperti"}
    elif warnings:
        situation = {"code": "WARNINGS", "label": f"{warnings} task con rilievi"}
    elif in_progress:
        situation = {"code": "IN_PROGRESS", "label": f"{in_progress} task in corso"}
    else:
        situation = {"code": "REGULAR", "label": "Regolare"}
    due = date.fromisoformat(practice.due_date)
    days = (due - date.today()).days
    if days < 0:
        urgency = {"level": "OVERDUE", "label": "In ritardo", "detail": f"{abs(days)} gg"}
    elif days <= 7:
        urgency = {"level": "HIGH", "label": "Alta", "detail": f"{days} gg"}
    elif days <= 30:
        urgency = {"level": "MEDIUM", "label": "Media", "detail": f"{days} gg"}
    else:
        urgency = {"level": "LOW", "label": "Bassa", "detail": f"{days} gg"}
    return {
        "id": practice.id,
        "practice_type_code": practice.practice_type_code,
        "client_id": practice.client_id,
        "period_start": practice.period_start,
        "period_end": practice.period_end,
        "due_date": practice.due_date,
        "status": practice.status.value,
        "progress": {"completed": completed, "total": total, "percent": round(100 * completed / total) if total else 0},
        "situation": situation,
        "urgency": urgency,
        "urgency_sort": days,
    }


class PracticeService:
    def __init__(self, state_path=None, rich_demo: bool = False):
        self._lock = RLock()
        self._state_path = Path(state_path) if state_path else None
        self._practices = self._load_state() if self._state_path and self._state_path.exists() else {DEMO_PRACTICE_ID: build_demo_practice()}
        if rich_demo:
            changed = False
            for practice_id, practice in build_rich_demo_practices().items():
                if practice_id not in self._practices:
                    self._practices[practice_id] = practice
                    changed = True
            if changed:
                self._persist()

    def _load_state(self):
        try:
            with self._state_path.open("rb") as handle:
                state = pickle.load(handle)
            if not isinstance(state, dict) or not all(isinstance(item, Practice) for item in state.values()):
                raise ValueError("formato stato demo non valido")
            return state
        except Exception as error:
            raise RuntimeError(f"Impossibile caricare lo stato demo da {self._state_path}: {error}") from error

    def _persist(self):
        if not self._state_path:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        with temporary.open("wb") as handle:
            pickle.dump(self._practices, handle, pickle.HIGHEST_PROTOCOL)
        temporary.replace(self._state_path)

    def _role(self, actor):
        try:
            return DEMO_USERS[actor]
        except KeyError as error:
            raise PermissionError(f"Utente demo sconosciuto: {actor}") from error

    def get(self, practice_id):
        with self._lock:
            return serialize_practice(self._find(practice_id))

    def manager_practices(self, actor):
        if self._role(actor) != UserRole.MANAGER:
            raise PermissionError("La lista pratiche è riservata al manager")
        with self._lock:
            return sorted(
                [_summary(practice) for practice in self._practices.values() if practice.status.value != "CHIUSA"],
                key=lambda row: (row["urgency_sort"], row["due_date"], row["id"]),
            )

    def validation_queue(self, actor):
        if self._role(actor) != UserRole.VALIDATORE:
            raise PermissionError("La coda di validazione è riservata al validatore")
        with self._lock:
            rows = []
            for practice in self._practices.values():
                if practice.status.value != "DA_VALIDARE":
                    continue
                row = _summary(practice)
                entered = next(
                    (
                        event.at
                        for event in reversed(practice.audit)
                        if event.event_type == "PRACTICE_STATUS_CHANGED" and event.details.get("current") == "DA_VALIDARE"
                    ),
                    None,
                )
                row["waiting_since"] = _date(entered)
                row["waiting_hours"] = round((datetime.now(timezone.utc) - entered).total_seconds() / 3600, 1) if entered else None
                rows.append(row)
            return sorted(rows, key=lambda row: (row["urgency_sort"], row.get("waiting_since") or "", row["id"]))

    def work_queue(self, operator):
        if self._role(operator) != UserRole.OPERATORE:
            raise PermissionError("I miei compiti sono riservati agli operatori")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_COMPLETED_HOURS)
        rows = []
        with self._lock:
            for practice in self._practices.values():
                results = {result.id: result for result in practice.results}
                for task in practice.tasks:
                    if task.assignee != operator:
                        continue
                    row = {
                        "practice_id": practice.id,
                        "practice_type_code": practice.practice_type_code,
                        "client_id": practice.client_id,
                        "due_date": practice.due_date,
                        **_task(task),
                    }
                    if task.status.value != "COMPLETATO":
                        row["queue_section"] = "ACTIVE"
                        rows.append(row)
                        continue
                    result = results.get(task.result_id)
                    if result and result.actor == operator and result.timestamp >= cutoff:
                        row.update({
                            "queue_section": "RECENT_COMPLETED",
                            "completed_at": _date(result.timestamp),
                            "outcome": result.outcome,
                            "result_note": result.note,
                        })
                        rows.append(row)
            return rows

    def task_detail(self, practice_id, task_code, operator, include_context=False):
        if self._role(operator) != UserRole.OPERATORE:
            raise PermissionError("L'attività è riservata agli operatori")
        with self._lock:
            practice = self._find(practice_id)
            task = self._find_task(practice, task_code)
            if task.assignee != operator:
                raise PermissionError("Attività non assegnata all'operatore")
            evidences = {item.id: _evidence(item) for item in practice.evidence}
            journal = []
            for event in reversed(practice.audit):
                if event.details.get("task_code") != task.code:
                    continue
                if event.event_type == "TASK_PROGRESS_SAVED":
                    ids = event.details.get("evidence_ids") or []
                    journal.append({
                        "type": "PROGRESS",
                        "actor": event.actor,
                        "at": _date(event.at),
                        "note": event.details.get("note") or "",
                        "evidence": [evidences[eid] for eid in ids if eid in evidences],
                    })
                elif event.event_type == "TASK_REOPENED":
                    journal.append({"type": "REOPENED", "actor": event.actor, "at": _date(event.at), "note": event.details.get("reason") or "", "evidence": []})
            detail = {
                "practice": {
                    "id": practice.id,
                    "type": practice.practice_type_code,
                    "client_id": practice.client_id,
                    "period_start": practice.period_start,
                    "period_end": practice.period_end,
                    "due_date": practice.due_date,
                },
                "task": _task(task),
                "task_journal": journal,
                "task_progress_evidence": [evidences[eid] for eid in task.progress_evidence_ids if eid in evidences],
            }
            if include_context:
                titles = {item.code: item.title for item in practice.tasks}
                previous = []
                for result in practice.results:
                    if result.related_task_code == task.code:
                        continue
                    row = _result(result)
                    row["related_task_title"] = titles.get(result.related_task_code or "")
                    row["evidence"] = [evidences[eid] for eid in result.evidence_ids if eid in evidences]
                    previous.append(row)
                detail["previous_results"] = previous
                detail["evidence"] = [_evidence(item) for item in practice.evidence]
            return detail

    def evidence_content(self, evidence_id):
        with self._lock:
            for practice in self._practices.values():
                for item in practice.evidence:
                    if item.id == evidence_id:
                        return item
            raise KeyError(f"Evidenza inesistente: {evidence_id}")

    def save_task_progress(self, practice_id, task_code, actor, note="", attachments=None):
        with self._lock:
            practice = self._find(practice_id)
            save_task_progress(practice, task_code, actor, self._role(actor), note, attachments)
            self._persist()
            return serialize_practice(practice)

    def complete_task(self, practice_id, task_code, actor, outcome="COMPLETATO", note="", attachments=None):
        with self._lock:
            practice = self._find(practice_id)
            complete_task(practice, task_code, actor, self._role(actor), outcome, note, attachments)
            self._persist()
            return serialize_practice(practice)

    def assign_task(self, practice_id, task_code, assignee, actor):
        if self._role(assignee) != UserRole.OPERATORE:
            raise PermissionError("L'assegnatario deve avere ruolo OPERATORE")
        with self._lock:
            practice = self._find(practice_id)
            assign_task(practice, task_code, assignee, actor, self._role(actor))
            self._persist()
            return serialize_practice(practice)

    def reopen_task(self, practice_id, task_code, actor, reason=""):
        with self._lock:
            practice = self._find(practice_id)
            reopen_task(practice, task_code, actor, self._role(actor), reason)
            self._persist()
            return serialize_practice(practice)

    def validate(self, practice_id, actor, outcome="VALIDATA", note="", attachments=None):
        with self._lock:
            practice = self._find(practice_id)
            validate_practice(practice, actor, self._role(actor), outcome, note, attachments)
            self._persist()
            return serialize_practice(practice)

    def close(self, practice_id, actor, outcome="CHIUSA", note="", attachments=None):
        with self._lock:
            practice = self._find(practice_id)
            close_practice(practice, actor, self._role(actor), outcome, note, attachments)
            self._persist()
            return serialize_practice(practice)

    def _find(self, practice_id):
        try:
            return self._practices[practice_id]
        except KeyError as error:
            raise KeyError(f"Pratica inesistente: {practice_id}") from error

    @staticmethod
    def _find_task(practice, task_code):
        task = next((item for item in practice.tasks if item.code == task_code), None)
        if task is None:
            raise KeyError(f"Task inesistente: {task_code}")
        return task
