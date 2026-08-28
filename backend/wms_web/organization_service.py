from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.wms_core.models import UserRole
from backend.wms_core.workflow import close_practice, complete_task, reopen_task, save_task_progress, validate_practice
from backend.wms_web.service import RECENT_COMPLETED_HOURS, PracticeService, _date, _evidence, _result, _summary, _task, serialize_practice


class OrganizationalPracticeService(PracticeService):
    """Adapter for the organizational model: user -> membership -> group -> role.

    Tasks are owned by groups. A person may claim a task when starting work; the
    claim is operational and never replaces the group's organizational ownership.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._migrate_group_assignments()

    @staticmethod
    def _role(principal):
        try:
            return UserRole(principal["role"])
        except (KeyError, ValueError) as error:
            raise PermissionError("Ruolo attivo non valido") from error

    @staticmethod
    def _require_role(principal, role, message):
        if OrganizationalPracticeService._role(principal) != role:
            raise PermissionError(message)

    def _migrate_group_assignments(self):
        changed = False
        with self._lock:
            for practice in self._practices.values():
                for task in practice.tasks:
                    if not getattr(task, "assigned_group", None):
                        # Tutti i task demo contabili precedenti erano distribuiti ad Anna/Luca.
                        task.assigned_group = "contabili"
                        changed = True
                    legacy = getattr(task, "assignee", None)
                    if legacy:
                        task.assignee = None
                        changed = True
                    if not hasattr(task, "claimed_by"):
                        task.claimed_by = None
                        changed = True
            if changed:
                self._persist()

    @staticmethod
    def _serialize_task(task):
        row = _task(task)
        row["assigned_group"] = task.assigned_group
        row["claimed_by"] = task.claimed_by
        row.pop("assignee", None)
        return row

    def get_for(self, practice_id, principal):
        with self._lock:
            data = serialize_practice(self._find(practice_id))
            for row, task in zip(data["tasks"], self._find(practice_id).tasks):
                row["assigned_group"] = task.assigned_group
                row["claimed_by"] = task.claimed_by
                row.pop("assignee", None)
            data["active_context"] = principal
            return data

    def manager_practices_for(self, principal):
        self._require_role(principal, UserRole.MANAGER, "La lista pratiche è riservata al manager")
        with self._lock:
            return sorted([_summary(p) for p in self._practices.values() if p.status.value != "CHIUSA"], key=lambda r:(r["urgency_sort"],r["due_date"],r["id"]))

    def validation_queue_for(self, principal):
        self._require_role(principal, UserRole.VALIDATORE, "La coda di validazione è riservata al validatore")
        with self._lock:
            rows=[]
            for practice in self._practices.values():
                if practice.status.value != "DA_VALIDARE": continue
                row=_summary(practice)
                entered=next((e.at for e in reversed(practice.audit) if e.event_type=="PRACTICE_STATUS_CHANGED" and e.details.get("current")=="DA_VALIDARE"),None)
                row["waiting_since"]=_date(entered);row["waiting_hours"]=round((datetime.now(timezone.utc)-entered).total_seconds()/3600,1) if entered else None;rows.append(row)
            return sorted(rows,key=lambda r:(r["urgency_sort"],r.get("waiting_since") or "",r["id"]))

    def validation_history_for(self, principal):
        self._require_role(principal, UserRole.VALIDATORE, "Lo storico validazioni è riservato al validatore")
        actor=principal["username"];cutoff=datetime.now(timezone.utc)-timedelta(hours=RECENT_COMPLETED_HOURS);rows=[]
        with self._lock:
            for practice in self._practices.values():
                result=next((r for r in reversed(practice.results) if r.action=="VALIDATION" and r.actor==actor),None)
                if result is None or result.timestamp<cutoff:continue
                row=_summary(practice);row.update({"validated_at":_date(result.timestamp),"validation_outcome":result.outcome,"validation_note":result.note});rows.append(row)
        return sorted(rows,key=lambda r:r["validated_at"],reverse=True)

    def work_queue_for(self, principal):
        self._require_role(principal, UserRole.OPERATORE, "I miei compiti sono riservati agli operatori")
        group=principal["group_id"];actor=principal["username"];cutoff=datetime.now(timezone.utc)-timedelta(hours=RECENT_COMPLETED_HOURS);rows=[]
        with self._lock:
            for practice in self._practices.values():
                results={r.id:r for r in practice.results}
                for task in practice.tasks:
                    if task.assigned_group != group:continue
                    # Un task preso in carico da un collega resta del gruppo ma non appare tra i propri task attivi.
                    if task.claimed_by and task.claimed_by != actor and task.status.value != "COMPLETATO":continue
                    row={"practice_id":practice.id,"practice_type_code":practice.practice_type_code,"client_id":practice.client_id,"due_date":practice.due_date,**self._serialize_task(task)}
                    if task.status.value!="COMPLETATO":row["queue_section"]="ACTIVE";rows.append(row);continue
                    result=results.get(task.result_id)
                    if result and result.actor==actor and result.timestamp>=cutoff:
                        row.update({"queue_section":"RECENT_COMPLETED","completed_at":_date(result.timestamp),"outcome":result.outcome,"result_note":result.note});rows.append(row)
            return rows

    def task_detail_for(self, practice_id, task_code, principal, include_context=False):
        self._require_role(principal, UserRole.OPERATORE, "L'attività è riservata agli operatori")
        actor=principal["username"]
        with self._lock:
            practice=self._find(practice_id);task=self._find_task(practice,task_code)
            if task.assigned_group!=principal["group_id"]:raise PermissionError("Attività non assegnata al gruppo attivo")
            if task.claimed_by and task.claimed_by!=actor:raise PermissionError("Attività già presa in carico da un altro operatore")
            evidences={item.id:_evidence(item) for item in practice.evidence};journal=[]
            for event in reversed(practice.audit):
                if event.details.get("task_code")!=task.code:continue
                if event.event_type=="TASK_PROGRESS_SAVED":
                    ids=event.details.get("evidence_ids") or [];journal.append({"type":"PROGRESS","actor":event.actor,"at":_date(event.at),"note":event.details.get("note") or "","evidence":[evidences[e] for e in ids if e in evidences]})
                elif event.event_type=="TASK_REOPENED":journal.append({"type":"REOPENED","actor":event.actor,"at":_date(event.at),"note":event.details.get("reason") or "","evidence":[]})
            detail={"practice":{"id":practice.id,"type":practice.practice_type_code,"client_id":practice.client_id,"period_start":practice.period_start,"period_end":practice.period_end,"due_date":practice.due_date},"task":self._serialize_task(task),"task_journal":journal,"task_progress_evidence":[evidences[e] for e in task.progress_evidence_ids if e in evidences]}
            if include_context:
                titles={t.code:t.title for t in practice.tasks};previous=[]
                for result in practice.results:
                    if result.related_task_code==task.code:continue
                    row=_result(result);row["related_task_title"]=titles.get(result.related_task_code or "");row["evidence"]=[evidences[e] for e in result.evidence_ids if e in evidences];previous.append(row)
                detail["previous_results"]=previous;detail["evidence"]=[_evidence(i) for i in practice.evidence]
            return detail

    def _claim(self, task, principal, practice):
        if task.assigned_group != principal["group_id"]:raise PermissionError("Il task appartiene a un altro gruppo")
        actor=principal["username"]
        if task.claimed_by and task.claimed_by!=actor:raise PermissionError("Il task è già preso in carico da un altro operatore")
        if not task.claimed_by:
            task.claimed_by=actor;practice.record("TASK_CLAIMED",actor,task_code=task.code,group=task.assigned_group)
        # Compatibilità transitoria con le invarianti del core: assignee riflette il claim, non l'assegnazione organizzativa.
        task.assignee=actor
        return actor

    def save_task_progress_for(self, practice_id, task_code, principal, note="", attachments=None):
        self._require_role(principal,UserRole.OPERATORE,"Solo un operatore può lavorare i task")
        with self._lock:
            p=self._find(practice_id);t=self._find_task(p,task_code);actor=self._claim(t,principal,p);save_task_progress(p,task_code,actor,UserRole.OPERATORE,note,attachments);self._persist();return self.get_for(practice_id,principal)

    def complete_task_for(self, practice_id, task_code, principal, outcome="COMPLETATO", note="", attachments=None):
        self._require_role(principal,UserRole.OPERATORE,"Solo un operatore può completare i task")
        with self._lock:
            p=self._find(practice_id);t=self._find_task(p,task_code);actor=self._claim(t,principal,p);complete_task(p,task_code,actor,UserRole.OPERATORE,outcome,note,attachments);self._persist();return self.get_for(practice_id,principal)

    def reopen_task_for(self, practice_id, task_code, principal, reason=""):
        self._require_role(principal,UserRole.MANAGER,"Solo un manager può riaprire i task")
        with self._lock:
            p=self._find(practice_id);t=self._find_task(p,task_code);reopen_task(p,task_code,principal["username"],UserRole.MANAGER,reason);t.claimed_by=None;t.assignee=None;self._persist();return self.get_for(practice_id,principal)

    def validate_for(self, practice_id, principal, outcome="VALIDATA", note="", attachments=None):
        self._require_role(principal,UserRole.VALIDATORE,"Solo un validatore può validare la pratica")
        with self._lock:
            p=self._find(practice_id);validate_practice(p,principal["username"],UserRole.VALIDATORE,outcome,note,attachments);self._persist();return self.get_for(practice_id,principal)

    def close_for(self, practice_id, principal, outcome="CHIUSA", note="", attachments=None):
        self._require_role(principal,UserRole.MANAGER,"Solo un manager può chiudere la pratica")
        with self._lock:
            p=self._find(practice_id);close_practice(p,principal["username"],UserRole.MANAGER,outcome,note,attachments);self._persist();return self.get_for(practice_id,principal)

    def assign_group_for(self, practice_id, task_code, group_id, principal):
        self._require_role(principal,UserRole.MANAGER,"Solo un manager può modificare il gruppo assegnatario")
        with self._lock:
            p=self._find(practice_id);t=self._find_task(p,task_code);previous=t.assigned_group;t.assigned_group=group_id;t.claimed_by=None;t.assignee=None;p.record("TASK_GROUP_ASSIGNED",principal["username"],task_code=t.code,previous_group=previous,assigned_group=group_id);self._persist();return self.get_for(practice_id,principal)
