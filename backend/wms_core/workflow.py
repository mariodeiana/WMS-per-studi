from __future__ import annotations

from datetime import datetime, timezone

from .models import Practice, PracticeStatus, TaskStatus


class WorkflowError(ValueError):
    pass


def _transition(practice: Practice, target: PracticeStatus, actor: str) -> None:
    previous = practice.status
    practice.status = target
    practice.record("PRACTICE_STATUS_CHANGED", actor, previous=previous.value, current=target.value)


def start_practice(practice: Practice, actor: str) -> None:
    if practice.status != PracticeStatus.DA_FARE:
        raise WorkflowError("La pratica può essere avviata solo da DA_FARE")
    _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor)


def complete_task(practice: Practice, task_code: str, actor: str) -> None:
    if practice.status not in {PracticeStatus.IN_LAVORAZIONE, PracticeStatus.DA_FARE}:
        raise WorkflowError("I task non possono essere completati nello stato corrente")

    task = next((item for item in practice.tasks if item.code == task_code), None)
    if task is None:
        raise WorkflowError(f"Task inesistente: {task_code}")

    if practice.status == PracticeStatus.DA_FARE:
        start_practice(practice, actor)

    task.status = TaskStatus.COMPLETATO
    practice.record("TASK_COMPLETED", actor, task_code=task.code)

    if practice.required_tasks_complete:
        _transition(practice, PracticeStatus.COMPLETATA, actor)
        if practice.requires_validation:
            _transition(practice, PracticeStatus.DA_VALIDARE, actor)


def request_validation(practice: Practice, actor: str) -> None:
    if practice.status != PracticeStatus.COMPLETATA:
        raise WorkflowError("La validazione può essere richiesta solo da COMPLETATA")
    if not practice.requires_validation:
        raise WorkflowError("Il tipo di pratica non richiede validazione")
    _transition(practice, PracticeStatus.DA_VALIDARE, actor)


def validate_practice(practice: Practice, actor: str, actor_can_validate: bool) -> None:
    if practice.status != PracticeStatus.DA_VALIDARE:
        raise WorkflowError("La pratica non è in attesa di validazione")
    if not actor_can_validate:
        raise WorkflowError("L'utente non è autorizzato alla validazione")

    practice.validated_by = actor
    practice.validated_at = datetime.now(timezone.utc)
    _transition(practice, PracticeStatus.VALIDATA, actor)
    practice.record("PRACTICE_VALIDATED", actor)


def close_practice(practice: Practice, actor: str) -> None:
    allowed = PracticeStatus.VALIDATA if practice.requires_validation else PracticeStatus.COMPLETATA
    if practice.status != allowed:
        raise WorkflowError("La pratica non può essere chiusa nello stato corrente")
    _transition(practice, PracticeStatus.CHIUSA, actor)
