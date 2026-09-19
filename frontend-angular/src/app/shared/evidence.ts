import { Component, input } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Evidence } from '../core/models';
@Component({ selector: 'wms-evidence', imports: [DatePipe], template: `
  <div class="evidence-collection">@for (e of items(); track e.id) {
    <div class="evidence-item"><a class="evidence-name" [href]="url(e.preview_url)" target="_blank" rel="noopener">▤ {{ e.filename }}</a>
      @if(e.description) { <p>{{ e.description }}</p> }
      <small>{{ e.document_type }} · {{ e.actor }} · {{ e.created_at | date:'dd/MM/yyyy HH:mm' }}</small>
      <div class="evidence-actions"><a [href]="url(e.preview_url)" target="_blank" rel="noopener">Apri anteprima</a><a [href]="url(e.download_url)">Scarica</a></div>
    </div>
  } @empty { <p class="evidence-empty">Nessuna evidenza.</p> }</div>
` })
export class EvidenceList {
  items = input<Evidence[]>([]);
  url(value: string) { return value.startsWith('/api/evidence/') ? value : ''; }
}
