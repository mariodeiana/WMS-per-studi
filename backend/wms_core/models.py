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


@dataclass
class Task:
    code: str
    title: str
    required: bool = True
    status: TaskStatus = TaskStatus.DA_FARE
    assignee: Optional[str] = None
    completed_by: Optional[str] = None
    depends_on: tuple[str, ...] = ()


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

    def record(self, event_type: str, actor: str, **details: object) -> None:
        self.audit.append(AuditEvent(event_type=event_type, actor=actor, details=details))

    @property
    def required_tasks_complete(self) -> bool:
        return all(task.status == TaskStatus.COMPLETATO for task in self.tasks if task.required)
