from __future__ import annotations

from datetime import datetime
from threading import RLock

from backend.wms_core.models import AuditEvent, Evidence, Practice, Task, UserRole, WorkResult
from backend.wms_core.templates import build_lipe_trim_tasks
from backend.wms_core.workflow import (
    assign_task,
    close_practice,
    complete_task,
    reopen_task,
    validate_practice,
)


DEMO_PRACTICE_ID = "P-2026-LIPE-001"
DEMO_USERS = {
    "anna.operatore": UserRole.OPERATORE,
    "luca.operatore": UserRole.OPERATORE,
    "valeria.validatore": UserRole.VALIDATORE,
    "marta.manager": UserRole.MANAGER,
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
    assignees = ("anna.operatore", "luca.operatore")
    for index, task in enumerate(practice.tasks):
        assign_task(
            practice,
            task.code,
            assignees[index % len(assignees)],
            actor="marta.manager",
            actor_role=UserRole.MANAGER,
        )
    return practice


def _date(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _task(task: Task) -> dict[str, object]:
    return {
        "code": task.code,
        "title": task.title,
        "required": task.required,
        "status": task.status.value,
        "assignee": task.assignee,
        "completed_by": task.completed_by,
        "depends_on": list(task.depends_on),
        "result_id": task.result_id,
    }


def _event(event: AuditEvent) -> dict[str, object]:
    return {
        "event_type": event.event_type,
        "actor": event.actor,
        "at": _date(event.at),
        "details": event.details,
    }


def _result(result: WorkResult) -> dict[str, object]:
    return {
        "id": result.id, "actor": result.actor, "actor_role": result.actor_role.value,
        "timestamp": _date(result.timestamp), "outcome": result.outcome, "note": result.note,
        "evidence_ids": list(result.evidence_ids),
        "related_practice_id": result.related_practice_id,
        "related_task_code": result.related_task_code, "action": result.action,
    }


def _evidence(item: Evidence) -> dict[str, object]:
    return {
        "id": item.id, "filename": item.filename, "content_type": item.content_type,
        "actor": item.actor, "actor_role": item.actor_role.value,
        "created_at": _date(item.created_at), "source": item.source,
        "related_task_code": item.related_task_code,
    }


def serialize_practice(practice: Practice) -> dict[str, object]:
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
        "roles": {
            "validator": "valeria.validatore",
            "manager": "marta.manager",
        },
    }


class PracticeService:
    """Application boundary: identities and demo data stay outside WMS Core."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._practices = {DEMO_PRACTICE_ID: build_demo_practice()}

    def _role(self, actor: str) -> UserRole:
        try:
            return DEMO_USERS[actor]
        except KeyError as error:
            raise PermissionError(f"Utente demo sconosciuto: {actor}") from error

    def get(self, practice_id: str) -> dict[str, object]:
        with self._lock:
            return serialize_practice(self._find(practice_id))

    def work_queue(self, operator: str) -> list[dict[str, object]]:
        if self._role(operator) != UserRole.OPERATORE:
            raise PermissionError("La work queue è riservata agli operatori")
        with self._lock:
            return [
                {
                    "practice_id": practice.id,
                    "practice_type_code": practice.practice_type_code,
                    "client_id": practice.client_id,
                    "due_date": practice.due_date,
                    **_task(task),
                }
                for practice in self._practices.values()
                for task in practice.tasks
                if task.assignee == operator and task.status.value != "COMPLETATO"
            ]

    def task_detail(self, practice_id: str, task_code: str, operator: str, include_context: bool = False) -> dict[str, object]:
        if self._role(operator) != UserRole.OPERATORE:
            raise PermissionError("L'attività è riservata agli operatori")
        with self._lock:
            practice = self._find(practice_id)
            task = self._find_task(practice, task_code)
            if task.assignee != operator:
                raise PermissionError("Attività non assegnata all'operatore")
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
            }
            if include_context:
                detail["previous_results"] = [
                    _result(result) for result in practice.results
                    if result.related_task_code != task.code
                ]
                detail["evidence"] = [_evidence(item) for item in practice.evidence]
            return detail

    def complete_task(self, practice_id: str, task_code: str, actor: str,
                      outcome: str = "COMPLETATO", note: str = "",
                      attachments: list[dict[str, str]] | None = None) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            complete_task(practice, task_code, actor, self._role(actor), outcome, note, attachments)
            return serialize_practice(practice)

    def assign_task(self, practice_id: str, task_code: str, assignee: str, actor: str) -> dict[str, object]:
        if self._role(assignee) != UserRole.OPERATORE:
            raise PermissionError("L'assegnatario deve avere ruolo OPERATORE")
        with self._lock:
            practice = self._find(practice_id)
            assign_task(practice, task_code, assignee, actor, self._role(actor))
            return serialize_practice(practice)

    def reopen_task(self, practice_id: str, task_code: str, actor: str) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            reopen_task(practice, task_code, actor, self._role(actor))
            return serialize_practice(practice)

    def validate(self, practice_id: str, actor: str, outcome: str = "VALIDATA",
                 note: str = "", attachments: list[dict[str, str]] | None = None) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            validate_practice(practice, actor, self._role(actor), outcome, note, attachments)
            return serialize_practice(practice)

    def close(self, practice_id: str, actor: str, outcome: str = "CHIUSA",
              note: str = "", attachments: list[dict[str, str]] | None = None) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            close_practice(practice, actor, self._role(actor), outcome, note, attachments)
            return serialize_practice(practice)

    def _find(self, practice_id: str) -> Practice:
        try:
            return self._practices[practice_id]
        except KeyError as error:
            raise KeyError(f"Pratica inesistente: {practice_id}") from error

    @staticmethod
    def _find_task(practice: Practice, task_code: str) -> Task:
        task = next((task for task in practice.tasks if task.code == task_code), None)
        if task is None:
            raise KeyError(f"Task inesistente: {task_code}")
        return task
