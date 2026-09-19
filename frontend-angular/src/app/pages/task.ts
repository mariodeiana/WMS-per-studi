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
@Component({ selector: 'wms-task', imports: [DatePipe, FormsModule, RouterLink, Attachments, EvidenceList, Results], template: `
  <a routerLink="/work">← I miei compiti</a>
  @if (loading()) { <p role="status">Caricamento attività…</p> }
  @if (error()) { <p class="message error" role="alert">{{ error() }}</p> }
  @if (data(); as d) {
    <section class="panel"><p class="eyebrow">{{ d.practice.type }} · {{ d.practice.id }} · {{ d.task.code }}</p><h1>{{ d.task.title }}</h1>
      <p>Cliente {{ d.practice.client_id }} · {{ d.practice.period_start | date:'dd/MM/yyyy' }} – {{ d.practice.period_end | date:'dd/MM/yyyy' }}</p>
      <p>Scadenza {{ (d.task.due_date || d.practice.due_date) | date:'dd/MM/yyyy' }} · {{ d.task.status }}</p>
      <p>Dipendenze: {{ d.task.depends_on.join(', ') || 'Nessuna' }}</p>
      @if (d.task.reopen_reason) { <p class="notice preline">Riaperta dal Manager: {{ d.task.reopen_reason }}</p> }
      <h2>Istruzioni operative</h2><p class="preline">{{ d.task.instructions || 'Nessuna istruzione definita.' }}</p>
    </section>
    <section class="panel"><h2>Diario del task</h2>
      @for (entry of d.task_journal; track $index) { <article class="panel"><small>{{ entry.actor }} · {{ entry.at | date:'dd/MM/yyyy HH:mm' }} · {{ entry.type }}</small><p class="preline">{{ entry.note }}</p><wms-evidence [items]="entry.evidence" /></article> } @empty { <p>Nessuna annotazione.</p> }
      <wms-evidence [items]="d.task_progress_evidence" />
    </section>
    <section class="panel"><h2>Risultati del task</h2><wms-results [items]="d.task_results || []" [evidence]="d.evidence || []" [tasks]="[d.task]" /></section>
    <section class="panel"><h2>Materiale e risultati precedenti</h2><wms-results [items]="d.previous_results || []" [evidence]="d.evidence || []" /></section>
    @if (d.task.status !== 'COMPLETATO' && d.task.active) {
      <section class="panel"><h2>Lavorazione</h2><fieldset class="stack" [disabled]="busy()">
        <label>Esito<select [(ngModel)]="outcome"><option value="">Seleziona esito</option>@for (o of outcomes(); track o) { <option [value]="o">{{ o }}</option> }</select></label>
        <label>Nota<textarea [(ngModel)]="note"></textarea></label><wms-attachments [disabled]="busy()" />
        <div class="actions"><button type="button" class="secondary" (click)="save(false)">Salva e torna ai compiti</button><button type="button" (click)="save(true)" [disabled]="!outcome">Registra risultato e completa</button></div>
      </fieldset></section>
    } @else { <p class="notice">{{ d.task.status === 'COMPLETATO' ? 'Attività completata.' : 'Attività in attesa dell’attivazione del percorso.' }}</p> }
  }
` })
export class TaskPage implements OnInit {
  private api = inject(Api); private route = inject(ActivatedRoute); private router = inject(Router); private destroy = inject(DestroyRef);
  data = signal<TaskDetail | null>(null); loading = signal(true); busy = signal(false); error = signal(''); outcome = ''; note = ''; private version = 0;
  attachments = viewChild(Attachments);
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
