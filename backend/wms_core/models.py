from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


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


class UserRole(str, Enum):
    OPERATORE = "OPERATORE"
    VALIDATORE = "VALIDATORE"
    MANAGER = "MANAGER"


@dataclass
class AuditEvent:
    event_type: str
    actor: str
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    """An immutable dossier entry produced by a workflow action.

    v0.3 stores attachment metadata rather than file bytes.  This keeps the
    domain independent from the future persistence/document adapter.
    """

    id: str
    filename: str
    actor: str
    actor_role: UserRole
    source: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    related_task_code: Optional[str] = None
    content_type: Optional[str] = None


@dataclass(frozen=True)
class WorkResult:
    """Structured result of a task, validation or closure action."""

    id: str
    actor: str
    actor_role: UserRole
    outcome: str
    note: str
    related_practice_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    related_task_code: Optional[str] = None
    evidence_ids: tuple[str, ...] = ()
    action: str = "TASK"


@dataclass
class Task:
    code: str
    title: str
    required: bool = True
    status: TaskStatus = TaskStatus.DA_FARE
    assignee: Optional[str] = None
    completed_by: Optional[str] = None
    depends_on: tuple[str, ...] = ()
    result_id: Optional[str] = None


@dataclass
class Practice:
    id: str
    practice_type_code: str
    client_id: str
    period_start: str
    period_end: str
    due_date: str
    requires_validation: bool = True
    status: PracticeStatus = PracticeStatus.DA_FARE
    tasks: list[Task] = field(default_factory=list)
    audit: list[AuditEvent] = field(default_factory=list)
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    results: list[WorkResult] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    validation_result_id: Optional[str] = None
    closure_result_id: Optional[str] = None

    def record(self, event_type: str, actor: str, **details: object) -> None:
        self.audit.append(AuditEvent(event_type=event_type, actor=actor, details=details))

    @property
    def required_tasks_complete(self) -> bool:
        return all(task.status == TaskStatus.COMPLETATO for task in self.tasks if task.required)
