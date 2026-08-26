from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

class PracticeStatus(str, Enum):
    DA_FARE="DA_FARE"; IN_LAVORAZIONE="IN_LAVORAZIONE"; COMPLETATA="COMPLETATA"; DA_VALIDARE="DA_VALIDARE"; VALIDATA="VALIDATA"; NON_VALIDATA="NON_VALIDATA"; CHIUSA="CHIUSA"
class TaskStatus(str, Enum): DA_FARE="DA_FARE"; IN_LAVORAZIONE="IN_LAVORAZIONE"; COMPLETATO="COMPLETATO"
class UserRole(str, Enum): OPERATORE="OPERATORE"; VALIDATORE="VALIDATORE"; MANAGER="MANAGER"
class NonConformityStatus(str, Enum): APERTA="APERTA"; IN_SANATORIA="IN_SANATORIA"; DA_VERIFICARE="DA_VERIFICARE"; CHIUSA="CHIUSA"
@dataclass
class AuditEvent:
    event_type:str; actor:str; at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); details:dict=field(default_factory=dict)
@dataclass(frozen=True)
class TaskNote:
    actor:str; note:str; at:datetime=field(default_factory=lambda:datetime.now(timezone.utc))
@dataclass(frozen=True)
class Evidence:
    id:str; filename:str; actor:str; actor_role:UserRole; source:str; related_practice_id:str; created_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); related_task_code:Optional[str]=None; content_type:Optional[str]=None; description:str=""; document_type:str="DOCUMENTO"; content_base64:str=""; size_bytes:int=0
@dataclass(frozen=True)
class WorkResult:
    id:str; actor:str; actor_role:UserRole; outcome:str; note:str; related_practice_id:str; timestamp:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); related_task_code:Optional[str]=None; evidence_ids:tuple[str,...]=(); action:str="TASK"
@dataclass
class CorrectiveAction:
    id:str; actor:str; instruction:str; task_codes:tuple[str,...]; created_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); completed_at:Optional[datetime]=None
@dataclass
class NonConformity:
    id:str; reason:str; opened_by:str; opened_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); status:NonConformityStatus=NonConformityStatus.APERTA; source:str="VALIDATION"; corrective_actions:list[CorrectiveAction]=field(default_factory=list); closed_at:Optional[datetime]=None; closed_by:Optional[str]=None
@dataclass
class Task:
    code:str; title:str; required:bool=True; status:TaskStatus=TaskStatus.DA_FARE; assignee:Optional[str]=None; completed_by:Optional[str]=None; depends_on:tuple[str,...]=(); result_id:Optional[str]=None; instructions:str=""; work_note:str=""; work_notes:list[TaskNote]=field(default_factory=list); progress_evidence_ids:list[str]=field(default_factory=list); reopen_reason:str=""
@dataclass
class Practice:
    id:str; practice_type_code:str; client_id:str; period_start:str; period_end:str; due_date:str; requires_validation:bool=True; status:PracticeStatus=PracticeStatus.DA_FARE; tasks:list[Task]=field(default_factory=list); audit:list[AuditEvent]=field(default_factory=list); validated_by:Optional[str]=None; validated_at:Optional[datetime]=None; results:list[WorkResult]=field(default_factory=list); evidence:list[Evidence]=field(default_factory=list); validation_result_id:Optional[str]=None; closure_result_id:Optional[str]=None; nonconformities:list[NonConformity]=field(default_factory=list)
    def record(self,event_type:str,actor:str,**details:object)->None:self.audit.append(AuditEvent(event_type=event_type,actor=actor,details=details))
    @property
    def required_tasks_complete(self)->bool:return all(task.status==TaskStatus.COMPLETATO for task in self.tasks if task.required)
