import { Component, input } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Evidence } from '../core/models';
@Component({ selector: 'wms-evidence', imports: [DatePipe], template: `
  @for (e of items(); track e.id) {
    <div class="panel"><strong>{{ e.filename }}</strong><p>{{ e.description }}</p>
      <small>{{ e.document_type }} · {{ e.actor }} · {{ e.created_at | date:'dd/MM/yyyy HH:mm' }}</small>
      <div class="actions"><a [href]="url(e.preview_url)" target="_blank" rel="noopener">Apri anteprima</a>
        <a [href]="url(e.download_url)">Scarica</a></div>
    </div>
  } @empty { <p class="muted">Nessuna evidenza.</p> }
` })
export class EvidenceList {
  items = input<Evidence[]>([]);
  url(value: string) { return value.startsWith('/api/evidence/') ? value : ''; }
}
