import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Api, message } from '../core/api';
import { PracticeSummary } from '../core/models';
@Component({ selector: 'wms-validation', imports: [DatePipe, RouterLink], template: `
  <p class="eyebrow">Scrivania Validatore</p><h1>Pratiche da validare</h1>
  @if (loading()) { <p role="status">Caricamento pratiche…</p> }
  @if (error()) { <p class="message error" role="alert">{{ error() }}</p><button (click)="load()">Riprova</button> }
  @if (!loading() && !error()) {
    <section class="panel table-wrap"><table><thead><tr><th>Pratica / Cliente</th><th>Periodo</th><th>Scadenza</th><th>Attività</th><th>Situazione</th><th>Attesa</th></tr></thead><tbody>
      @for (p of queue(); track p.id) { <tr><td><a [routerLink]="['/practices', p.id]">{{ p.practice_type_code }} · {{ p.id }}</a><small>{{ p.client_id }}</small></td><td>{{ p.period_start | date:'dd/MM/yyyy' }} – {{ p.period_end | date:'dd/MM/yyyy' }}</td><td>{{ p.due_date | date:'dd/MM/yyyy' }}<small>{{ p.urgency.label }} · {{ p.urgency.detail }}</small></td><td>{{ p.progress.completed }}/{{ p.progress.total }}</td><td>{{ p.situation.label }}</td><td>{{ p.waiting_hours ?? '—' }} h<small>{{ p.waiting_since | date:'dd/MM/yyyy HH:mm' }}</small></td></tr> }
      @empty { <tr><td colspan="6">Nessuna pratica in attesa di validazione.</td></tr> }
    </tbody></table></section>
    <section class="panel"><h2>Le mie validazioni nelle ultime 8 ore</h2>
      @for (p of history(); track p.id) { <article class="panel"><h3><a [routerLink]="['/practices', p.id]">{{ p.practice_type_code }} · {{ p.client_id }}</a></h3><p>{{ p.validation_outcome }} · {{ p.validated_at | date:'dd/MM/yyyy HH:mm' }}</p><p class="preline">{{ p.validation_note }}</p></article> }
      @empty { <p>Nessuna validazione recente.</p> }
    </section>
  }
` })
export class Validation implements OnInit {
  private api = inject(Api); queue = signal<PracticeSummary[]>([]); history = signal<PracticeSummary[]>([]); loading = signal(true); error = signal('');
  ngOnInit() { void this.load(); }
  async load() { this.loading.set(true); this.error.set(''); try { const [queue, history] = await Promise.all([this.api.get<PracticeSummary[]>('/validation-queue'), this.api.get<PracticeSummary[]>('/validation-history')]); this.queue.set(queue); this.history.set(history); } catch (e) { this.error.set(message(e)); } finally { this.loading.set(false); } }
}
