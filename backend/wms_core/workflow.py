from __future__ import annotations

from datetime import datetime, timezone

from .models import Practice, PracticeStatus, Task, TaskStatus, UserRole


class WorkflowError(ValueError):
    pass


def _transition(practice: Practice, target: PracticeStatus, actor: str) -> None:
    previous = practice.status
    practice.status = target
    practice.record("PRACTICE_STATUS_CHANGED", actor, previous=previous.value, current=target.value)


def _task(practice: Practice, task_code: str) -> Task:
    task = next((item for item in practice.tasks if item.code == task_code), None)
    if task is None:
        raise WorkflowError(f"Task inesistente: {task_code}")
    return task


def _require_role(actual: UserRole, expected: UserRole, message: str) -> None:
    if actual != expected:
        raise WorkflowError(message)


def assign_task(
    practice: Practice,
    task_code: str,
    assignee: str,
    actor: str,
    actor_role: UserRole,
) -> None:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può assegnare i task")
    if practice.status in {PracticeStatus.VALIDATA, PracticeStatus.CHIUSA}:
        raise WorkflowError("I task non possono essere assegnati dopo la validazione")
    task = _task(practice, task_code)
    if task.status == TaskStatus.COMPLETATO:
        raise WorkflowError("Un task completato deve essere riaperto prima di riassegnarlo")
    previous = task.assignee
    task.assignee = assignee
    practice.record("TASK_ASSIGNED", actor, task_code=task.code, previous=previous, assignee=assignee)


def start_practice(practice: Practice, actor: str) -> None:
    if practice.status != PracticeStatus.DA_FARE:
        raise WorkflowError("La pratica può essere avviata solo da DA_FARE")
    _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor)


def complete_task(practice: Practice, task_code: str, actor: str, actor_role: UserRole) -> None:
    _require_role(actor_role, UserRole.OPERATORE, "Solo un operatore può completare i task")
    if practice.status not in {PracticeStatus.IN_LAVORAZIONE, PracticeStatus.DA_FARE}:
        raise WorkflowError("I task non possono essere completati nello stato corrente")
    task = _task(practice, task_code)
    if task.assignee != actor:
        raise WorkflowError("Il task può essere completato solo dall'operatore assegnatario")
    if task.status == TaskStatus.COMPLETATO:
        raise WorkflowError("Il task è già completato")
    incomplete_dependencies = [
        code for code in task.depends_on if _task(practice, code).status != TaskStatus.COMPLETATO
    ]
    if incomplete_dependencies:
        raise WorkflowError(f"Dipendenze non completate: {', '.join(incomplete_dependencies)}")

    if practice.status == PracticeStatus.DA_FARE:
        start_practice(practice, actor)
    task.status = TaskStatus.COMPLETATO
    task.completed_by = actor
    practice.record("TASK_COMPLETED", actor, task_code=task.code)

    if practice.required_tasks_complete:
        _transition(practice, PracticeStatus.COMPLETATA, actor)
        if practice.requires_validation:
            _transition(practice, PracticeStatus.DA_VALIDARE, actor)


def reopen_task(practice: Practice, task_code: str, actor: str, actor_role: UserRole) -> None:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può riaprire i task")
    if practice.status not in {PracticeStatus.IN_LAVORAZIONE, PracticeStatus.DA_VALIDARE}:
        raise WorkflowError("I task possono essere riaperti solo prima della validazione")
    task = _task(practice, task_code)
    if task.status != TaskStatus.COMPLETATO:
        raise WorkflowError("Solo un task completato può essere riaperto")

    previous_completed_by = task.completed_by
    task.status = TaskStatus.IN_LAVORAZIONE
    task.completed_by = None
    practice.record(
        "TASK_REOPENED", actor, task_code=task.code, previous_completed_by=previous_completed_by
    )
    if practice.status == PracticeStatus.DA_VALIDARE:
        _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor)


def validate_practice(practice: Practice, actor: str, actor_role: UserRole) -> None:
    _require_role(actor_role, UserRole.VALIDATORE, "Solo un validatore può validare la pratica")
    if practice.status != PracticeStatus.DA_VALIDARE or not practice.required_tasks_complete:
        raise WorkflowError("La pratica non è pronta per la validazione")
    if any(event.event_type == "TASK_COMPLETED" and event.actor == actor for event in practice.audit):
        raise WorkflowError("Chi ha eseguito task della pratica non può validarla")

    practice.validated_by = actor
    practice.validated_at = datetime.now(timezone.utc)
    _transition(practice, PracticeStatus.VALIDATA, actor)
    practice.record("PRACTICE_VALIDATED", actor)


def close_practice(practice: Practice, actor: str, actor_role: UserRole) -> None:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può chiudere la pratica")
    allowed = PracticeStatus.VALIDATA if practice.requires_validation else PracticeStatus.COMPLETATA
    if practice.status != allowed:
        raise WorkflowError("La pratica non può essere chiusa nello stato corrente")
    _transition(practice, PracticeStatus.CHIUSA, actor)
    practice.record("PRACTICE_CLOSED", actor)
