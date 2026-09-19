import { Component, DestroyRef, OnInit, inject, signal, viewChild } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Api, message, segment } from '../core/api';
import { TaskDetail } from '../core/models';
import { Attachments } from '../shared/attachments';
import { EvidenceList } from '../shared/evidence';
import { Results } from '../shared/results';
@Component({ selector: 'wms-task', imports: [DatePipe, FormsModule, RouterLink, Attachments, EvidenceList, Results], templateUrl: './task.html' })
export class TaskPage implements OnInit {
  private api = inject(Api); private route = inject(ActivatedRoute); private router = inject(Router); private destroy = inject(DestroyRef);
  data = signal<TaskDetail | null>(null); loading = signal(true); busy = signal(false); error = signal(''); outcome = ''; note = ''; private version = 0;
  attachments = viewChild(Attachments);
  tab = 'results';
  tabs = [{id:'results',label:'Risultati attività'},{id:'journal',label:'Diario'},{id:'previous',label:'Attività precedenti'},{id:'documents',label:'Documenti'}];
  statusLabel() { const t=this.data()?.task; return t?.status==='COMPLETATO' ? 'Completata' : !t?.active ? 'In attesa' : t?.status==='IN_LAVORAZIONE' ? 'In corso' : 'Da fare'; }
  documents() { const d=this.data(); return (d?.evidence || []).filter(e=>e.related_task_code===d?.task.code); }
  tabCount(id: string) { const d=this.data(); return id==='results' ? d?.task_results?.length || 0 : id==='journal' ? d?.task_journal.length || 0 : id==='previous' ? d?.previous_results?.length || 0 : this.documents().length; }
  tabKey(event: KeyboardEvent) { let i=this.tabs.findIndex(t=>t.id===this.tab); if(event.key==='ArrowRight') i=(i+1)%4; else if(event.key==='ArrowLeft') i=(i+3)%4; else if(event.key==='Home') i=0; else if(event.key==='End') i=3; else return; event.preventDefault(); this.tab=this.tabs[i].id; (event.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>('[role=tab]')[i]?.focus(); }

  ngOnInit() { this.route.paramMap.pipe(takeUntilDestroyed(this.destroy)).subscribe(params => { void this.load(params.get('id') || '', params.get('code') || ''); }); }
  outcomes() { const configured = this.data()?.task.outcomes; return configured?.length ? configured : ['POSITIVO', 'CON_RILIEVI']; }
  async load(id: string, code: string) {
    const version = ++this.version; this.loading.set(true); this.data.set(null); this.error.set(''); this.outcome = ''; this.note = '';
    try { const d = await this.api.get<TaskDetail>(`/tasks/${segment(id)}/${segment(code)}?context=1`); if (version === this.version) this.data.set(d); }
    catch (e) { if (version === this.version) this.error.set(message(e)); }
    finally { if (version === this.version) this.loading.set(false); }
  }
  async save(complete: boolean) {
    const d = this.data(); if (!d || this.busy() || (complete && !this.outcome)) return;
    this.busy.set(true); this.error.set('');
    try {
      const attachments = await this.attachments()?.payload() || [];
      await this.api.post(`/practices/${segment(d.practice.id)}/tasks/${segment(d.task.code)}/${complete ? 'complete' : 'progress'}`, { outcome: this.outcome, note: this.note, attachments });
      this.attachments()?.clear(); await this.router.navigateByUrl('/work');
    } catch (e) { this.error.set(message(e)); }
    finally { this.busy.set(false); }
  }
}
