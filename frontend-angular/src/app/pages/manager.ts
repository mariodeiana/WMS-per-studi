import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Api, message } from '../core/api';
import { PracticeSummary } from '../core/models';
@Component({selector: 'wms-manager', imports: [CommonModule, RouterLink], templateUrl: './manager.html'})
export class Manager implements OnInit {
  private api = inject(Api);
  readonly practices = signal<PracticeSummary[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  async ngOnInit() {
    try { this.practices.set(await this.api.get<PracticeSummary[]>('/manager/practices')); }
    catch (e) { this.error.set(message(e)); }
    finally { this.loading.set(false); }
  }
  overallProgress(): number {
    const rows = this.practices();
    const total = rows.reduce((sum, p) => sum + Number(p.progress.total || 0), 0);
    const completed = rows.reduce((sum, p) => sum + Number(p.progress.completed || 0), 0);
    return total ? Math.round(completed * 100 / total) : 0;
  }

  criticalCount(): number {
    return this.practices().filter(
      p => p.status === 'NON_VALIDATA' || p.urgency.level === 'OVERDUE'
    ).length;
  }

  warningsCount(): number {
    return this.practices().filter(
      p => p.situation.code === 'WARNINGS'
    ).length;
  }

  dueSoonCount(): number {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const limit = new Date(today);
    limit.setDate(limit.getDate() + 7);

    return this.practices().filter(p => {
      const due = new Date(`${p.due_date}T00:00:00`);
      return due >= today && due <= limit;
    }).length;
  }

  gaugeStyle(value: number, maximum = 100): string {
    const safe = Math.max(0, Math.min(maximum, Number(value) || 0));
    return `${maximum ? safe / maximum * 360 : 0}deg`;
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      DA_FARE: 'Da fare',
      IN_LAVORAZIONE: 'In corso',
      COMPLETATA: 'Completata',
      DA_VALIDARE: 'Da validare',
      VALIDATA: 'Validata',
      NON_VALIDATA: 'Non validata'
    };
    return labels[status] || status;
  }
}
