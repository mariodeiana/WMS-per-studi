import { Component, DestroyRef, OnInit, inject, signal, viewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Api, message, segment } from '../core/api';
import { Auth } from '../core/auth';
import { Practice as PracticeData, Task } from '../core/models';
import { Attachments } from '../shared/attachments';
import { EvidenceList } from '../shared/evidence';
import { Results } from '../shared/results';
@Component({ selector: 'wms-practice', imports: [CommonModule, FormsModule, RouterLink, Attachments, EvidenceList, Results], templateUrl: './practice.html' })
export class Practice implements OnInit {
  private api = inject(Api); private route = inject(ActivatedRoute); private destroy = inject(DestroyRef);
  auth = inject(Auth); data = signal<PracticeData | null>(null); loading = signal(true); busy = signal(false); error = signal('');
  groups = signal<{id: string; name: string}[]>([]); taskCode = ''; reason: Record<string, string> = {}; group: Record<string, string> = {};
  selection: Record<string, boolean> = {}; instruction = ''; outcome = ''; note = ''; private version = 0;
  attachments = viewChild(Attachments);
  manager() { return this.auth.session()?.active.role === 'MANAGER'; }
  validator() { return this.auth.session()?.active.role === 'VALIDATORE'; }
  ngOnInit() { this.route.paramMap.pipe(takeUntilDestroyed(this.destroy)).subscribe(params => { this.taskCode = params.get('code') || ''; void this.load(params.get('id') || ''); }); }
  async load(id: string) {
    const version = ++this.version; this.loading.set(true); this.error.set(''); this.data.set(null); this.outcome = ''; this.note = ''; this.selection = {}; this.instruction = '';
    try {
      const [p, groups] = await Promise.all([this.api.get<PracticeData>('/practices/' + segment(id)), this.manager() ? this.api.get<{id:string; name:string}[]>('/manager/assignment-groups') : Promise.resolve([])]);
      if (version !== this.version) return;
      if (this.taskCode && !p.tasks.some(t => t.code === this.taskCode)) throw new Error('Attività inesistente.');
      this.data.set(p); this.groups.set(groups); this.setGroups(p);
    } catch (e) { if (version === this.version) this.error.set(message(e)); }
    finally { if (version === this.version) this.loading.set(false); }
  }
  setGroups(p: PracticeData) { this.group = Object.fromEntries(p.tasks.map(t => [t.code, t.assigned_group])); }
  visibleTasks() { return this.data()?.tasks.filter(t => !this.taskCode || t.code === this.taskCode) || []; }
  visibleResults() { return this.data()?.results.filter(r => !this.taskCode || r.related_task_code === this.taskCode) || []; }
  canReopen(t: Task) { return t.status === 'COMPLETATO' && !['VALIDATA', 'CHIUSA'].includes(this.data()?.status || ''); }
  canClose() { const p = this.data(); return p?.status === (p?.requires_validation ? 'VALIDATA' : 'COMPLETATA'); }
  selected() { return Object.keys(this.selection).filter(code => this.selection[code]); }
  canSubmit() { return !!this.outcome && (!this.validator() || this.outcome === 'VALIDATA' || !!this.note.trim()); }
  async action(action: string, body: unknown) {
    const p = this.data(); if (!p || this.busy()) return;
    this.busy.set(true); this.error.set('');
    try { const result = await this.api.post<PracticeData>(`/practices/${segment(p.id)}/${action}`, body); this.data.set(result); this.setGroups(result); this.reason = {}; this.selection = {}; this.instruction = ''; }
    catch (e) { this.error.set(message(e)); this.setGroups(p); }
    finally { this.busy.set(false); }
  }
  assign(t: Task) { return this.action(`tasks/${segment(t.code)}/assign`, { group_id: this.group[t.code] }); }
  reopen(t: Task) { return this.action(`tasks/${segment(t.code)}/reopen`, { reason: this.reason[t.code] }); }
  correct() { return this.action('corrective-action', { task_codes: this.selected(), instruction: this.instruction }); }
  async submitResult() {
    const p = this.data(); if (!p || this.busy() || !this.canSubmit()) return;
    this.busy.set(true); this.error.set('');
    try {
      const attachments = await this.attachments()?.payload() || [];
      this.data.set(await this.api.post<PracticeData>(`/practices/${segment(p.id)}/${this.validator() ? 'validate' : 'close'}`, { outcome: this.outcome, note: this.note, attachments }));
      this.outcome = ''; this.note = ''; this.attachments()?.clear();
    } catch (e) { this.error.set(message(e)); }
    finally { this.busy.set(false); }
  }
}
