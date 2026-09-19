import { Component, input } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Evidence, Result, Task } from '../core/models';
import { EvidenceList } from './evidence';
@Component({ selector: 'wms-results', imports: [DatePipe, EvidenceList], template: `
  @for (r of items(); track r.id) {
    <article class="result-entry" [class.has-warning]="r.outcome.includes('RILIEV') || r.outcome === 'NON_VALIDATA'" [class.result-history]="historical(r)">
      <div><h3 class="result-title">{{ title(r) }}</h3><div class="result-badges"><span class="status">{{ r.outcome.replaceAll('_',' ') }}</span>@if(historical(r)) { <span class="status">Storico</span> }</div><p class="preline result-note">{{ r.note || 'Nessuna nota' }}</p></div>
      <div class="result-author"><strong>{{ r.actor }}</strong><small>{{ r.timestamp | date:'dd/MM/yyyy HH:mm' }}</small></div>
      <wms-evidence [items]="documents(r)" />
    </article>
  } @empty { <p class="muted">Nessun risultato registrato.</p> }
` })
export class Results {
  items = input<Result[]>([]); evidence = input<Evidence[]>([]); tasks = input<Task[]>([]);
  title(r: Result) { const task=this.tasks().find(t=>t.code===r.related_task_code); return task ? task.code+' · '+task.title : r.related_task_title || r.related_task_code || ({VALIDATION:'Validazione',CLOSURE:'Chiusura'} as Record<string,string>)[r.action] || r.action; }
  documents(r: Result) { return r.evidence || this.evidence().filter(e => r.evidence_ids.includes(e.id)); }
  historical(r: Result) { const task = this.tasks().find(t => t.code === r.related_task_code); return task && task.result_id !== r.id; }
}
