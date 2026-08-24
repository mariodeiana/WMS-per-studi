"""Framework-neutral API representations used by future HTTP adapters and UI views."""

from __future__ import annotations

from dataclasses import asdict

from .models import Practice
from .workflow import WorkflowError


def _task(practice: Practice, task_code: str):
    task = next((item for item in practice.tasks if item.code == task_code), None)
    if task is None:
        raise WorkflowError(f"Task inesistente: {task_code}")
    return task


def task_detail(practice: Practice, task_code: str) -> dict:
    """Task Context in the display order required by the operator card."""
    task = _task(practice, task_code)
    return {
        "work": {"code": task.code, "title": task.title, "status": task.status.value},
        "practice": {"id": practice.id, "type": practice.practice_type_code},
        "client": {"id": practice.client_id, "name": practice.client_name},
        "schedule": {"due_date": task.due_date or practice.due_date, "priority": task.priority},
        "instructions": task.instructions,
        "context": dict(practice.context),
        "depends_on": list(task.depends_on),
        "previous_evidence": [asdict(item) for item in practice.dossier if item.task_code != task.code],
        "outcome": task.result.outcome if task.result else None,
        "note": task.result.note if task.result else "",
        "evidence": [asdict(item) for item in task.result.attachments] if task.result else [],
        "action": "Completa attività",
    }


def validator_view(practice: Practice) -> dict:
    return {
        "practice": {"id": practice.id, "client_id": practice.client_id, "status": practice.status.value},
        "completed_tasks": [
            {
                "code": task.code,
                "title": task.title,
                "completed_by": task.completed_by,
                "outcome": task.result.outcome if task.result else None,
                "note": task.result.note if task.result else "",
                "evidence": [asdict(item) for item in task.result.attachments] if task.result else [],
            }
            for task in practice.tasks if task.completed_by
        ],
        "validation": asdict(practice.validation_result) if practice.validation_result else None,
        "action": "Valida pratica",
    }


def manager_practice_view(practice: Practice) -> dict:
    return {
        "practice": {"id": practice.id, "client_id": practice.client_id, "status": practice.status.value},
        "tasks": [
            {
                "code": task.code, "assigned_to": task.assigned_to, "status": task.status.value,
                "completed_by": task.completed_by, "note": task.result.note if task.result else "",
                "evidence": [asdict(item) for item in task.result.attachments] if task.result else [],
            } for task in practice.tasks
        ],
        "validation_result": asdict(practice.validation_result) if practice.validation_result else None,
        "closure_result": asdict(practice.closure_result) if practice.closure_result else None,
        "dossier": [asdict(item) for item in practice.dossier],
        "audit": [asdict(event) for event in practice.audit],
    }
