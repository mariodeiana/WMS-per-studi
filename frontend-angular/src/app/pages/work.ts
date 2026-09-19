import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Api, message } from '../core/api';
import { QueueTask } from '../core/models';
@Component({ selector: 'wms-work', imports: [DatePipe, RouterLink], template: `
  <p class="eyebrow">Scrivania Operatore</p><h1>I miei compiti</h1>
  @if (loading()) { <p role="status">Caricamento attività…</p> }
  @if (error()) { <p class="message error" role="alert">{{ error() }}</p><button (click)="load()">Riprova</button> }
  @if (!loading() && !error()) {
    @for (section of sections; track section.code) {
      <section class="panel"><h2>{{ section.title }}</h2>
        @for (t of rows(section.code); track t.practice_id + '/' + t.code) {
          <article class="panel"><p class="eyebrow">{{ t.practice_type_code }} · {{ t.client_id }} · {{ t.code }}</p>
            <h3><a [routerLink]="['/work', t.practice_id, t.code]">{{ t.title }}</a></h3>
            <p>{{ t.status }} · Scadenza {{ t.due_date | date:'dd/MM/yyyy' }}</p>
            @if (!t.active) { <p class="notice">In attesa dell’attivazione del percorso.</p> }
            @if (t.reopen_reason) { <p class="notice preline">Riaperta: {{ t.reopen_reason }}</p> }
            @if (t.work_note) { <p class="preline">{{ t.work_note }}</p> }
            @if (t.completed_at) { <p>{{ t.outcome }} · {{ t.completed_at | date:'dd/MM/yyyy HH:mm' }}</p><p>{{ t.result_note }}</p> }
          </article>
        } @empty { <p>Nessuna attività.</p> }
      </section>
    }
  }
` })
export class Work implements OnInit {
  private api = inject(Api); tasks = signal<QueueTask[]>([]); loading = signal(true); error = signal('');
  sections = [{code:'ACTIVE', title:'Da lavorare'}, {code:'RECENT_COMPLETED', title:'Completate nelle ultime 8 ore'}];
  rows(section: string) { return this.tasks().filter(t => t.queue_section === section).sort((a,b) => section === 'RECENT_COMPLETED' ? (b.completed_at || '').localeCompare(a.completed_at || '') : a.due_date.localeCompare(b.due_date)); }
  ngOnInit() { void this.load(); }
  async load() { this.loading.set(true); this.error.set(''); try { this.tasks.set(await this.api.get<QueueTask[]>('/work-queue')); } catch (e) { this.error.set(message(e)); } finally { this.loading.set(false); } }
}
