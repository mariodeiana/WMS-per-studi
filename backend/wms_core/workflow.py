from __future__ import annotations

from collections.abc import Iterable

from .models import Evidence, EvidenceInput, EvidenceOrigin, Practice, PracticeStatus, Task, TaskStatus, UserRole, WorkResult


class WorkflowError(ValueError):
    pass


def _transition(practice: Practice, target: PracticeStatus, actor: str, actor_role: UserRole | None = None) -> None:
    previous = practice.status
    practice.status = target
    practice.record("PRACTICE_STATUS_CHANGED", actor, actor_role, previous=previous.value, current=target.value)


def _task(practice: Practice, task_code: str) -> Task:
    task = next((item for item in practice.tasks if item.code == task_code), None)
    if task is None:
        raise WorkflowError(f"Task inesistente: {task_code}")
    return task


def _require_role(actual: UserRole, expected: UserRole, message: str) -> None:
    if actual != expected:
        raise WorkflowError(message)


def _evidence(inputs: Iterable[EvidenceInput | dict] | None, origin: EvidenceOrigin, actor: str, task_code: str | None = None) -> list[Evidence]:
    items = []
    for value in inputs or []:
        item = EvidenceInput(**value) if isinstance(value, dict) else value
        items.append(Evidence(name=item.name, content_ref=item.content_ref, metadata=dict(item.metadata), origin=origin, author=actor, task_code=task_code))
    return items


def assign_task(practice: Practice, task_code: str, assignee: str, actor: str, actor_role: UserRole) -> None:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può assegnare i task")
    if practice.status in {PracticeStatus.VALIDATA, PracticeStatus.CHIUSA}:
        raise WorkflowError("I task non possono essere assegnati dopo la validazione")
    task = _task(practice, task_code)
    if task.status == TaskStatus.COMPLETATO:
        raise WorkflowError("Un task completato deve essere riaperto prima di riassegnarlo")
    previous = task.assignee
    task.assignee = assignee
    practice.record("TASK_ASSIGNED", actor, actor_role, task_code=task.code, previous=previous, assignee=assignee)


def start_practice(practice: Practice, actor: str, actor_role: UserRole = UserRole.OPERATORE) -> None:
    _require_role(actor_role, UserRole.OPERATORE, "Solo un operatore può avviare la pratica")
    if practice.status != PracticeStatus.DA_FARE:
        raise WorkflowError("La pratica può essere avviata solo da DA_FARE")
    _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor, actor_role)


def complete_task(practice: Practice, task_code: str, actor: str, actor_role: UserRole = UserRole.OPERATORE, outcome: str = "COMPLETATO", note: str = "", attachments: Iterable[EvidenceInput | dict] | None = None) -> WorkResult:
    _require_role(actor_role, UserRole.OPERATORE, "Solo un operatore può completare i task")
    if practice.status not in {PracticeStatus.IN_LAVORAZIONE, PracticeStatus.DA_FARE}:
        raise WorkflowError("I task non possono essere completati nello stato corrente")
    task = _task(practice, task_code)
    if task.assignee != actor:
        raise WorkflowError("Il task può essere completato solo dall'operatore assegnatario")
    if task.status == TaskStatus.COMPLETATO:
        raise WorkflowError("Il task è già completato")
    incomplete = [code for code in task.depends_on if _task(practice, code).status != TaskStatus.COMPLETATO]
    if incomplete:
        raise WorkflowError(f"Dipendenze non completate: {', '.join(incomplete)}")
    if practice.status == PracticeStatus.DA_FARE:
        start_practice(practice, actor, actor_role)
    evidence = _evidence(attachments, EvidenceOrigin.TASK, actor, task.code)
    result = WorkResult(actor, actor_role, outcome, practice.id, note, evidence, task.code)
    task.status = TaskStatus.COMPLETATO
    task.completed_by = actor
    task.result = result
    practice.record("TASK_COMPLETED", actor, actor_role, task_code=task.code, outcome=outcome)
    practice.record("WORK_RESULT_RECORDED", actor, actor_role, origin="TASK", task_code=task.code)
    for item in evidence:
        practice.record("EVIDENCE_ADDED", actor, actor_role, evidence_id=item.id, origin=item.origin.value, task_code=task.code)
    if practice.required_tasks_complete:
        _transition(practice, PracticeStatus.COMPLETATA, actor, actor_role)
        if practice.requires_validation:
            _transition(practice, PracticeStatus.DA_VALIDARE, actor, actor_role)
    return result


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
    task.result = None
    practice.record("TASK_REOPENED", actor, actor_role, task_code=task.code, previous_completed_by=previous_completed_by)
    if practice.status == PracticeStatus.DA_VALIDARE:
        _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor, actor_role)


def validate_practice(practice: Practice, actor: str, actor_role: UserRole = UserRole.VALIDATORE, outcome: str = "VALIDATA", note: str = "", attachments: Iterable[EvidenceInput | dict] | None = None) -> WorkResult:
    _require_role(actor_role, UserRole.VALIDATORE, "Solo un validatore può validare la pratica")
    if practice.status != PracticeStatus.DA_VALIDARE or not practice.required_tasks_complete:
        raise WorkflowError("La pratica non è pronta per la validazione")
    if actor in {task.completed_by for task in practice.tasks if task.completed_by}:
        raise WorkflowError("Chi ha eseguito task della pratica non può validarla")
    evidence = _evidence(attachments, EvidenceOrigin.VALIDATION, actor)
    result = WorkResult(actor, actor_role, outcome, practice.id, note, evidence)
    practice.validation_result = result
    practice.validated_by = actor
    practice.validated_at = result.timestamp
    _transition(practice, PracticeStatus.VALIDATA, actor, actor_role)
    practice.record("PRACTICE_VALIDATED", actor, actor_role, outcome=outcome)
    practice.record("WORK_RESULT_RECORDED", actor, actor_role, origin="VALIDATION")
    for item in evidence:
        practice.record("EVIDENCE_ADDED", actor, actor_role, evidence_id=item.id, origin=item.origin.value)
    return result


def close_practice(practice: Practice, actor: str, actor_role: UserRole = UserRole.MANAGER, outcome: str = "CHIUSA", note: str = "", attachments: Iterable[EvidenceInput | dict] | None = None) -> WorkResult:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può chiudere la pratica")
    allowed = PracticeStatus.VALIDATA if practice.requires_validation else PracticeStatus.COMPLETATA
    if practice.status != allowed:
        raise WorkflowError("La pratica non può essere chiusa nello stato corrente")
    evidence = _evidence(attachments, EvidenceOrigin.CLOSURE, actor)
    result = WorkResult(actor, actor_role, outcome, practice.id, note, evidence)
    practice.closure_result = result
    _transition(practice, PracticeStatus.CHIUSA, actor, actor_role)
    practice.record("PRACTICE_CLOSED", actor, actor_role, outcome=outcome)
    practice.record("WORK_RESULT_RECORDED", actor, actor_role, origin="CLOSURE")
    for item in evidence:
        practice.record("EVIDENCE_ADDED", actor, actor_role, evidence_id=item.id, origin=item.origin.value)
    return result


def operator_work_queue(practices: Iterable[Practice], actor: str) -> list[tuple[Practice, Task]]:
    return [(practice, task) for practice in practices for task in practice.tasks if task.assignee == actor and task.status != TaskStatus.COMPLETATO]
