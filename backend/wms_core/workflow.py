from __future__ import annotations
import base64
from datetime import datetime,timezone
from .models import Evidence,Practice,PracticeStatus,Task,TaskNote,TaskStatus,UserRole,WorkResult
class WorkflowError(ValueError):pass
MAX_EVIDENCE_BYTES=5*1024*1024
def _add_evidence(practice,*,actor,actor_role,attachments,source,task_code=None):
 ids=[]
 for item in attachments or []:
  if not isinstance(item,dict):raise WorkflowError("Formato evidenza non valido")
  filename=str(item.get("filename","")).strip()
  if not filename:raise WorkflowError("Ogni evidenza deve avere un nome file")
  content=str(item.get("content_base64") or "")
  try:raw=base64.b64decode(content,validate=True) if content else b""
  except ValueError as e:raise WorkflowError("Contenuto evidenza non valido") from e
  if len(raw)>MAX_EVIDENCE_BYTES:raise WorkflowError("Ogni documento può avere dimensione massima di 5 MB")
  ev=Evidence(id=f"E-{len(practice.evidence)+1:04}",filename=filename,content_type=str(item.get("content_type") or "application/octet-stream"),description=str(item.get("description") or "").strip(),document_type=str(item.get("document_type") or "DOCUMENTO").strip() or "DOCUMENTO",content_base64=content,size_bytes=len(raw),actor=actor,actor_role=actor_role,source=source,related_practice_id=practice.id,related_task_code=task_code);practice.evidence.append(ev);ids.append(ev.id);practice.record("EVIDENCE_ADDED",actor,evidence_id=ev.id,task_code=task_code,source=source)
 return ids
def _record_result(practice,*,actor,actor_role,outcome,note,attachments,action,task_code=None,existing_evidence_ids=None):
 outcome=outcome.strip();note=note.strip()
 if not outcome:raise WorkflowError("L'esito è obbligatorio")
 ids=list(existing_evidence_ids or []);ids.extend(_add_evidence(practice,actor=actor,actor_role=actor_role,attachments=attachments,source=action,task_code=task_code));r=WorkResult(id=f"R-{len(practice.results)+1:04}",actor=actor,actor_role=actor_role,outcome=outcome,note=note,related_practice_id=practice.id,related_task_code=task_code,evidence_ids=tuple(ids),action=action);practice.results.append(r);practice.record("WORK_RESULT_RECORDED",actor,result_id=r.id,task_code=task_code);return r
def _transition(p,target,actor):previous=p.status;p.status=target;p.record("PRACTICE_STATUS_CHANGED",actor,previous=previous.value,current=target.value)
def _task(p,code):
 t=next((x for x in p.tasks if x.code==code),None)
 if t is None:raise WorkflowError(f"Task inesistente: {code}")
 return t
def _require_role(actual,expected,message):
 if actual!=expected:raise WorkflowError(message)
def assign_task(p,task_code,assignee,actor,actor_role):
 _require_role(actor_role,UserRole.MANAGER,"Solo un manager può assegnare i task")
 if p.status in {PracticeStatus.VALIDATA,PracticeStatus.CHIUSA}:raise WorkflowError("I task non possono essere assegnati dopo la validazione")
 t=_task(p,task_code)
 if t.status==TaskStatus.COMPLETATO:raise WorkflowError("Un task completato deve essere riaperto prima di riassegnarlo")
 previous=t.assignee;t.assignee=assignee;p.record("TASK_ASSIGNED",actor,task_code=t.code,previous=previous,assignee=assignee)
def start_practice(p,actor):
 if p.status!=PracticeStatus.DA_FARE:raise WorkflowError("La pratica può essere avviata solo da DA_FARE")
 _transition(p,PracticeStatus.IN_LAVORAZIONE,actor)
def save_task_progress(p,task_code,actor,actor_role,note="",attachments=None):
 _require_role(actor_role,UserRole.OPERATORE,"Solo un operatore può lavorare i task")
 if p.status not in {PracticeStatus.DA_FARE,PracticeStatus.IN_LAVORAZIONE}:raise WorkflowError("Il task non può essere lavorato nello stato corrente")
 t=_task(p,task_code)
 if t.assignee!=actor:raise WorkflowError("Il task può essere lavorato solo dall'operatore assegnatario")
 if t.status==TaskStatus.COMPLETATO:raise WorkflowError("Il task è già completato")
 if p.status==PracticeStatus.DA_FARE:start_practice(p,actor)
 previous=t.status;t.status=TaskStatus.IN_LAVORAZIONE;clean=note.strip()
 if clean:t.work_note=clean;t.work_notes.append(TaskNote(actor=actor,note=clean))
 ids=_add_evidence(p,actor=actor,actor_role=actor_role,attachments=attachments,source="TASK_PROGRESS",task_code=t.code);t.progress_evidence_ids.extend(ids);p.record("TASK_PROGRESS_SAVED",actor,task_code=t.code,previous=previous.value,current=t.status.value,note=clean,evidence_ids=ids)
def complete_task(p,task_code,actor,actor_role,outcome="COMPLETATO",note="",attachments=None):
 _require_role(actor_role,UserRole.OPERATORE,"Solo un operatore può completare i task")
 if p.status not in {PracticeStatus.IN_LAVORAZIONE,PracticeStatus.DA_FARE}:raise WorkflowError("I task non possono essere completati nello stato corrente")
 t=_task(p,task_code)
 if t.assignee!=actor:raise WorkflowError("Il task può essere completato solo dall'operatore assegnatario")
 if t.status==TaskStatus.COMPLETATO:raise WorkflowError("Il task è già completato")
 missing=[c for c in t.depends_on if _task(p,c).status!=TaskStatus.COMPLETATO]
 if missing:raise WorkflowError(f"Dipendenze non completate: {', '.join(missing)}")
 if p.status==PracticeStatus.DA_FARE:start_practice(p,actor)
 r=_record_result(p,actor=actor,actor_role=actor_role,outcome=outcome,note=note,attachments=attachments,action="TASK",task_code=t.code,existing_evidence_ids=t.progress_evidence_ids);t.status=TaskStatus.COMPLETATO;t.completed_by=actor;t.result_id=r.id;t.work_note="";t.reopen_reason="";t.progress_evidence_ids=[];p.record("TASK_COMPLETED",actor,task_code=t.code,result_id=r.id)
 if p.required_tasks_complete:_transition(p,PracticeStatus.COMPLETATA,actor);(_transition(p,PracticeStatus.DA_VALIDARE,actor) if p.requires_validation else None)
def reopen_task(p,task_code,actor,actor_role,reason=""):
 _require_role(actor_role,UserRole.MANAGER,"Solo un manager può riaprire i task")
 if p.status not in {PracticeStatus.IN_LAVORAZIONE,PracticeStatus.DA_VALIDARE,PracticeStatus.NON_VALIDATA}:raise WorkflowError("I task possono essere riaperti solo prima della validazione")
 reason=reason.strip()
 if not reason:raise WorkflowError("La motivazione della riapertura è obbligatoria")
 t=_task(p,task_code)
 if t.status!=TaskStatus.COMPLETATO:raise WorkflowError("Solo un task completato può essere riaperto")
 previous_by=t.completed_by;previous_result=t.result_id;t.status=TaskStatus.IN_LAVORAZIONE;t.completed_by=None;t.result_id=None;t.reopen_reason=reason;t.work_note="";t.progress_evidence_ids=[];p.record("TASK_REOPENED",actor,task_code=t.code,previous_completed_by=previous_by,previous_result_id=previous_result,reason=reason)
 if p.status in {PracticeStatus.DA_VALIDARE,PracticeStatus.NON_VALIDATA}:_transition(p,PracticeStatus.IN_LAVORAZIONE,actor)
def validate_practice(p,actor,actor_role,outcome="VALIDATA",note="",attachments=None):
 _require_role(actor_role,UserRole.VALIDATORE,"Solo un validatore può validare la pratica")
 if p.status!=PracticeStatus.DA_VALIDARE or not p.required_tasks_complete:raise WorkflowError("La pratica non è pronta per la validazione")
 if any(e.event_type=="TASK_COMPLETED" and e.actor==actor for e in p.audit):raise WorkflowError("Chi ha eseguito task della pratica non può validarla")
 outcome=outcome.strip().upper()
 if outcome not in {"VALIDATA","VALIDATA_CON_RILIEVI","NON_VALIDATA"}:raise WorkflowError("Esito di validazione non valido")
 if outcome in {"VALIDATA_CON_RILIEVI","NON_VALIDATA"} and not note.strip():raise WorkflowError("La motivazione è obbligatoria per questo esito")
 r=_record_result(p,actor=actor,actor_role=actor_role,outcome=outcome,note=note,attachments=attachments,action="VALIDATION");p.validation_result_id=r.id
 if outcome=="NON_VALIDATA":p.validated_by=None;p.validated_at=None;_transition(p,PracticeStatus.NON_VALIDATA,actor);p.record("PRACTICE_NOT_VALIDATED",actor,result_id=r.id,reason=note.strip());return
 p.validated_by=actor;p.validated_at=datetime.now(timezone.utc);_transition(p,PracticeStatus.VALIDATA,actor);p.record("PRACTICE_VALIDATED",actor,result_id=r.id)
def close_practice(p,actor,actor_role,outcome="CHIUSA",note="",attachments=None):
 _require_role(actor_role,UserRole.MANAGER,"Solo un manager può chiudere la pratica");allowed=PracticeStatus.VALIDATA if p.requires_validation else PracticeStatus.COMPLETATA
 if p.status!=allowed:raise WorkflowError("La pratica non può essere chiusa nello stato corrente")
 r=_record_result(p,actor=actor,actor_role=actor_role,outcome=outcome,note=note,attachments=attachments,action="CLOSURE");p.closure_result_id=r.id;_transition(p,PracticeStatus.CHIUSA,actor);p.record("PRACTICE_CLOSED",actor,result_id=r.id)
