import { Component, DestroyRef, OnInit, inject, signal, viewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Api, message, segment } from '../core/api';
import { Auth } from '../core/auth';
import { Practice as PracticeData, Task } from '../core/models';
import { Attachments } from '../shared/attachments';
import { EvidenceList } from '../shared/evidence';
import { WorkflowGraph } from '../shared/workflow-graph';
import { Results } from '../shared/results';
@Component({ selector: 'wms-practice', imports: [CommonModule, FormsModule, RouterLink, Attachments, EvidenceList, Results, WorkflowGraph], templateUrl: './practice.html' })
export class Practice implements OnInit {
  private router=inject(Router);
  openValidation() {
    this.practiceView='dossier';
    setTimeout(()=>{const section=document.getElementById('validation-activity');section?.scrollIntoView({block:'center',behavior:'smooth'});section?.focus();},0);
  }
  validationResults() {return this.data()?.results.filter(r=>r.action==='VALIDATION') || [];}

  openGraphTask(code:string) { const p=this.data(); if(p) void this.router.navigate(['/practices',p.id,'tasks',code]); }
  private api = inject(Api); private route = inject(ActivatedRoute); private destroy = inject(DestroyRef);
  auth = inject(Auth); data = signal<PracticeData | null>(null); loading = signal(true); busy = signal(false); error = signal('');
  groups = signal<{id: string; name: string}[]>([]); taskCode = ''; reason: Record<string, string> = {}; group: Record<string, string> = {};
  selection: Record<string, boolean> = {}; instruction = ''; outcome = ''; note = ''; private version = 0;
  attachments = viewChild(Attachments);
  dossierTab = 'documents';
  practiceView = 'dossier';
  practiceKey(event:KeyboardEvent) {
    if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key)) return;
    event.preventDefault();
    this.practiceView=event.key==='Home'?'dossier':event.key==='End'?'graph':this.practiceView==='dossier'?'graph':'dossier';
    (event.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>('[role=tab]')[this.practiceView==='dossier'?0:1]?.focus();
  }
  reachedTasks() { return this.data()?.tasks.filter(t=>t.active!==false) || []; }
  currentTasks() { return this.reachedTasks().filter(t=>t.status!=='COMPLETATO'); }
  operational() { return ['DA_FARE','IN_LAVORAZIONE'].includes(this.data()?.status || ''); }
  taskResults(t:Task) { return (this.data()?.results || []).filter(r=>r.related_task_code===t.code).sort((a,b)=>b.timestamp.localeCompare(a.timestamp)); }
  taskEvidence(t:Task) {
    const ids=new Set(this.taskResults(t).flatMap(r=>r.evidence_ids));
    return (this.data()?.evidence || []).filter(e=>e.related_task_code===t.code || ids.has(e.id));
  }
  taskNotes(t:Task) {
    const events=this.data()?.audit || [];
    const notes=(t.work_notes?.length ? t.work_notes : events.filter(e=>e.event_type==='TASK_PROGRESS_SAVED' && e.details['task_code']===t.code && e.details['note']).map(e=>({actor:e.actor,at:e.at,note:String(e.details['note'])}))).map(n=>({...n,label:'Annotazione'}));
    if(!notes.length && t.work_note) notes.push({actor:t.claimed_by || '',at:'',note:t.work_note,label:'Nota corrente'});
    for(const e of events.filter(e=>e.event_type==='TASK_REOPENED' && e.details['task_code']===t.code && e.details['reason'])) notes.push({actor:e.actor,at:e.at,note:String(e.details['reason']),label:'Riapertura'});
    return notes.filter(n=>n.note.trim()).sort((a,b)=>b.at.localeCompare(a.at));
  }
  noteCount(t:Task) { return this.taskNotes(t).length+this.taskResults(t).filter(r=>r.note.trim()).length; }
  latestNote(t:Task) {
    const notes=[...this.taskNotes(t),...this.taskResults(t).filter(r=>r.note.trim()).map(r=>({note:r.note,actor:r.actor,at:r.timestamp,label:'Esito'}))];
    return notes.sort((a,b)=>b.at.localeCompare(a.at))[0];
  }
  latestNotes() { return this.reachedTasks().flatMap(t=>{const note=this.latestNote(t);return note?[{...note,code:t.code}]:[];}).sort((a,b)=>b.at.localeCompare(a.at)).slice(0,3); }
  taskStarted(t:Task) {
    const times=(this.data()?.audit || []).filter(e=>(e.details['task_code']===t.code && ['TASK_PROGRESS_SAVED','TASK_COMPLETED','TASK_CLAIMED','TASK_REOPENED'].includes(e.event_type)) || (e.event_type==='TASK_TRANSITION_SELECTED' && Array.isArray(e.details['destinations']) && e.details['destinations'].includes(t.code))).map(e=>e.at);
    times.push(...this.taskResults(t).map(r=>r.timestamp));
    return times.sort()[0] || '';
  }
  attentionItems() {
    const items:{code:string;text:string}[]=[];
    const today=new Date(), date=new Date(today.getTime()-today.getTimezoneOffset()*60000).toISOString().slice(0,10);
    for(const t of this.reachedTasks()) {
      if(t.reopen_reason) items.push({code:t.code,text:'Riaperta: '+t.reopen_reason});
      else if(t.status==='COMPLETATO' && this.taskResult(t)?.outcome.includes('RILIEV')) items.push({code:t.code,text:'Esito con rilievi'});
      if(this.operational() && t.status!=='COMPLETATO' && (t.due_date || this.data()!.due_date)<date) items.push({code:t.code,text:'Scadenza superata'});
    }
    return items;
  }
  openNonconformities() { return this.data()?.nonconformities.some(n=>n.status!=='CHIUSA') || false; }
  evidenceOrigin(code:string|null) { const task=this.data()?.tasks.find(t=>t.code===code); return task ? task.code+' · '+task.title : code || 'Documento della pratica'; }
  phaseDescription() {
    return ({DA_FARE:'Attività pronte per essere prese in carico.',IN_LAVORAZIONE:'Il lavoro prosegue sulle attività indicate qui sotto.',DA_VALIDARE:'Attività operative concluse: in attesa del validatore.',VALIDATA:'Pratica validata: pronta per la chiusura del supervisore.',NON_VALIDATA:'La pratica richiede una correzione prima di proseguire.',COMPLETATA:'Attività operative concluse: pronta per la chiusura.',CHIUSA:'Pratica chiusa. Tutto il fascicolo resta consultabile.'} as Record<string,string>)[this.data()?.status || ''] || '';
  }

  statusLabel(value: string) { return ({DA_FARE:'Da fare',IN_LAVORAZIONE:'In corso',COMPLETATO:'Completato',COMPLETATA:'Completata',DA_VALIDARE:'Da validare',VALIDATA:'Validata',NON_VALIDATA:'Non validata',CHIUSA:'Chiusa',APERTA:'Aperta',IN_SANATORIA:'In sanatoria',DA_VERIFICARE:'Da verificare'} as Record<string,string>)[value] || value.replaceAll('_',' '); }
  taskResult(t: Task) { return this.data()?.results.find(r=>r.id===t.result_id); }
  taskHealth(t: Task) { if(t.active === false) return 'unreached'; return t.status==='COMPLETATO' ? (this.taskResult(t)?.outcome.includes('RILIEV') ? 'warning' : 'done') : t.reopen_reason ? 'reopened' : t.status==='IN_LAVORAZIONE' ? 'working' : 'pending'; }
  groupName(id: string) { return this.groups().find(g=>g.id===id)?.name || id; }
  visibleEvidence() { return this.data()?.evidence.filter(e=>!this.taskCode || e.related_task_code===this.taskCode) || []; }
  visibleAudit() { return this.data()?.audit.filter(e=>!this.taskCode || e.details['task_code']===this.taskCode) || []; }
  progressPercent() { const p=this.data()?.progress; return p?.total ? Math.round(p.completed/p.total*100) : 0; }
  dossierKey(event: KeyboardEvent) {
    const keys=['results','documents','audit']; let i=keys.indexOf(this.dossierTab);
    if(event.key==='ArrowRight') i=(i+1)%3; else if(event.key==='ArrowLeft') i=(i+2)%3; else if(event.key==='Home') i=0; else if(event.key==='End') i=2; else return;
    event.preventDefault(); this.dossierTab=keys[i]; (event.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>('[role=tab]')[i]?.focus();
  }
  manager() { return this.auth.session()?.active.role === 'MANAGER'; }
  validator() { return this.auth.session()?.active.role === 'VALIDATORE'; }
  ngOnInit() { this.route.paramMap.pipe(takeUntilDestroyed(this.destroy)).subscribe(params => { this.taskCode = params.get('code') || ''; this.practiceView='dossier'; void this.load(params.get('id') || ''); }); }
  async load(id: string) {
    const version = ++this.version; this.loading.set(true); this.error.set(''); this.data.set(null); this.outcome = ''; this.note = ''; this.selection = {}; this.instruction = '';
    try {
      const [p, groups] = await Promise.all([this.api.get<PracticeData>('/practices/' + segment(id)), this.manager() ? this.api.get<{id:string; name:string}[]>('/manager/assignment-groups') : Promise.resolve([])]);
      if (version !== this.version) return;
      if (this.taskCode && !p.tasks.some(t => t.code === this.taskCode)) throw new Error('Attività inesistente.');
      this.data.set(p); this.groups.set(groups); this.setGroups(p);
    } catch (e) { if (version === this.version) this.error.set(message(e)); }
    finally { if (version === this.version) this.loading.set(false); }
  }
  setGroups(p: PracticeData) { this.group = Object.fromEntries(p.tasks.map(t => [t.code, t.assigned_group])); }
  visibleTasks() { return this.taskCode ? this.data()?.tasks.filter(t=>t.code===this.taskCode) || [] : [...this.reachedTasks()].sort((a,b)=>this.taskStarted(a).localeCompare(this.taskStarted(b))); }
  visibleResults() { return this.data()?.results.filter(r => !this.taskCode || r.related_task_code === this.taskCode) || []; }
  canReopen(t: Task) { return t.status === 'COMPLETATO' && !['VALIDATA', 'CHIUSA'].includes(this.data()?.status || ''); }
  canClose() { const p = this.data(); return p?.status === (p?.requires_validation ? 'VALIDATA' : 'COMPLETATA'); }
  selected() { return Object.keys(this.selection).filter(code => this.selection[code]); }
  canSubmit() { return !!this.outcome && (!this.validator() || this.outcome === 'VALIDATA' || !!this.note.trim()); }
  async action(action: string, body: unknown) {
    const p = this.data(); if (!p || this.busy()) return;
    this.busy.set(true); this.error.set('');
    try { const result = await this.api.post<PracticeData>(`/practices/${segment(p.id)}/${action}`, body); this.data.set({...result,client_name:p.client_name}); this.setGroups(result); this.reason = {}; this.selection = {}; this.instruction = ''; }
    catch (e) { this.error.set(message(e)); this.setGroups(p); }
    finally { this.busy.set(false); }
  }
  assign(t: Task) { return this.action(`tasks/${segment(t.code)}/assign`, { group_id: this.group[t.code] }); }
  reopen(t: Task) { return this.action(`tasks/${segment(t.code)}/reopen`, { reason: this.reason[t.code] }); }
  correct() { return this.action('corrective-action', { task_codes: this.selected(), instruction: this.instruction }); }
  async submitResult() {
    const p = this.data(); if (!p || this.busy() || !this.canSubmit()) return;
    this.busy.set(true); this.error.set('');
    try {
      const attachments = await this.attachments()?.payload() || [];
      const updated=await this.api.post<PracticeData>(`/practices/${segment(p.id)}/${this.validator() ? 'validate' : 'close'}`, { outcome: this.outcome, note: this.note, attachments });
      this.data.set({...updated,client_name:p.client_name});
      this.outcome = ''; this.note = ''; this.attachments()?.clear();
    } catch (e) { this.error.set(message(e)); }
    finally { this.busy.set(false); }
  }
}
