import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, message } from '../core/api';
import { QueueTask } from '../core/models';
@Component({ selector: 'wms-work', imports: [DatePipe, FormsModule, RouterLink], templateUrl: './work.html' })
export class Work implements OnInit {
  private api = inject(Api); tasks = signal<QueueTask[]>([]); loading = signal(true); error = signal('');
  section = 'ACTIVE'; search = ''; filter = 'all';
  sections = [{code:'ACTIVE', title:'Da lavorare'}, {code:'IN_USE', title:'In carico ai colleghi'}, {code:'RECENT_COMPLETED', title:'Completate · ultime 8 ore'}];
  visible() { return this.tasks().filter(t=>t.queue_section==='RECENT_COMPLETED' || (t.active !== false && t.status !== 'COMPLETATO')); }
  count(section: string) { return this.visible().filter(t => t.queue_section === section).length; }
  days(t: QueueTask) {
    if (t.urgency_sort !== undefined) return t.urgency_sort;
    const now = new Date(); const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    return Math.round((Date.parse(t.due_date.slice(0,10)+'T00:00:00Z')-today)/86400000);
  }
  late(t: QueueTask) { return t.active && t.queue_section === 'ACTIVE' && this.days(t) < 0; }
  total(kind: string) { return this.visible().filter(t=>t.queue_section==='ACTIVE' && (kind==='late' ? this.late(t) : kind==='working' ? t.active && t.status==='IN_LAVORAZIONE' : !!t.reopen_reason)).length; }
  label(t: QueueTask) { return t.locked_by_other ? 'Occupata' : t.queue_section==='RECENT_COMPLETED' ? 'Completata' : !t.active ? 'In attesa' : t.reopen_reason ? 'Riaperta' : t.status==='IN_LAVORAZIONE' ? 'In corso' : 'Da fare'; }
  urgency(t: QueueTask) { const d=this.days(t); return !Number.isFinite(d) ? '' : d<0 ? 'Scaduta da '+Math.abs(d)+' gg' : d===0 ? 'Oggi' : d===1 ? 'Domani' : 'Tra '+d+' gg'; }
  rows(section: string) {
    const q=this.search.trim().toLocaleLowerCase('it');
    return this.visible().filter(t=>t.queue_section===section && (!q || [t.claimed_by_name,t.claimed_by,t.title,t.code,t.client_id,t.client_name,t.practice_id,t.practice_type_code,t.work_note,t.reopen_reason,t.result_note,t.outcome].join(' ').toLocaleLowerCase('it').includes(q)) && (section!=='ACTIVE' || this.filter==='all' || (this.filter==='late' && this.late(t)) || (this.filter==='working' && t.active && t.status==='IN_LAVORAZIONE') || (this.filter==='reopened' && !!t.reopen_reason)))
      .sort((a,b)=>section==='RECENT_COMPLETED' ? (b.completed_at||'').localeCompare(a.completed_at||'') : Number(b.active)-Number(a.active) || a.due_date.localeCompare(b.due_date) || a.practice_id.localeCompare(b.practice_id) || a.code.localeCompare(b.code));
  }
  reset() { this.search=''; this.filter='all'; }
  tabKey(event: KeyboardEvent) {
    const keys=this.sections.map(s=>s.code); let i=keys.indexOf(this.section);
    if(event.key==='ArrowRight') i=(i+1)%keys.length; else if(event.key==='ArrowLeft') i=(i+keys.length-1)%keys.length; else if(event.key==='Home') i=0; else if(event.key==='End') i=keys.length-1; else return;
    event.preventDefault(); this.section=keys[i]; (event.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>('[role=tab]')[i]?.focus();
  }
  ngOnInit() { void this.load(); }
  async load() { this.loading.set(true); this.error.set(''); try { this.tasks.set(await this.api.get<QueueTask[]>('/work-queue')); } catch (e) { this.error.set(message(e)); } finally { this.loading.set(false); } }
}
