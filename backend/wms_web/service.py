from __future__ import annotations

from datetime import datetime
from threading import RLock

from backend.wms_core.models import AuditEvent, Practice, Task
from backend.wms_core.templates import build_lipe_trim_tasks
from backend.wms_core.workflow import close_practice, complete_task, validate_practice


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
    }


class PracticeService:
    """Application boundary around the management-system-agnostic WMS Core."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._practices = {DEMO_PRACTICE_ID: build_demo_practice()}

    def get(self, practice_id: str) -> dict[str, object]:
        with self._lock:
            return serialize_practice(self._find(practice_id))

    def complete_task(self, practice_id: str, task_code: str, actor: str) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            complete_task(practice, task_code, actor)
            return serialize_practice(practice)

    def validate(self, practice_id: str, actor: str) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            validate_practice(practice, actor, actor_can_validate=True)
            return serialize_practice(practice)

    def close(self, practice_id: str, actor: str) -> dict[str, object]:
        with self._lock:
            practice = self._find(practice_id)
            close_practice(practice, actor)
            return serialize_practice(practice)

    def _find(self, practice_id: str) -> Practice:
        try:
            return self._practices[practice_id]
        except KeyError as error:
            raise KeyError(f"Pratica inesistente: {practice_id}") from error
