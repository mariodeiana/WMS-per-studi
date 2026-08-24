from __future__ import annotations

from datetime import datetime
from threading import RLock

from backend.wms_core.models import AuditEvent, Practice, Task
from backend.wms_core.templates import build_lipe_trim_tasks
from backend.wms_core.workflow import close_practice, complete_task, reopen_task, validate_practice


DEMO_PRACTICE_ID = "P-2026-LIPE-001"


def build_demo_practice() -> Practice:
    """Build the local demo using only WMS Core domain objects."""
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
    return practice


def _date(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _task(task: Task) -> dict[str, object]:
    return {
        "code": task.code,
        "title": task.title,
        "required": task.required,
        "status": task.status.value,
    }


def _event(event: AuditEvent) -> dict[str, object]:
    return {
        "event_type": event.event_type,
        "actor": event.actor,
        "at": _date(event.at),
        "details": event.details,
    }


def serialize_practice(practice: Practice, assignments: dict[str, str] | None = None) -> dict[str, object]:
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
        "assignments": assignments or {},
    }


class PracticeService:
    """Application boundary around the management-system-agnostic WMS Core."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._practices = {DEMO_PRACTICE_ID: build_demo_practice()}
        # Demo presentation data belongs to the application layer, not WMS Core.
        self._assignments = {
            DEMO_PRACTICE_ID: {
                "responsible": "Dott.ssa Giulia Bianchi",
                "operator": "Marco Rossi",
            }
        }

    def get(self, practice_id: str) -> dict[str, object]:
        with self._lock:
            return self._serialize(self._find(practice_id))

    def complete_task(self, practice_id: str, task_code: str, actor: str) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            complete_task(practice, task_code, actor)
            return self._serialize(practice)

    def reopen_task(self, practice_id: str, task_code: str, actor: str) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            reopen_task(practice, task_code, actor)
            return self._serialize(practice)

    def validate(self, practice_id: str, actor: str, actor_can_validate: bool) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            validate_practice(practice, actor, actor_can_validate=actor_can_validate)
            return self._serialize(practice)

    def close(self, practice_id: str, actor: str) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            close_practice(practice, actor)
            return self._serialize(practice)

    def _serialize(self, practice: Practice) -> dict[str, object]:
        return serialize_practice(practice, self._assignments.get(practice.id))

    def _find(self, practice_id: str) -> Practice:
        try:
            return self._practices[practice_id]
        except KeyError as error:
            raise KeyError(f"Pratica inesistente: {practice_id}") from error
