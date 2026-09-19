import { Component, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Attachment } from '../core/models';
interface Draft { file: File; description: string; document_type: string; }
@Component({ selector: 'wms-attachments', imports: [FormsModule], template: `
  <fieldset class="attachments-editor" [disabled]="disabled()"><legend>Evidenze</legend>
    <div class="attachment-toolbar"><label class="attachment-add">+ Aggiungi documenti<input aria-label="Aggiungi documenti" type="file" multiple (change)="add($event)"></label><small>Massimo 5 MB per documento.</small></div>
    @if (error()) { <p role="alert" class="message error">{{ error() }}</p> }
    @for (item of files(); track item; let i = $index) {
      <div class="attachment-draft"><strong>▤ {{ item.file.name }}</strong>
        <label>Descrizione<input [(ngModel)]="item.description" [ngModelOptions]="{standalone:true}" placeholder="Descrizione"></label>
        <label>Tipo documento<input [(ngModel)]="item.document_type" [ngModelOptions]="{standalone:true}"></label>
        <button type="button" class="secondary" (click)="remove(i)" [attr.aria-label]="'Rimuovi '+item.file.name">×</button>
      </div>
    }
  </fieldset>` })
export class Attachments {
  disabled = input(false); files = signal<Draft[]>([]); error = signal('');
  add(event: Event) {
    const picker = event.target as HTMLInputElement; this.error.set('');
    for (const file of Array.from(picker.files || [])) {
      if (file.size > 5 * 1024 * 1024) { this.error.set(`${file.name}: dimensione superiore a 5 MB`); continue; }
      this.files.update(files => [...files, { file, description: '', document_type: 'DOCUMENTO' }]);
    }
    picker.value = '';
  }
  remove(i: number) { this.files.update(files => files.filter((_, index) => index !== i)); }
  clear() { this.files.set([]); this.error.set(''); }
  async payload(): Promise<Attachment[]> {
    return Promise.all(this.files().map(async item => ({
      filename: item.file.name, content_type: item.file.type || 'application/octet-stream',
      description: item.description, document_type: item.document_type || 'DOCUMENTO',
      content_base64: await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(',', 2)[1] || '');
        reader.onerror = () => reject(new Error(`Impossibile leggere ${item.file.name}`));
        reader.readAsDataURL(item.file);
      })
    })));
  }
}
