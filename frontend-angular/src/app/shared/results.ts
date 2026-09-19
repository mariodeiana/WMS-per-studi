import { Component, input } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Evidence, Result, Task } from '../core/models';
import { EvidenceList } from './evidence';
@Component({ selector: 'wms-results', imports: [DatePipe, EvidenceList], template: `
  @for (r of items(); track r.id) {
    <article class="panel"><h3>{{ r.related_task_code || r.action }} · {{ r.outcome }}</h3>
      @if (historical(r)) { <span class="status">Storico</span> }
      <p class="preline">{{ r.note || 'Nessuna nota' }}</p>
      <small>{{ r.actor }} · {{ r.timestamp | date:'dd/MM/yyyy HH:mm' }}</small>
      <wms-evidence [items]="documents(r)" />
    </article>
  } @empty { <p class="muted">Nessun risultato registrato.</p> }
` })
export class Results {
  items = input<Result[]>([]); evidence = input<Evidence[]>([]); tasks = input<Task[]>([]);
  documents(r: Result) { return r.evidence || this.evidence().filter(e => r.evidence_ids.includes(e.id)); }
  historical(r: Result) { const task = this.tasks().find(t => t.code === r.related_task_code); return task && task.result_id !== r.id; }
}
