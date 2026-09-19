import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, message, segment } from '../core/api';

interface Row { id: string; active?: boolean; [key: string]: unknown; }
interface TaskSpec {
  code: string; title: string; instructions: string; assigned_group: string; days_before_due: number; required: boolean;
  depends_on: string[]; outcomes: string[]; transitions: Record<string, string[]>;
}
interface TaskDraft extends Omit<TaskSpec, 'outcomes' | 'transitions'> { choices: {name: string; destinations: string[]}[]; }
interface Field { key: string; label: string; type?: string; }
interface Meta { key: string; title: string; fields: Field[]; }
const fields = (...pairs: string[][]): Field[] => pairs.map(([key,label,type]) => ({key,label,type}));
@Component({ selector: 'wms-admin', imports: [CommonModule, FormsModule, RouterLink], templateUrl: './admin.html' })
export class Admin implements OnInit {
  private api = inject(Api);
  config = signal<Record<string, Row[]>>({}); roles = signal<string[]>([]); practices = signal<Row[]>([]);
  loading = signal(true); busy = signal(false); error = signal(''); editor = signal(false); formError = signal('');
  entity = 'groups'; original: Row | null = null; draft: Record<string, string> = {}; active = true; requiresValidation = true; tasks: TaskDraft[] = [];
  meta: Meta[] = [
    {key:'users',title:'Utenti',fields:fields(['id','ID'],['username','Login'],['display_name','Nome visualizzato'],['default_membership_id','Appartenenza predefinita'])},
    {key:'groups',title:'Gruppi',fields:fields(['id','Codice'],['name','Nome'],['role','Ruolo'])},
    {key:'memberships',title:'Appartenenze',fields:fields(['id','ID'],['user_id','Utente'],['group_id','Gruppo'],['label','Etichetta'])},
    {key:'assignment_policies',title:'Politiche di assegnazione',fields:fields(['id','Codice'],['name','Nome'],['strategy','Strategia'],['description','Descrizione','textarea'])},
    {key:'practice_types',title:'Tipi di pratica',fields:fields(['id','ID'],['code','Codice'],['name','Nome'],['description','Descrizione','textarea'])},
    {key:'clients',title:'Clienti',fields:fields(['id','Codice cliente'],['name','Ragione sociale'],['tax_code','Codice fiscale'],['vat_number','Partita IVA'],['email','Email','email'])},
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
    return related ? this.label(related) : String(row[key] ?? '');
  }
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    try {
      const [config, practices] = await Promise.all([this.api.get<Record<string, unknown>>('/admin/config'), this.api.get<Row[]>('/admin/practices')]);
      this.roles.set(config['roles'] as string[]); this.config.set(Object.fromEntries(this.meta.filter(m => m.key !== 'practices').map(m => [m.key, config[m.key] as Row[]]))); this.practices.set(practices);
    } catch (e) { this.error.set(message(e)); } finally { this.loading.set(false); }
  }
  open(row: Row | null = null) {
    this.original = row; this.draft = {}; this.formError.set('');
    for (const field of this.current().fields) this.draft[field.key] = String(row?.[field.key] ?? '');
    if (this.entity === 'groups' && !row) this.draft['role'] = 'OPERATORE';
    this.active = row?.active !== false; this.requiresValidation = row?.['requires_validation'] !== false;
    this.tasks = structuredClone((row?.['tasks'] || []) as TaskSpec[]).map(t => ({...t, depends_on:t.depends_on || [], choices:(t.outcomes || []).map(name => ({name,destinations:[...(t.transitions?.[name] || [])]}))}));
    if (this.entity === 'practices') this.draft['model_id'] = '';
    this.editor.set(true);
  }
  select(entity: string) { this.entity = entity; this.editor.set(false); this.error.set(''); }
  addTask() { this.tasks.push({code:'',title:'',instructions:'',assigned_group:'',days_before_due:0,required:true,depends_on:[],choices:[]}); }
  move(index: number, direction: number) { const next=index+direction; if (next<0 || next>=this.tasks.length) return; [this.tasks[index],this.tasks[next]]=[this.tasks[next],this.tasks[index]]; }
  removeTask(index: number) {
    const code = this.tasks[index].code;
    if (code && this.tasks.some((t,i) => i!==index && (t.depends_on.includes(code) || t.choices.some(c=>c.destinations.includes(code))))) { this.formError.set('Rimuovi prima le dipendenze e le transizioni verso questa attività.'); return; }
    this.tasks.splice(index,1);
  }
  renameTask(task: TaskDraft, next: string) {
    const old=task.code; task.code=next.trim();
    if (old) for (const t of this.tasks) { t.depends_on=t.depends_on.map(code=>code===old?task.code:code); for(const c of t.choices) c.destinations=c.destinations.map(code=>code===old?task.code:code); }
  }
  toggle(values: string[], value: string, enabled: boolean) { if (enabled && !values.includes(value)) values.push(value); else if (!enabled) { const i=values.indexOf(value); if(i>=0) values.splice(i,1); } }
  async save() {
    if(this.busy()) return; this.busy.set(true); this.formError.set('');
    try {
      const body: Record<string, unknown> = {...this.original,...this.draft,active:this.active};
      if (this.entity==='practice_types') {
        body['requires_validation']=this.requiresValidation;
        body['tasks']=this.tasks.map(({choices,...task})=>({...task,outcomes:choices.map(c=>c.name.trim()),transitions:Object.fromEntries(choices.map(c=>[c.name.trim(),c.destinations]))}));
      }
      await this.api.post(this.entity==='practices'?'/admin/practices':`/admin/config/${segment(this.entity)}`,body);
      this.editor.set(false); await this.load();
    } catch(e) { this.formError.set(message(e)); } finally { this.busy.set(false); }
  }
  async remove(row: Row) {
    if(this.busy() || !confirm(`Eliminare ${this.label(row)}?`)) return;
    this.busy.set(true); this.error.set('');
    try { await this.api.post(`/admin/config/${segment(this.entity)}/delete`,{id:row.id}); await this.load(); }
    catch(e) { this.error.set(message(e)); } finally { this.busy.set(false); }
  }
}
