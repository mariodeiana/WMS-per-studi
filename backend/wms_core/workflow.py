from __future__ import annotations

import base64
from datetime import datetime, timezone

from .models import Evidence, Practice, PracticeStatus, Task, TaskNote, TaskStatus, UserRole, WorkResult


class WorkflowError(ValueError):
    pass


MAX_EVIDENCE_BYTES = 5 * 1024 * 1024


def _add_evidence(practice: Practice, *, actor: str, actor_role: UserRole,
                  attachments: list[dict[str, str]] | None, source: str,
                  task_code: str | None = None) -> list[str]:
    evidence_ids: list[str] = []
    for item in attachments or []:
        if not isinstance(item, dict):
            raise WorkflowError("Formato evidenza non valido")
        filename = str(item.get("filename", "")).strip()
        if not filename:
            raise WorkflowError("Ogni evidenza deve avere un nome file")
        content_base64 = str(item.get("content_base64") or "")
        try:
            raw = base64.b64decode(content_base64, validate=True) if content_base64 else b""
        except ValueError as error:
            raise WorkflowError("Contenuto evidenza non valido") from error
        if len(raw) > MAX_EVIDENCE_BYTES:
            raise WorkflowError("Ogni documento può avere dimensione massima di 5 MB")
        evidence = Evidence(
            id=f"E-{len(practice.evidence) + 1:04}", filename=filename,
            content_type=str(item.get("content_type") or "application/octet-stream"),
            description=str(item.get("description") or "").strip(),
            document_type=str(item.get("document_type") or "DOCUMENTO").strip() or "DOCUMENTO",
            content_base64=content_base64, size_bytes=len(raw), actor=actor, actor_role=actor_role,
            source=source, related_practice_id=practice.id, related_task_code=task_code,
        )
        practice.evidence.append(evidence)
        evidence_ids.append(evidence.id)
        practice.record("EVIDENCE_ADDED", actor, evidence_id=evidence.id, task_code=task_code, source=source)
    return evidence_ids


def _record_result(practice: Practice, *, actor: str, actor_role: UserRole, outcome: str, note: str,
                   attachments: list[dict[str, str]] | None, action: str, task_code: str | None = None,
                   existing_evidence_ids: list[str] | None = None) -> WorkResult:
    outcome = outcome.strip(); note = note.strip()
    if not outcome:
        raise WorkflowError("L'esito è obbligatorio")
    evidence_ids = list(existing_evidence_ids or [])
    evidence_ids.extend(_add_evidence(practice, actor=actor, actor_role=actor_role,
                                      attachments=attachments, source=action, task_code=task_code))
    result = WorkResult(
        id=f"R-{len(practice.results) + 1:04}", actor=actor, actor_role=actor_role,
        outcome=outcome, note=note, related_practice_id=practice.id, related_task_code=task_code,
        evidence_ids=tuple(evidence_ids), action=action,
    )
    practice.results.append(result)
    practice.record("WORK_RESULT_RECORDED", actor, result_id=result.id, task_code=task_code)
    return result


def _transition(practice: Practice, target: PracticeStatus, actor: str) -> None:
    previous = practice.status; practice.status = target
    practice.record("PRACTICE_STATUS_CHANGED", actor, previous=previous.value, current=target.value)


def _task(practice: Practice, task_code: str) -> Task:
    task = next((item for item in practice.tasks if item.code == task_code), None)
    if task is None: raise WorkflowError(f"Task inesistente: {task_code}")
    return task


def _require_role(actual: UserRole, expected: UserRole, message: str) -> None:
    if actual != expected: raise WorkflowError(message)


def assign_task(practice: Practice, task_code: str, assignee: str, actor: str, actor_role: UserRole) -> None:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può assegnare i task")
    if practice.status in {PracticeStatus.VALIDATA, PracticeStatus.CHIUSA}:
        raise WorkflowError("I task non possono essere assegnati dopo la validazione")
    task = _task(practice, task_code)
    if task.status == TaskStatus.COMPLETATO:
        raise WorkflowError("Un task completato deve essere riaperto prima di riassegnarlo")
    previous = task.assignee; task.assignee = assignee
    practice.record("TASK_ASSIGNED", actor, task_code=task.code, previous=previous, assignee=assignee)


def start_practice(practice: Practice, actor: str) -> None:
    if practice.status != PracticeStatus.DA_FARE:
        raise WorkflowError("La pratica può essere avviata solo da DA_FARE")
    _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor)


def save_task_progress(practice: Practice, task_code: str, actor: str, actor_role: UserRole,
                       note: str = "", attachments: list[dict[str, str]] | None = None) -> None:
    _require_role(actor_role, UserRole.OPERATORE, "Solo un operatore può lavorare i task")
    if practice.status not in {PracticeStatus.DA_FARE, PracticeStatus.IN_LAVORAZIONE}:
        raise WorkflowError("Il task non può essere lavorato nello stato corrente")
    task = _task(practice, task_code)
    if task.assignee != actor:
        raise WorkflowError("Il task può essere lavorato solo dall'operatore assegnatario")
    if task.status == TaskStatus.COMPLETATO:
        raise WorkflowError("Il task è già completato")
    if practice.status == PracticeStatus.DA_FARE:
        start_practice(practice, actor)
    previous_status = task.status; task.status = TaskStatus.IN_LAVORAZIONE
    clean_note = note.strip()
    if clean_note:
        task.work_note = clean_note
        task.work_notes.append(TaskNote(actor=actor, note=clean_note))
    new_ids = _add_evidence(practice, actor=actor, actor_role=actor_role, attachments=attachments,
                            source="TASK_PROGRESS", task_code=task.code)
    task.progress_evidence_ids.extend(new_ids)
    practice.record("TASK_PROGRESS_SAVED", actor, task_code=task.code, previous=previous_status.value,
                    current=task.status.value, note=clean_note, evidence_ids=new_ids)


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
    incomplete_dependencies = [code for code in task.depends_on if _task(practice, code).status != TaskStatus.COMPLETATO]
    if incomplete_dependencies:
        raise WorkflowError(f"Dipendenze non completate: {', '.join(incomplete_dependencies)}")
    if practice.status == PracticeStatus.DA_FARE:
        start_practice(practice, actor)
    result = _record_result(practice, actor=actor, actor_role=actor_role, outcome=outcome, note=note,
                            attachments=attachments, action="TASK", task_code=task.code,
                            existing_evidence_ids=task.progress_evidence_ids)
    task.status = TaskStatus.COMPLETATO; task.completed_by = actor; task.result_id = result.id
    task.work_note = ""; task.reopen_reason = ""; task.progress_evidence_ids = []
    practice.record("TASK_COMPLETED", actor, task_code=task.code, result_id=result.id)
    if practice.required_tasks_complete:
        _transition(practice, PracticeStatus.COMPLETATA, actor)
        if practice.requires_validation: _transition(practice, PracticeStatus.DA_VALIDARE, actor)


def reopen_task(practice: Practice, task_code: str, actor: str, actor_role: UserRole, reason: str = "") -> None:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può riaprire i task")
    if practice.status not in {PracticeStatus.IN_LAVORAZIONE, PracticeStatus.DA_VALIDARE}:
        raise WorkflowError("I task possono essere riaperti solo prima della validazione")
    reason = reason.strip()
    if not reason: raise WorkflowError("La motivazione della riapertura è obbligatoria")
    task = _task(practice, task_code)
    if task.status != TaskStatus.COMPLETATO: raise WorkflowError("Solo un task completato può essere riaperto")
    previous_completed_by = task.completed_by; previous_result_id = task.result_id
    task.status = TaskStatus.IN_LAVORAZIONE; task.completed_by = None; task.result_id = None
    task.reopen_reason = reason; task.work_note = ""; task.progress_evidence_ids = []
    practice.record("TASK_REOPENED", actor, task_code=task.code, previous_completed_by=previous_completed_by,
                    previous_result_id=previous_result_id, reason=reason)
    if practice.status == PracticeStatus.DA_VALIDARE: _transition(practice, PracticeStatus.IN_LAVORAZIONE, actor)


def validate_practice(practice: Practice, actor: str, actor_role: UserRole,
                      outcome: str = "VALIDATA", note: str = "",
                      attachments: list[dict[str, str]] | None = None) -> None:
    _require_role(actor_role, UserRole.VALIDATORE, "Solo un validatore può validare la pratica")
    if practice.status != PracticeStatus.DA_VALIDARE or not practice.required_tasks_complete:
        raise WorkflowError("La pratica non è pronta per la validazione")
    if any(event.event_type == "TASK_COMPLETED" and event.actor == actor for event in practice.audit):
        raise WorkflowError("Chi ha eseguito task della pratica non può validarla")
    result = _record_result(practice, actor=actor, actor_role=actor_role, outcome=outcome, note=note,
                            attachments=attachments, action="VALIDATION")
    practice.validation_result_id = result.id; practice.validated_by = actor; practice.validated_at = datetime.now(timezone.utc)
    _transition(practice, PracticeStatus.VALIDATA, actor); practice.record("PRACTICE_VALIDATED", actor, result_id=result.id)


def close_practice(practice: Practice, actor: str, actor_role: UserRole,
                   outcome: str = "CHIUSA", note: str = "",
                   attachments: list[dict[str, str]] | None = None) -> None:
    _require_role(actor_role, UserRole.MANAGER, "Solo un manager può chiudere la pratica")
    allowed = PracticeStatus.VALIDATA if practice.requires_validation else PracticeStatus.COMPLETATA
    if practice.status != allowed: raise WorkflowError("La pratica non può essere chiusa nello stato corrente")
    result = _record_result(practice, actor=actor, actor_role=actor_role, outcome=outcome, note=note,
                            attachments=attachments, action="CLOSURE")
    practice.closure_result_id = result.id; _transition(practice, PracticeStatus.CHIUSA, actor)
    practice.record("PRACTICE_CLOSED", actor, result_id=result.id)
