from __future__ import annotations
import pickle
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from threading import RLock
from backend.wms_core.models import Practice,UserRole
from backend.wms_core.templates import build_lipe_trim_tasks
from backend.wms_core.workflow import assign_task,close_practice,complete_task,reopen_task,save_task_progress,validate_practice
DEMO_PRACTICE_ID="P-2026-LIPE-001";RECENT_COMPLETED_HOURS=8
DEMO_USERS={"anna.operatore":UserRole.OPERATORE,"luca.operatore":UserRole.OPERATORE,"valeria.validatore":UserRole.VALIDATORE,"marta.manager":UserRole.MANAGER}
def build_demo_practice():
 p=Practice(id=DEMO_PRACTICE_ID,practice_type_code="LIPE_TRIM",client_id="CLIENT-001",period_start="2026-04-01",period_end="2026-06-30",due_date="2026-09-30",tasks=build_lipe_trim_tasks());p.record("PRACTICE_CREATED","sistema",source="demo-locale")
 for i,t in enumerate(p.tasks):assign_task(p,t.code,("anna.operatore","luca.operatore")[i%2],"marta.manager",UserRole.MANAGER)
 return p
def _date(v):return v.isoformat() if v else None
def _task(t):return {"code":t.code,"title":t.title,"instructions":t.instructions,"required":t.required,"status":t.status.value,"assignee":t.assignee,"completed_by":t.completed_by,"depends_on":list(t.depends_on),"result_id":t.result_id,"work_note":t.work_note,"work_notes":[{"actor":n.actor,"note":n.note,"at":_date(n.at)} for n in t.work_notes],"progress_evidence_ids":list(t.progress_evidence_ids),"reopen_reason":t.reopen_reason}
def _event(e):return {"event_type":e.event_type,"actor":e.actor,"at":_date(e.at),"details":e.details}
def _result(r):return {"id":r.id,"actor":r.actor,"actor_role":r.actor_role.value,"timestamp":_date(r.timestamp),"outcome":r.outcome,"note":r.note,"evidence_ids":list(r.evidence_ids),"related_practice_id":r.related_practice_id,"related_task_code":r.related_task_code,"action":r.action}
def _evidence(e):return {"id":e.id,"filename":e.filename,"content_type":e.content_type,"description":e.description,"document_type":e.document_type,"size_bytes":e.size_bytes,"actor":e.actor,"actor_role":e.actor_role.value,"created_at":_date(e.created_at),"source":e.source,"related_practice_id":e.related_practice_id,"related_task_code":e.related_task_code,"preview_url":f"/api/evidence/{e.id}?disposition=inline","download_url":f"/api/evidence/{e.id}?disposition=attachment"}
def serialize_practice(p):
 completed=sum(t.status.value=="COMPLETATO" for t in p.tasks);return {"id":p.id,"practice_type_code":p.practice_type_code,"client_id":p.client_id,"period_start":p.period_start,"period_end":p.period_end,"due_date":p.due_date,"requires_validation":p.requires_validation,"status":p.status.value,"tasks":[_task(t) for t in p.tasks],"progress":{"completed":completed,"total":len(p.tasks)},"audit":[_event(e) for e in reversed(p.audit)],"validated_by":p.validated_by,"validated_at":_date(p.validated_at),"results":[_result(r) for r in reversed(p.results)],"evidence":[_evidence(e) for e in reversed(p.evidence)],"validation_result_id":p.validation_result_id,"closure_result_id":p.closure_result_id,"roles":{"validator":"valeria.validatore","manager":"marta.manager"}}
def _summary(p):
 total=len(p.tasks);completed=sum(t.status.value=="COMPLETATO" for t in p.tasks);warnings=sum("RILIEVI" in str(r.outcome) for r in p.results if r.action=="TASK");due=date.fromisoformat(p.due_date);days=(due-date.today()).days;urg={"level":"OVERDUE","label":"In ritardo","detail":f"{abs(days)} gg"} if days<0 else {"level":"HIGH","label":"Alta","detail":f"{days} gg"} if days<=7 else {"level":"MEDIUM","label":"Media","detail":f"{days} gg"} if days<=30 else {"level":"LOW","label":"Bassa","detail":f"{days} gg"};return {"id":p.id,"practice_type_code":p.practice_type_code,"client_id":p.client_id,"period_start":p.period_start,"period_end":p.period_end,"due_date":p.due_date,"status":p.status.value,"progress":{"completed":completed,"total":total,"percent":round(100*completed/total) if total else 0},"situation":{"code":"WARNINGS" if warnings else "REGULAR","label":f"{warnings} task con rilievi" if warnings else "Regolare"},"urgency":urg,"urgency_sort":days}
class PracticeService:
 def __init__(self,state_path=None):self._lock=RLock();self._state_path=Path(state_path) if state_path else None;self._practices=self._load_state() if self._state_path and self._state_path.exists() else {DEMO_PRACTICE_ID:build_demo_practice()}
 def _load_state(self):
  try:
   with self._state_path.open("rb") as h:state=pickle.load(h)
   if not isinstance(state,dict) or not all(isinstance(x,Practice) for x in state.values()):raise ValueError("formato stato demo non valido")
   return state
  except Exception as e:raise RuntimeError(f"Impossibile caricare lo stato demo da {self._state_path}: {e}") from e
 def _persist(self):
  if not self._state_path:return
  self._state_path.parent.mkdir(parents=True,exist_ok=True);tmp=self._state_path.with_suffix(self._state_path.suffix+".tmp")
  with tmp.open("wb") as h:pickle.dump(self._practices,h,pickle.HIGHEST_PROTOCOL)
  tmp.replace(self._state_path)
 def _role(self,a):
  try:return DEMO_USERS[a]
  except KeyError as e:raise PermissionError(f"Utente demo sconosciuto: {a}") from e
 def get(self,id):
  with self._lock:return serialize_practice(self._find(id))
 def manager_practices(self,actor):
  if self._role(actor)!=UserRole.MANAGER:raise PermissionError("La lista pratiche è riservata al manager")
  with self._lock:return sorted([_summary(p) for p in self._practices.values() if p.status.value!="CHIUSA"],key=lambda x:(x["urgency_sort"],x["id"]))
 def validation_queue(self,actor):
  if self._role(actor)!=UserRole.VALIDATORE:raise PermissionError("La coda di validazione è riservata al validatore")
  with self._lock:
   rows=[]
   for p in self._practices.values():
    if p.status.value!="DA_VALIDARE":continue
    row=_summary(p);entered=next((e.at for e in reversed(p.audit) if e.event_type=="PRACTICE_STATUS_CHANGED" and e.details.get("current")=="DA_VALIDARE"),None);row["waiting_since"]=_date(entered);row["waiting_hours"]=round((datetime.now(timezone.utc)-entered).total_seconds()/3600,1) if entered else None;rows.append(row)
   return sorted(rows,key=lambda x:(x["urgency_sort"],x.get("waiting_since") or "",x["id"]))
 def work_queue(self,operator):
  if self._role(operator)!=UserRole.OPERATORE:raise PermissionError("I miei compiti sono riservati agli operatori")
  cutoff=datetime.now(timezone.utc)-timedelta(hours=RECENT_COMPLETED_HOURS);rows=[]
  with self._lock:
   for p in self._practices.values():
    results={r.id:r for r in p.results}
    for t in p.tasks:
     if t.assignee!=operator:continue
     row={"practice_id":p.id,"practice_type_code":p.practice_type_code,"client_id":p.client_id,"due_date":p.due_date,**_task(t)}
     if t.status.value!="COMPLETATO":row["queue_section"]="ACTIVE";rows.append(row);continue
     r=results.get(t.result_id)
     if r and r.actor==operator and r.timestamp>=cutoff:row.update({"queue_section":"RECENT_COMPLETED","completed_at":_date(r.timestamp),"outcome":r.outcome,"result_note":r.note});rows.append(row)
   return rows
 def task_detail(self,practice_id,task_code,operator,include_context=False):
  if self._role(operator)!=UserRole.OPERATORE:raise PermissionError("L'attività è riservata agli operatori")
  with self._lock:
   p=self._find(practice_id);t=self._find_task(p,task_code)
   if t.assignee!=operator:raise PermissionError("Attività non assegnata all'operatore")
   ev={e.id:_evidence(e) for e in p.evidence};journal=[]
   for event in reversed(p.audit):
    if event.details.get("task_code")!=t.code:continue
    if event.event_type=="TASK_PROGRESS_SAVED":journal.append({"type":"PROGRESS","actor":event.actor,"at":_date(event.at),"note":event.details.get("note") or "","evidence":[ev[x] for x in event.details.get("evidence_ids") or [] if x in ev]})
    elif event.event_type=="TASK_REOPENED":journal.append({"type":"REOPENED","actor":event.actor,"at":_date(event.at),"note":event.details.get("reason") or "","evidence":[]})
   d={"practice":{"id":p.id,"type":p.practice_type_code,"client_id":p.client_id,"period_start":p.period_start,"period_end":p.period_end,"due_date":p.due_date},"task":_task(t),"task_journal":journal,"task_progress_evidence":[ev[x] for x in t.progress_evidence_ids if x in ev]}
   if include_context:
    titles={x.code:x.title for x in p.tasks};prev=[]
    for r in p.results:
     if r.related_task_code==t.code:continue
     row=_result(r);row["related_task_title"]=titles.get(r.related_task_code or "");row["evidence"]=[ev[x] for x in r.evidence_ids if x in ev];prev.append(row)
    d["previous_results"]=prev;d["evidence"]=[_evidence(e) for e in p.evidence]
   return d
 def evidence_content(self,id):
  with self._lock:
   for p in self._practices.values():
    for e in p.evidence:
     if e.id==id:return e
   raise KeyError(f"Evidenza inesistente: {id}")
 def save_task_progress(self,p,t,a,note="",attachments=None):
  with self._lock:x=self._find(p);save_task_progress(x,t,a,self._role(a),note,attachments);self._persist();return serialize_practice(x)
 def complete_task(self,p,t,a,outcome="COMPLETATO",note="",attachments=None):
  with self._lock:x=self._find(p);complete_task(x,t,a,self._role(a),outcome,note,attachments);self._persist();return serialize_practice(x)
 def assign_task(self,p,t,assignee,a):
  if self._role(assignee)!=UserRole.OPERATORE:raise PermissionError("L'assegnatario deve avere ruolo OPERATORE")
  with self._lock:x=self._find(p);assign_task(x,t,assignee,a,self._role(a));self._persist();return serialize_practice(x)
 def reopen_task(self,p,t,a,reason=""):
  with self._lock:x=self._find(p);reopen_task(x,t,a,self._role(a),reason);self._persist();return serialize_practice(x)
 def validate(self,p,a,outcome="VALIDATA",note="",attachments=None):
  with self._lock:x=self._find(p);validate_practice(x,a,self._role(a),outcome,note,attachments);self._persist();return serialize_practice(x)
 def close(self,p,a,outcome="CHIUSA",note="",attachments=None):
  with self._lock:x=self._find(p);close_practice(x,a,self._role(a),outcome,note,attachments);self._persist();return serialize_practice(x)
 def _find(self,id):
  try:return self._practices[id]
  except KeyError as e:raise KeyError(f"Pratica inesistente: {id}") from e
 @staticmethod
 def _find_task(p,c):
  t=next((x for x in p.tasks if x.code==c),None)
  if t is None:raise KeyError(f"Task inesistente: {c}")
  return t
