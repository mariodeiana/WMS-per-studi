import { Component, ElementRef, Injector, OnInit, OnDestroy, NgZone, afterNextRender, inject, signal, viewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { WorkflowGraph } from '../shared/workflow-graph';
import { GraphEdge, GraphTask, Point, graphEdges, graphOutcomes, graphNodeKinds, graphKindBackground, graphNodeSummary, wouldCreateCycle } from '../shared/workflow-graph-model';
import { Practice } from '../core/models';
import { Auth } from '../core/auth';
import { Api, message, segment } from '../core/api';

interface Row { id: string; active?: boolean; [key: string]: unknown; }
interface TaskSpec {
  code: string; title: string; instructions: string; assigned_group: string; days_before_due: number; required: boolean;
  is_initial?: boolean; graph_position?: Point | null; outcomes: string[]; transitions: Record<string, string[]>;
}
interface TaskDraft extends Omit<TaskSpec, 'outcomes' | 'transitions'> { choices: {name: string; destinations: string[]}[]; }
interface Field { key: string; label: string; type?: string; }
interface Meta { key: string; title: string; fields: Field[]; }
const fields = (...pairs: string[][]): Field[] => pairs.map(([key,label,type]) => ({key,label,type}));
interface EditorSnapshot { original:Row|null; draft:Record<string,string>; active:boolean; requiresValidation:boolean; tasks:TaskDraft[]; edgeDraft:{from:string;to:string;outcome:string}|null; originalEdge:GraphEdge|null; }
interface SavedDraft { id:string;revision:number;updated_at:string;snapshot:EditorSnapshot; }
@Component({ selector: 'wms-admin', imports: [CommonModule, FormsModule, RouterLink, WorkflowGraph], templateUrl: './admin.html' })
export class Admin implements OnInit, OnDestroy {
  private zone=inject(NgZone);private auth=inject(Auth);private draftOwner:string|undefined;
  savedDrafts=signal<SavedDraft[]>([]); draftMessage=signal(''); draftProblem=signal(false); draftSaving=signal(false);
  private draftId=''; private draftRevision=0; private savedSignature=''; private timer?:ReturnType<typeof setInterval>; private pendingDraft:Promise<boolean>|null=null;
  graphTask:TaskDraft|null=null;
  private newDraftId() {
    const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
    const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
    return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
  }

  private snapshot():EditorSnapshot { return structuredClone({original:this.original,draft:this.draft,active:this.active,requiresValidation:this.requiresValidation,tasks:this.tasks,edgeDraft:this.edgeDraft,originalEdge:this.originalEdge}); }
  private beforeUnload=(event:BeforeUnloadEvent)=>{ if(this.editor() && this.entity==='practice_types' && JSON.stringify(this.snapshot())!==this.savedSignature) {event.preventDefault();event.returnValue='';} };
  async loadDrafts() { try { this.savedDrafts.set(await this.api.get<SavedDraft[]>('/admin/model-drafts') || []); } catch { this.error.set('Impossibile recuperare le bozze. Riprova prima di iniziare un nuovo disegno.'); } }
  async persistDraft():Promise<boolean> {
    if(this.pendingDraft) { const success=await this.pendingDraft; return success ? this.persistDraft() : false; }
    if(!this.editor() || this.entity!=='practice_types') return true;
    const snapshot=this.snapshot(), signature=JSON.stringify(snapshot), id=this.draftId;
    if(signature===this.savedSignature) return true;
    this.draftSaving.set(true);this.draftMessage.set('Salvataggio bozza sul server…');
    this.pendingDraft=(async()=>{
      try {
        const saved=await this.api.post<SavedDraft>('/admin/model-drafts',{id,revision:this.draftRevision,snapshot,owner:this.draftOwner},true);
        if(id===this.draftId) { this.draftRevision=saved.revision;this.savedSignature=signature;this.draftProblem.set(false);this.draftMessage.set('Bozza salvata sul server · '+new Date(saved.updated_at).toLocaleTimeString('it-IT')); }
        this.savedDrafts.update(rows=>[saved,...rows.filter(r=>r.id!==saved.id)]);
        return true;
      } catch(e) { this.draftProblem.set(true);this.draftMessage.set('Bozza non salvata: '+message(e)+'. Mantieni aperta questa pagina.');return false; }
      finally {this.draftSaving.set(false);this.pendingDraft=null;}
    })();
    const ok=await this.pendingDraft;
    return ok && id===this.draftId && JSON.stringify(this.snapshot())!==signature ? this.persistDraft() : ok;
  }
  async saveDraftCopy() { if(this.pendingDraft) await this.pendingDraft;this.draftId=this.newDraftId();this.draftRevision=0;this.savedSignature='';await this.persistDraft(); }
  resumeDraft(saved:SavedDraft) {
    this.entity='practice_types';this.open(saved.snapshot.original);
    const state=structuredClone(saved.snapshot);this.original=state.original;this.draft=state.draft;this.active=state.active;this.requiresValidation=state.requiresValidation;this.tasks=state.tasks;this.edgeDraft=state.edgeDraft;this.originalEdge=state.originalEdge;this.draftId=saved.id;this.draftRevision=saved.revision;this.savedSignature=JSON.stringify(this.snapshot());this.modelTab='tasks';this.draftMessage.set('Bozza recuperata dal server. Salva modifiche per aggiornare il modello.');
  }
  async discardDraft(saved:SavedDraft) {
    if(!confirm('Eliminare questa bozza? Il modello pubblicato resta invariato.')) return;
    try {await this.api.post('/admin/model-drafts/delete',{id:saved.id,revision:saved.revision},true);this.savedDrafts.update(rows=>rows.filter(r=>r.id!==saved.id));} catch(e) {this.error.set(message(e));}
  }
  private api = inject(Api); private injector = inject(Injector);
  editorDialog = viewChild<ElementRef<HTMLDialogElement>>('editorDialog');
  practiceDialog = viewChild<ElementRef<HTMLDialogElement>>('practiceDialog');
  edgeDraft: {from:string;to:string;outcome:string} | null = null; originalEdge: GraphEdge | null = null; edgeError='';
  clientTab = 'general'; repertoire: string[] = [];
  clientTabs = [{key:'general',label:'Anagrafica'},{key:'fiscal',label:'Dati fiscali'},{key:'repertoire',label:'REPERTORIO'},{key:'practices',label:'Pratiche'}];
  clientPractices() { return this.practices().filter(p=>p['client_id']===this.original?.id); }
  clientFields(tab: string) { return this.current().fields.filter(f=>['tax_code','vat_number','gis_company_code','accounting_regime','vat_settlement_type'].includes(f.key) === (tab==='fiscal')); }
  economicLabel(value: unknown) { return value==='IN_REPERTORIO'?'In repertorio':value==='EXTRA_CONTRATTO'?'Extra contratto':'Non rilevato (storico)'; }
  modelTab = 'general'; expandedTask: TaskDraft | null = null;
  practicePreview = signal<Practice | null>(null);
  filter = '';
  help() { return ({clients:'Completa e organizza le anagrafiche dei clienti.', practice_types:'Modelli di lavoro: attività, responsabilità, esiti e scadenze. Le modifiche si applicano alle nuove pratiche.', practices:'Pratiche generate dai modelli, con attività e assegnazioni già predisposte.', users:'Utenti e contesto operativo predefinito.', groups:'Gruppi di lavoro e responsabilità.', memberships:'Collega gli utenti ai gruppi e ai ruoli operativi.', assignment_policies:'Regole di presa in carico delle attività.'} as Record<string,string>)[this.entity] || ''; }
  filteredRows() { const q=this.filter.trim().toLocaleLowerCase('it'); return this.rows().filter(row=>!q || this.current().fields.some(f=>this.display(row,f.key).toLocaleLowerCase('it').includes(q))); }
  taskCount(row: Row) { return ((row['tasks'] || []) as unknown[]).length; }
  groupColor(id:string) { return String(this.values('groups').find(g=>g.id===id)?.['color'] || '#edf1f5'); }
  groupName(id: string) { const group=this.values('groups').find(g=>g.id===id); return group ? this.label(group) : id || 'Gruppo da scegliere'; }
  private reveal(dialog: 'editor' | 'practice') {
    afterNextRender(()=>{
      const el=(dialog==='editor'?this.editorDialog():this.practiceDialog())?.nativeElement;
      if(el && (dialog==='editor'?this.editor():!!this.practicePreview()) && !el.open) el.showModal();
    },{injector:this.injector});
  }
  async closeEditor() { if(this.busy()) return false; if(!await this.persistDraft()) return false;this.editorDialog()?.nativeElement.close();this.editor.set(false);return true; }
  cancelEditor(event: Event) { event.preventDefault(); this.closeEditor(); }
  closePractice() { this.practiceDialog()?.nativeElement.close(); this.practicePreview.set(null); }
  async showPractice(row: Row) {
    if(this.busy()) return; this.busy.set(true); this.error.set('');
    try { this.practicePreview.set(await this.api.get<Practice>('/practices/'+segment(row.id))); this.reveal('practice'); }
    catch(e) { this.error.set(message(e)); } finally { this.busy.set(false); }
  }
  tabKey(event: KeyboardEvent, type: 'entity' | 'model' | 'client') {
    const keys=type==='entity'?this.meta.map(m=>m.key):type==='client'?this.clientTabs.map(t=>t.key):['general','tasks'];
    const current=type==='entity'?this.entity:type==='client'?this.clientTab:this.modelTab;
    let index=keys.indexOf(current);
    if(event.key==='ArrowRight') index=(index+1)%keys.length;
    else if(event.key==='ArrowLeft') index=(index+keys.length-1)%keys.length;
    else if(event.key==='Home') index=0;
    else if(event.key==='End') index=keys.length-1;
    else return;
    event.preventDefault(); if(type==='entity') this.select(keys[index]); else if(type==='client') this.clientTab=keys[index]; else this.modelTab=keys[index];
    (event.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>('[role=tab]')[index]?.focus();
  }
  config = signal<Record<string, Row[]>>({}); roles = signal<string[]>([]); practices = signal<Row[]>([]);
  loading = signal(true); busy = signal(false); error = signal(''); editor = signal(false); formError = signal('');
  entity = 'groups'; original: Row | null = null; draft: Record<string, string> = {}; active = true; requiresValidation = true; tasks: TaskDraft[] = [];
  meta: Meta[] = [
    {key:'users',title:'Utenti',fields:fields(['id','ID'],['username','Login'],['display_name','Nome visualizzato'],['default_membership_id','Appartenenza predefinita'])},
    {key:'groups',title:'Gruppi',fields:fields(['id','Codice'],['name','Nome'],['role','Ruolo'])},
    {key:'memberships',title:'Appartenenze',fields:fields(['id','ID'],['user_id','Utente'],['group_id','Gruppo'],['label','Etichetta'])},
    {key:'assignment_policies',title:'Politiche di assegnazione',fields:fields(['id','Codice'],['name','Nome'],['strategy','Strategia'],['description','Descrizione','textarea'])},
    {key:'practice_types',title:'Tipi di pratica',fields:fields(['id','ID'],['code','Codice'],['name','Nome'],['description','Descrizione','textarea'])},
    {key:'clients',title:'Clienti',fields:fields(['id','Codice cliente'],['name','Ragione sociale'],['tax_code','Codice fiscale'],['vat_number','Partita IVA'],['email','Email','email'],['gis_company_code','Cod. Azienda GIS'],['accounting_regime','Regime contabile'],['vat_settlement_type','Tipo liquidazione IVA'],['notes','Note','textarea'])},
    {key:'practices',title:'Pratiche',fields:fields(['id','Codice'],['client_id','Cliente'],['practice_type_code','Tipo'],['period_start','Dal'],['period_end','Al'],['due_date','Scadenza'])}
  ];
  current() { return this.meta.find(m => m.key === this.entity)!; }
  rows() { return this.entity === 'practices' ? this.practices() : this.config()[this.entity] || []; }
  values(entity: string, activeOnly = false) { return (this.config()[entity] || []).filter(r => !activeOnly || r.active !== false); }
  operators() { return this.values('groups').filter(g => g['role'] === 'OPERATORE'); }
  label(row: Row) { return String(row['name'] || row['display_name'] || row['label'] || row.id); }
  display(row: Row, key: string) {
    const entity = ({user_id:'users',group_id:'groups',client_id:'clients'} as Record<string,string>)[key];
    const related = entity && this.values(entity).find(r => r.id === row[key]);
    return related ? this.label(related) : this.roleLabel(String(row[key] ?? ''));
  }
  ngOnInit() {
    void this.load();window.addEventListener('beforeunload',this.beforeUnload);
    this.zone.runOutsideAngular(()=>{this.timer=setInterval(()=>{if(!this.busy()) this.zone.run(()=>void this.persistDraft());},1000);});
  }
  ngOnDestroy() {if(this.timer)clearInterval(this.timer);window.removeEventListener('beforeunload',this.beforeUnload);}

  async load() {
    this.loading.set(true); this.error.set('');
    try {
      const [config, practices] = await Promise.all([this.api.get<Record<string, unknown>>('/admin/config'), this.api.get<Row[]>('/admin/practices')]);
      this.roles.set(config['roles'] as string[]); this.config.set(Object.fromEntries(this.meta.filter(m => m.key !== 'practices').map(m => [m.key, config[m.key] as Row[]]))); this.practices.set(practices);await this.loadDrafts();
    } catch (e) { this.error.set(message(e)); } finally { this.loading.set(false); }
  }
  open(row: Row | null = null) {
    this.clientTab='general'; this.repertoire=[...((row?.['repertoire'] || []) as string[])];
    this.draftOwner=this.auth.session()?.user.username;
    this.draftId=this.newDraftId();this.draftRevision=0;this.draftMessage.set('Le modifiche sono salvate automaticamente come bozza.');this.draftProblem.set(false);this.graphTask=null;
    this.modelTab='general'; this.expandedTask=null; this.edgeDraft=null; this.originalEdge=null;
    this.original = row; this.draft = {}; this.formError.set('');
    for (const field of this.current().fields) this.draft[field.key] = String(row?.[field.key] ?? '');
    if (this.entity === 'groups' && !row) this.draft['role'] = 'OPERATORE';
    this.active = row?.active !== false; this.requiresValidation = row?.['requires_validation'] !== false;
    this.tasks = structuredClone((row?.['tasks'] || []) as TaskSpec[]).map(t => ({...t, choices:[...new Set([...(t.outcomes || []), ...Object.keys(t.transitions || {})])].map(name => ({name,destinations:[...(t.transitions?.[name] || [])]}))}));
    const legacy=!this.tasks.some(t=>t.is_initial !== undefined);
    for(const task of this.tasks) task.is_initial=legacy ? !this.tasks.some(t=>t.choices.some(c=>c.destinations.includes(task.code))) : task.is_initial === true;
    if (this.entity === 'practices') this.draft['model_id'] = '';
    this.savedSignature=JSON.stringify(this.snapshot());
    this.editor.set(true); this.reveal('editor');
  }
  async select(entity: string) { if(this.editor() && !await this.closeEditor()) return;this.entity=entity;this.filter='';this.error.set(''); }
  addTask(position?:Point) {
    if(this.edgeDraft) {this.edgeError='Applica o annulla prima il collegamento in modifica.';return;}
    let index=1; while(this.tasks.some(t=>t.code==='A'+index)) index++;
    const task:TaskDraft={code:'A'+index,title:'Nuova attività',instructions:'',assigned_group:this.operators().find(g=>g.active!==false)?.id || '',days_before_due:0,required:true,is_initial:this.tasks.length===0,choices:[]};
    if(position) task.graph_position={...position};
    this.tasks.push(task);this.expandedTask=null;this.graphTask=task;
  }
  private graphSignature=''; private graphSnapshot:GraphTask[]=[];
  graphTasks(): GraphTask[] {
    const unique=new Set<string>();
    const nodes=this.tasks.filter(t=>t.code && t.code!=='@END' && !unique.has(t.code) && !!unique.add(t.code)).map(t=>({...t,assigned_group_name:this.groupName(t.assigned_group),assigned_group_color:this.groupColor(t.assigned_group),outcomes:t.choices.map(c=>c.name).filter(n=>n && n!=='*'),transitions:Object.fromEntries(t.choices.filter(c=>c.name).map(c=>[c.name,c.destinations]))}));
    const signature=JSON.stringify(nodes);
    if(signature!==this.graphSignature) { this.graphSignature=signature; this.graphSnapshot=structuredClone(nodes); }
    return this.graphSnapshot;
  }
  openGraphTask(code:string) { if(this.edgeDraft) {this.edgeError='Applica o annulla prima il collegamento in modifica.';return;} this.graphTask=this.tasks.find(t=>t.code===code)||null;this.edgeDraft=null;this.originalEdge=null; }
  moveGraphNode(change:{code:string;position:Point}) {
    if(this.busy()) return;
    const task=this.tasks.find(t=>t.code===change.code); if(task) task.graph_position={...change.position};
  }
  arrangeGraph() { if(!this.busy()) for(const task of this.tasks) delete task.graph_position; }
  newEdge(connection?:{from:string;to:string;outcome?:string}) {
    if(this.busy()) return;
    if(this.edgeDraft) {this.edgeError='Applica o annulla prima il collegamento in modifica.';return;}
    this.graphTask=null;this.originalEdge=null; this.edgeError='';
    this.edgeDraft={from:connection?.from || this.tasks[0]?.code || '',to:connection?.to || '@END',outcome:connection?.outcome || '*'};
  }
  editEdge(edge:GraphEdge) {
    if(this.busy()) return;
    if(this.edgeDraft && (this.originalEdge?.id===edge.id || (!this.originalEdge && this.edgeDraft.from===edge.from && this.edgeDraft.to===edge.to && this.edgeDraft.outcome===edge.outcome)))return;
    if(this.edgeDraft) {this.edgeError='Applica o annulla prima il collegamento in modifica.';return;}
    this.graphTask=null;this.originalEdge=edge.implicit?null:edge; this.edgeError='';
    this.edgeDraft={from:edge.from,to:edge.to,outcome:edge.outcome};
  }
  saveEdge() {
    if(!this.edgeDraft || this.busy()) return;
    const {from,to}=this.edgeDraft, outcome=this.edgeDraft.outcome.trim();
    const source=this.tasks.find(t=>t.code===from);
    if(!source || !outcome || (to!=='@END'&&!this.tasks.some(t=>t.code===to))) { this.edgeError='Seleziona origine, esito e destinazione.'; return; }
    const graph=this.graphTasks().map(t=>({...t,transitions:Object.fromEntries(Object.entries(t.transitions).map(([key,ds])=>[key,[...ds]]))}));
    const old=this.originalEdge;
    if(old) { const previous=graph.find(t=>t.code===old.from); if(previous) previous.transitions[old.outcome]=(previous.transitions[old.outcome]||[]).filter(d=>d!==old.to); }
    if(wouldCreateCycle(graph,from,to)) { this.edgeError='Questo collegamento crea un ciclo. Scegli una destinazione successiva.'; return; }
    if(old) this.removeEdgeReference(old);
    let choice=source.choices.find(c=>c.name===outcome);
    if(!choice) { choice={name:outcome,destinations:[]}; source.choices.push(choice); }
    if(!choice.destinations.includes(to)) choice.destinations.push(to);
    this.edgeDraft=null; this.originalEdge=null; this.edgeError='';
  }
  removeEdgeReference(edge:GraphEdge) {
    const choice=this.tasks.find(t=>t.code===edge.from)?.choices.find(c=>c.name===edge.outcome);
    if(choice) choice.destinations=choice.destinations.filter(d=>d!==edge.to);
  }
  deleteEdge() {
    if(this.originalEdge && !this.busy()) this.removeEdgeReference(this.originalEdge);
    this.edgeDraft=null; this.originalEdge=null;
  }

  move(index: number, direction: number) { const next=index+direction; if (next<0 || next>=this.tasks.length) return; [this.tasks[index],this.tasks[next]]=[this.tasks[next],this.tasks[index]]; }
  removeTask(index: number) {
    const code = this.tasks[index].code;
    if (code && this.tasks.some((t,i) => i!==index && t.choices.some(c=>c.destinations.includes(code)))) { this.formError.set('Rimuovi prima le transizioni verso questa attività.'); return; }
    if(this.graphTask===this.tasks[index])this.graphTask=null;
    this.tasks.splice(index,1); this.edgeDraft=null; this.originalEdge=null;
  }
  renameTask(task: TaskDraft, next: string) {
    const old=task.code; task.code=next.trim(); this.edgeDraft=null; this.originalEdge=null;
    if (old) for (const t of this.tasks) { for(const c of t.choices) c.destinations=c.destinations.map(code=>code===old?task.code:code); }
  }
  roleLabel(role: string) { return role === 'MANAGER' ? 'Supervisore' : role; }
  taskKinds(task:TaskDraft) {
    const graph=this.graphTasks(), node=graph.find(t=>t.code===task.code);
    return node ? graphNodeKinds({code:node.code,initial:this.initial(task),outcomes:graphOutcomes(node)},graphEdges(graph)) : [];
  }
  taskSummary(task:TaskDraft) { return graphNodeSummary(this.graphTasks().find(t=>t.code===task.code),this.taskKinds(task)); }
  taskBackground(task:TaskDraft) { return graphKindBackground(this.taskKinds(task)); }
  initial(task: TaskDraft) { return task.is_initial === true; }
  toggle(values: string[], value: string, enabled: boolean) { if (enabled && !values.includes(value)) values.push(value); else if (!enabled) { const i=values.indexOf(value); if(i>=0) values.splice(i,1); } }
  async save() {
    if(this.busy()) return;
    if(this.edgeDraft) { this.formError.set('Applica o annulla prima il collegamento in modifica.'); return; }
    if(!await this.persistDraft()) {this.formError.set('Prima di pubblicare occorre salvare la bozza sul server.');return;}
    this.busy.set(true); this.formError.set('');
    try {
      const body: Record<string, unknown> = {...this.original,...this.draft,active:this.active};
      if (this.entity==='clients') body['repertoire']=[...this.repertoire];
      if (this.entity==='practice_types') {
        body['_expected_model']=this.original;
        body['requires_validation']=this.requiresValidation;
        body['tasks']=this.tasks.map(({choices,...task})=>({...task,depends_on:[],outcomes:choices.map(c=>c.name.trim()).filter(name=>name!=='*'),transitions:Object.fromEntries(choices.map(c=>[c.name.trim(),c.destinations]))}));
      }
      await this.api.post(this.entity==='practices'?'/admin/practices':`/admin/config/${segment(this.entity)}`,body,true);
      if(this.entity==='practice_types' && this.draftRevision) {
        try {await this.api.post('/admin/model-drafts/delete',{id:this.draftId,revision:this.draftRevision},true);this.savedDrafts.update(rows=>rows.filter(r=>r.id!==this.draftId));}
        catch {this.error.set('Modello pubblicato. La bozza resta disponibile: eliminala dall’elenco quando non serve più.');}
      }
      this.editorDialog()?.nativeElement.close(); this.editor.set(false); await this.load();
    } catch(e) { this.formError.set(message(e)); } finally { this.busy.set(false); }
  }
  async remove(row: Row) {
    if(this.busy() || !confirm(`Eliminare ${this.label(row)}?`)) return;
    this.busy.set(true); this.error.set('');
    try { await this.api.post(`/admin/config/${segment(this.entity)}/delete`,{id:row.id}); await this.load(); }
    catch(e) { this.error.set(message(e)); } finally { this.busy.set(false); }
  }
}
