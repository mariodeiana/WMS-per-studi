from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    OPERATORE = "OPERATORE"
    VALIDATORE = "VALIDATORE"
    MANAGER = "MANAGER"


class PracticeStatus(str, Enum):
    DA_FARE = "DA_FARE"
    IN_LAVORAZIONE = "IN_LAVORAZIONE"
    COMPLETATA = "COMPLETATA"
    DA_VALIDARE = "DA_VALIDARE"
    VALIDATA = "VALIDATA"
    CHIUSA = "CHIUSA"


class TaskStatus(str, Enum):
    DA_FARE = "DA_FARE"
    IN_LAVORAZIONE = "IN_LAVORAZIONE"
    COMPLETATO = "COMPLETATO"


class EvidenceOrigin(str, Enum):
    TASK = "TASK"
    VALIDATION = "VALIDATION"
    CLOSURE = "CLOSURE"


@dataclass
class AuditEvent:
    event_type: str
    actor: str
    actor_role: Optional[Role] = None
    at: datetime = field(default_factory=utc_now)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Evidence:
    name: str
    origin: EvidenceOrigin
    author: str
    content_ref: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    task_code: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class EvidenceInput:
    name: str
    content_ref: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkResult:
    actor: str
    actor_role: Role
    outcome: str
    related_practice_id: str
    note: str = ""
    attachments: list[Evidence] = field(default_factory=list)
    related_task_code: Optional[str] = None
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class Task:
    code: str
    title: str
    instructions: str = ""
    required: bool = True
    status: TaskStatus = TaskStatus.DA_FARE
    assigned_to: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)
    priority: Optional[str] = None
    due_date: Optional[str] = None
    completed_by: Optional[str] = None
    result: Optional[WorkResult] = None


@dataclass
class Practice:
    id: str
    practice_type_code: str
    client_id: str
    period_start: str
    period_end: str
    due_date: str
    client_name: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    requires_validation: bool = True
    status: PracticeStatus = PracticeStatus.DA_FARE
    tasks: list[Task] = field(default_factory=list)
    audit: list[AuditEvent] = field(default_factory=list)
    validation_result: Optional[WorkResult] = None
    closure_result: Optional[WorkResult] = None
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None

    def record(
        self, event_type: str, actor: str, actor_role: Optional[Role] = None, **details: object
    ) -> None:
        self.audit.append(
            AuditEvent(event_type=event_type, actor=actor, actor_role=actor_role, details=details)
        )

    @property
    def required_tasks_complete(self) -> bool:
        return all(task.status == TaskStatus.COMPLETATO for task in self.tasks if task.required)

    @property
    def work_results(self) -> list[WorkResult]:
        results = [task.result for task in self.tasks if task.result is not None]
        if self.validation_result is not None:
            results.append(self.validation_result)
        if self.closure_result is not None:
            results.append(self.closure_result)
        return results

    @property
    def dossier(self) -> list[Evidence]:
        """Fascicolo della pratica: contenuti prodotti, mai eventi di audit."""
        return [evidence for result in self.work_results for evidence in result.attachments]
