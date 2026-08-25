from __future__ import annotations

from datetime import datetime, timezone

from .models import Evidence, Practice, PracticeStatus, Task, TaskStatus, UserRole, WorkResult


class WorkflowError(ValueError):
    pass


def _record_result(
    practice: Practice,
    *,
    actor: str,
    actor_role: UserRole,
    outcome: str,
    note: str,
    attachments: list[dict[str, str]] | None,
    action: str,
    task_code: str | None = None,
) -> WorkResult:
    outcome = outcome.strip()
    note = note.strip()
    if not outcome:
        raise WorkflowError("L'esito è obbligatorio")
    evidence_ids: list[str] = []
    for item in attachments or []:
        if not isinstance(item, dict):
            raise WorkflowError("Formato evidenza non valido")
        filename = str(item.get("filename", "")).strip()
        if not filename:
            raise WorkflowError("Ogni evidenza deve avere un nome file")
        evidence = Evidence(
            id=f"E-{len(practice.evidence) + 1:04}", filename=filename,
            content_type=str(item.get("content_type") or "application/octet-stream"),
            actor=actor, actor_role=actor_role, source=action,
            related_task_code=task_code,
        )
        practice.evidence.append(evidence)
        evidence_ids.append(evidence.id)
    result = WorkResult(
        id=f"R-{len(practice.results) + 1:04}", actor=actor,
        actor_role=actor_role, outcome=outcome, note=note,
        related_practice_id=practice.id, related_task_code=task_code,
        evidence_ids=tuple(evidence_ids), action=action,
    )
    practice.results.append(result)
    return result


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


def complete_task(practice: Practice, task_code: str, actor: str, actor_role: UserRole,
                  outcome: str = "COMPLETATO", note: str = "",
                  attachments: list[dict[str, str]] | None = None) -> None:
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
    result = _record_result(practice, actor=actor, actor_role=actor_role,
                            outcome=outcome, note=note, attachments=attachments,
                            action="TASK", task_code=task.code)
    task.status = TaskStatus.COMPLETATO
    task.completed_by = actor
    task.result_id = result.id
    practice.record("TASK_COMPLETED", actor, task_code=task.code, result_id=result.id)

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
    previous_result_id = task.result_id
    task.result_id = None
    practice.record(
        "TASK_REOPENED", actor, task_code=task.code, previous_completed_by=previous_completed_by,
        previous_result_id=previous_result_id,
    )
    if practice.status == PracticeStatus.DA_VALIDARE:
        _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor)


def validate_practice(practice: Practice, actor: str, actor_role: UserRole,
                      outcome: str = "VALIDATA", note: str = "",
                      attachments: list[dict[str, str]] | None = None) -> None:
    _require_role(actor_role, UserRole.VALIDATORE, "Solo un validatore può validare la pratica")
    if practice.status != PracticeStatus.DA_VALIDARE or not practice.required_tasks_complete:
        raise WorkflowError("La pratica non è pronta per la validazione")
    if any(event.event_type == "TASK_COMPLETED" and event.actor == actor for event in practice.audit):
        raise WorkflowError("Chi ha eseguito task della pratica non può validarla")

    result = _record_result(practice, actor=actor, actor_role=actor_role,
                            outcome=outcome, note=note, attachments=attachments,
                            action="VALIDATION")
    practice.validation_result_id = result.id
    practice.validated_by = actor
    practice.validated_at = datetime.now(timezone.utc)
    _transition(practice, PracticeStatus.VALIDATA, actor)
    practice.record("PRACTICE_VALIDATED", actor, result_id=result.id)


def close_practice(practice: Practice, actor: str, actor_role: UserRole,
                   outcome: str = "CHIUSA", note: str = "",
                   attachments: list[dict[str, str]] | None = None) -> None:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può chiudere la pratica")
    allowed = PracticeStatus.VALIDATA if practice.requires_validation else PracticeStatus.COMPLETATA
    if practice.status != allowed:
        raise WorkflowError("La pratica non può essere chiusa nello stato corrente")
    result = _record_result(practice, actor=actor, actor_role=actor_role,
                            outcome=outcome, note=note, attachments=attachments,
                            action="CLOSURE")
    practice.closure_result_id = result.id
    _transition(practice, PracticeStatus.CHIUSA, actor)
    practice.record("PRACTICE_CLOSED", actor, result_id=result.id)
