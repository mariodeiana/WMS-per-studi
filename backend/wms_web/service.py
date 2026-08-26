from __future__ import annotations

import pickle
from datetime import date, datetime
from pathlib import Path
from threading import RLock

from backend.wms_core.models import AuditEvent, Evidence, Practice, Task, UserRole, WorkResult
from backend.wms_core.templates import build_lipe_trim_tasks
from backend.wms_core.workflow import assign_task, close_practice, complete_task, reopen_task, save_task_progress, validate_practice

DEMO_PRACTICE_ID = "P-2026-LIPE-001"
DEMO_USERS = {"anna.operatore": UserRole.OPERATORE, "luca.operatore": UserRole.OPERATORE,
              "valeria.validatore": UserRole.VALIDATORE, "marta.manager": UserRole.MANAGER}

def build_demo_practice() -> Practice:
    practice = Practice(id=DEMO_PRACTICE_ID, practice_type_code="LIPE_TRIM", client_id="CLIENT-001",
                        period_start="2026-04-01", period_end="2026-06-30", due_date="2026-09-30",
                        tasks=build_lipe_trim_tasks())
    practice.record("PRACTICE_CREATED", "sistema", source="demo-locale")
    assignees = ("anna.operatore", "luca.operatore")
    for index, task in enumerate(practice.tasks): assign_task(practice, task.code, assignees[index % 2], "marta.manager", UserRole.MANAGER)
    return practice

def _date(value: datetime | None) -> str | None: return value.isoformat() if value else None

def _task(task: Task) -> dict[str, object]:
    return {"code": task.code, "title": task.title, "instructions": task.instructions, "required": task.required,
            "status": task.status.value, "assignee": task.assignee, "completed_by": task.completed_by,
            "depends_on": list(task.depends_on), "result_id": task.result_id, "work_note": task.work_note,
            "work_notes": [{"actor":n.actor,"note":n.note,"at":_date(n.at)} for n in task.work_notes],
            "progress_evidence_ids": list(task.progress_evidence_ids), "reopen_reason": task.reopen_reason}

def _event(event: AuditEvent) -> dict[str, object]: return {"event_type": event.event_type, "actor": event.actor, "at": _date(event.at), "details": event.details}

def _result(result: WorkResult) -> dict[str, object]:
    return {"id": result.id, "actor": result.actor, "actor_role": result.actor_role.value, "timestamp": _date(result.timestamp), "outcome": result.outcome, "note": result.note, "evidence_ids": list(result.evidence_ids), "related_practice_id": result.related_practice_id, "related_task_code": result.related_task_code, "action": result.action}

def _evidence(item: Evidence) -> dict[str, object]:
    return {"id": item.id, "filename": item.filename, "content_type": item.content_type, "description": item.description, "document_type": item.document_type, "size_bytes": item.size_bytes, "actor": item.actor, "actor_role": item.actor_role.value, "created_at": _date(item.created_at), "source": item.source, "related_practice_id": item.related_practice_id, "related_task_code": item.related_task_code, "preview_url": f"/api/evidence/{item.id}?disposition=inline", "download_url": f"/api/evidence/{item.id}?disposition=attachment"}

def serialize_practice(practice: Practice) -> dict[str, object]:
    completed=sum(task.status.value=="COMPLETATO" for task in practice.tasks)
    return {"id":practice.id,"practice_type_code":practice.practice_type_code,"client_id":practice.client_id,"period_start":practice.period_start,"period_end":practice.period_end,"due_date":practice.due_date,"requires_validation":practice.requires_validation,"status":practice.status.value,"tasks":[_task(task) for task in practice.tasks],"progress":{"completed":completed,"total":len(practice.tasks)},"audit":[_event(event) for event in reversed(practice.audit)],"validated_by":practice.validated_by,"validated_at":_date(practice.validated_at),"results":[_result(result) for result in reversed(practice.results)],"evidence":[_evidence(item) for item in reversed(practice.evidence)],"validation_result_id":practice.validation_result_id,"closure_result_id":practice.closure_result_id,"roles":{"validator":"valeria.validatore","manager":"marta.manager"}}

def _manager_summary(practice: Practice) -> dict[str, object]:
    total=len(practice.tasks); completed=sum(t.status.value=="COMPLETATO" for t in practice.tasks); reopened=sum(bool(t.reopen_reason) and t.status.value!="COMPLETATO" for t in practice.tasks); in_progress=sum(t.status.value=="IN_LAVORAZIONE" for t in practice.tasks)
    warning_results=sum("RILIEVI" in str(r.outcome) for r in practice.results)
    if reopened: situation={"code":"REOPENED","label":f"{reopened} task riaperto" if reopened==1 else f"{reopened} task riaperti"}
    elif warning_results: situation={"code":"WARNINGS","label":f"{warning_results} risultato con rilievi"}
    elif in_progress: situation={"code":"IN_PROGRESS","label":f"{in_progress} task in corso"}
    else: situation={"code":"REGULAR","label":"Regolare"}
    due=date.fromisoformat(practice.due_date); days=(due-date.today()).days
    if days<0: urgency={"level":"OVERDUE","label":"In ritardo","detail":f"{abs(days)} gg"}
    elif days<=7: urgency={"level":"HIGH","label":"Alta","detail":f"{days} gg"}
    elif days<=30: urgency={"level":"MEDIUM","label":"Media","detail":f"{days} gg"}
    else: urgency={"level":"LOW","label":"Bassa","detail":f"{days} gg"}
    return {"id":practice.id,"practice_type_code":practice.practice_type_code,"client_id":practice.client_id,"period_start":practice.period_start,"period_end":practice.period_end,"due_date":practice.due_date,"status":practice.status.value,"progress":{"completed":completed,"total":total,"percent":round(100*completed/total) if total else 0},"situation":situation,"urgency":urgency,"urgency_sort":days}

class PracticeService:
    def __init__(self, state_path: str | Path | None = None) -> None:
        self._lock = RLock()
        self._state_path = Path(state_path) if state_path else None
        self._practices = self._load_state() if self._state_path and self._state_path.exists() else {DEMO_PRACTICE_ID: build_demo_practice()}

    def _load_state(self) -> dict[str, Practice]:
        try:
            with self._state_path.open("rb") as handle:
                state = pickle.load(handle)
            if not isinstance(state, dict) or not all(isinstance(item, Practice) for item in state.values()):
                raise ValueError("formato stato demo non valido")
            return state
        except Exception as error:
            raise RuntimeError(f"Impossibile caricare lo stato demo da {self._state_path}: {error}") from error

    def _persist(self) -> None:
        if not self._state_path:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        with temporary.open("wb") as handle:
            pickle.dump(self._practices, handle, protocol=pickle.HIGHEST_PROTOCOL)
        temporary.replace(self._state_path)

    def _role(self,actor:str)->UserRole:
        try:return DEMO_USERS[actor]
        except KeyError as error:raise PermissionError(f"Utente demo sconosciuto: {actor}") from error
    def get(self,practice_id:str)->dict[str,object]:
        with self._lock:return serialize_practice(self._find(practice_id))
    def manager_practices(self,actor:str)->list[dict[str,object]]:
        if self._role(actor)!=UserRole.MANAGER: raise PermissionError("La lista pratiche è riservata al manager")
        with self._lock:
            rows=[_manager_summary(p) for p in self._practices.values() if p.status.value!="CHIUSA"]
            return sorted(rows,key=lambda row:(row["urgency_sort"],row["due_date"],row["id"]))
    def work_queue(self,operator:str)->list[dict[str,object]]:
        if self._role(operator)!=UserRole.OPERATORE:raise PermissionError("I miei compiti sono riservati agli operatori")
        with self._lock:return [{"practice_id":p.id,"practice_type_code":p.practice_type_code,"client_id":p.client_id,"due_date":p.due_date,**_task(t)} for p in self._practices.values() for t in p.tasks if t.assignee==operator and t.status.value!="COMPLETATO"]
    def task_detail(self,practice_id:str,task_code:str,operator:str,include_context:bool=False)->dict[str,object]:
        if self._role(operator)!=UserRole.OPERATORE:raise PermissionError("L'attività è riservata agli operatori")
        with self._lock:
            practice=self._find(practice_id);task=self._find_task(practice,task_code)
            if task.assignee!=operator:raise PermissionError("Attività non assegnata all'operatore")
            evidences={e.id:_evidence(e) for e in practice.evidence};journal=[]
            for event in reversed(practice.audit):
                if event.details.get("task_code")!=task.code:continue
                if event.event_type=="TASK_PROGRESS_SAVED":
                    ids=event.details.get("evidence_ids") or [];journal.append({"type":"PROGRESS","actor":event.actor,"at":_date(event.at),"note":event.details.get("note") or "","evidence":[evidences[eid] for eid in ids if eid in evidences]})
                elif event.event_type=="TASK_REOPENED":journal.append({"type":"REOPENED","actor":event.actor,"at":_date(event.at),"note":event.details.get("reason") or "","evidence":[]})
            detail={"practice":{"id":practice.id,"type":practice.practice_type_code,"client_id":practice.client_id,"period_start":practice.period_start,"period_end":practice.period_end,"due_date":practice.due_date},"task":_task(task),"task_journal":journal,"task_progress_evidence":[evidences[eid] for eid in task.progress_evidence_ids if eid in evidences]}
            if include_context:
                task_titles={t.code:t.title for t in practice.tasks};previous=[]
                for result in practice.results:
                    if result.related_task_code==task.code:continue
                    row=_result(result);row["related_task_title"]=task_titles.get(result.related_task_code or "");row["evidence"]=[evidences[eid] for eid in result.evidence_ids if eid in evidences];previous.append(row)
                detail["previous_results"]=previous;detail["evidence"]=[_evidence(e) for e in practice.evidence]
            return detail
    def evidence_content(self,evidence_id:str)->Evidence:
        with self._lock:
            for practice in self._practices.values():
                for item in practice.evidence:
                    if item.id==evidence_id:return item
            raise KeyError(f"Evidenza inesistente: {evidence_id}")
    def save_task_progress(self,practice_id,task_code,actor,note="",attachments=None):
        with self._lock:
            p=self._find(practice_id);save_task_progress(p,task_code,actor,self._role(actor),note,attachments);self._persist();return serialize_practice(p)
    def complete_task(self,practice_id,task_code,actor,outcome="COMPLETATO",note="",attachments=None):
        with self._lock:
            p=self._find(practice_id);complete_task(p,task_code,actor,self._role(actor),outcome,note,attachments);self._persist();return serialize_practice(p)
    def assign_task(self,practice_id,task_code,assignee,actor):
        if self._role(assignee)!=UserRole.OPERATORE:raise PermissionError("L'assegnatario deve avere ruolo OPERATORE")
        with self._lock:
            p=self._find(practice_id);assign_task(p,task_code,assignee,actor,self._role(actor));self._persist();return serialize_practice(p)
    def reopen_task(self,practice_id,task_code,actor,reason=""):
        with self._lock:
            p=self._find(practice_id);reopen_task(p,task_code,actor,self._role(actor),reason);self._persist();return serialize_practice(p)
    def validate(self,practice_id,actor,outcome="VALIDATA",note="",attachments=None):
        with self._lock:
            p=self._find(practice_id);validate_practice(p,actor,self._role(actor),outcome,note,attachments);self._persist();return serialize_practice(p)
    def close(self,practice_id,actor,outcome="CHIUSA",note="",attachments=None):
        with self._lock:
            p=self._find(practice_id);close_practice(p,actor,self._role(actor),outcome,note,attachments);self._persist();return serialize_practice(p)
    def _find(self,practice_id):
        try:return self._practices[practice_id]
        except KeyError as error:raise KeyError(f"Pratica inesistente: {practice_id}") from error
    @staticmethod
    def _find_task(practice,task_code):
        task=next((t for t in practice.tasks if t.code==task_code),None)
        if task is None:raise KeyError(f"Task inesistente: {task_code}")
        return task
