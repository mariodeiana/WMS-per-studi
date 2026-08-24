from __future__ import annotations

from collections.abc import Iterable

from .models import (
    Evidence,
    EvidenceInput,
    EvidenceOrigin,
    Practice,
    PracticeStatus,
    Role,
    Task,
    TaskStatus,
    WorkResult,
)


class WorkflowError(ValueError):
    pass


def _transition(practice: Practice, target: PracticeStatus, actor: str, role: Role) -> None:
    previous = practice.status
    practice.status = target
    practice.record(
        "PRACTICE_STATUS_CHANGED", actor, role, previous=previous.value, current=target.value
    )


def _require_role(actual: Role, expected: Role) -> None:
    if actual != expected:
        raise WorkflowError(f"Azione consentita solo al ruolo {expected.value}")


def _task(practice: Practice, task_code: str) -> Task:
    task = next((item for item in practice.tasks if item.code == task_code), None)
    if task is None:
        raise WorkflowError(f"Task inesistente: {task_code}")
    return task


def _evidence(
    inputs: Iterable[EvidenceInput | dict] | None,
    origin: EvidenceOrigin,
    actor: str,
    task_code: str | None = None,
) -> list[Evidence]:
    items = []
    for value in inputs or []:
        item = EvidenceInput(**value) if isinstance(value, dict) else value
        items.append(
            Evidence(
                name=item.name,
                content_ref=item.content_ref,
                metadata=dict(item.metadata),
                origin=origin,
                author=actor,
                task_code=task_code,
            )
        )
    return items


def start_practice(practice: Practice, actor: str, actor_role: Role = Role.OPERATORE) -> None:
    _require_role(actor_role, Role.OPERATORE)
    if practice.status != PracticeStatus.DA_FARE:
        raise WorkflowError("La pratica può essere avviata solo da DA_FARE")
    _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor, actor_role)


def complete_task(
    practice: Practice,
    task_code: str,
    actor: str,
    outcome: str = "COMPLETATO",
    note: str = "",
    attachments: Iterable[EvidenceInput | dict] | None = None,
    actor_role: Role = Role.OPERATORE,
) -> WorkResult:
    _require_role(actor_role, Role.OPERATORE)
    if practice.status not in {PracticeStatus.IN_LAVORAZIONE, PracticeStatus.DA_FARE}:
        raise WorkflowError("I task non possono essere completati nello stato corrente")
    task = _task(practice, task_code)
    if task.assigned_to is not None and task.assigned_to != actor:
        raise WorkflowError("Il task è assegnato a un altro operatore")
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


def request_validation(practice: Practice, actor: str, actor_role: Role = Role.OPERATORE) -> None:
    if practice.status != PracticeStatus.COMPLETATA:
        raise WorkflowError("La validazione può essere richiesta solo da COMPLETATA")
    if not practice.requires_validation:
        raise WorkflowError("Il tipo di pratica non richiede validazione")
    _transition(practice, PracticeStatus.DA_VALIDARE, actor, actor_role)


def validate_practice(
    practice: Practice,
    actor: str,
    actor_can_validate: bool | None = None,
    outcome: str = "VALIDATA",
    note: str = "",
    attachments: Iterable[EvidenceInput | dict] | None = None,
    actor_role: Role = Role.VALIDATORE,
) -> WorkResult:
    if practice.status != PracticeStatus.DA_VALIDARE:
        raise WorkflowError("La pratica non è in attesa di validazione")
    if actor_can_validate is False:
        raise WorkflowError("L'utente non è autorizzato alla validazione")
    _require_role(actor_role, Role.VALIDATORE)
    if actor in {task.completed_by for task in practice.tasks if task.completed_by}:
        raise WorkflowError("Separazione dei compiti: un operatore non può autovalidarsi")

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


def close_practice(
    practice: Practice,
    actor: str,
    outcome: str = "CHIUSA",
    note: str = "",
    attachments: Iterable[EvidenceInput | dict] | None = None,
    actor_role: Role = Role.MANAGER,
) -> WorkResult:
    _require_role(actor_role, Role.MANAGER)
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
    return [
        (practice, task)
        for practice in practices
        for task in practice.tasks
        if task.assigned_to == actor and task.status != TaskStatus.COMPLETATO
    ]


def reopen_task(
    practice: Practice,
    task_code: str,
    actor: str,
    actor_role: Role = Role.MANAGER,
) -> None:
    """Riapre un task completato e invalida i risultati successivi della pratica."""
    _require_role(actor_role, Role.MANAGER)
    task = _task(practice, task_code)
    if task.status != TaskStatus.COMPLETATO:
        raise WorkflowError("Può essere riaperto solo un task completato")
    if practice.status == PracticeStatus.CHIUSA:
        raise WorkflowError("Una pratica chiusa non può essere modificata")

    previous_result = task.result
    task.status = TaskStatus.DA_FARE
    task.completed_by = None
    task.result = None
    practice.validation_result = None
    practice.validated_by = None
    practice.validated_at = None
    _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor, actor_role)
    practice.record(
        "TASK_REOPENED",
        actor,
        actor_role,
        task_code=task.code,
        previous_outcome=previous_result.outcome if previous_result else None,
    )
