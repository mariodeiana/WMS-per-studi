import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

interface Session {
  user: {
    username: string;
    display_name: string;
  };
  active: {
    id: string;
    role: string;
  };
  memberships: Array<{
    id: string;
    label: string;
    role: string;
  }>;
}

interface Practice {
  id: string;
  client_id: string;
  client_name: string;
  practice_type_code: string;
  period_start: string;
  period_end: string;
  due_date: string;
  status: string;
  progress: {
    completed: number;
    total: number;
    percent: number;
  };
  situation: {
    code: string;
    label: string;
  };
  urgency: {
    level: string;
    label: string;
    detail: string;
  };
}

@Component({
  selector: 'app-root',
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  readonly session = signal<Session | null>(null);
  readonly practices = signal<Practice[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly authenticated = signal(false);
  username = '';
  password = '';
  loginBusy = false;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.http.get<Session>('/api/session').subscribe({
      next: session => {
        this.authenticated.set(true);
        this.session.set(session);

        if (session.active.role !== 'MANAGER') {
          this.error.set(`Ruolo attivo: ${session.active.role}. Selezionare il ruolo Manager.`);
          this.loading.set(false);
          return;
        }

        this.http.get<Practice[]>('/api/manager/practices').subscribe({
          next: practices => {
            this.practices.set(practices);
            this.loading.set(false);
          },
          error: err => this.fail(err)
        });
      },
      error: err => this.fail(err)
    });
  }

  private fail(err: any): void {
    if (err.status === 401) {
      this.authenticated.set(false);
      this.error.set('');
    } else {
      this.error.set(err.error?.error || 'Impossibile caricare la Scrivania Manager.');
    }
    this.loading.set(false);
  }

  login(): void {
    if (!this.username.trim() || !this.password) return;

    this.loginBusy = true;
    this.error.set('');

    this.http.post<Session>('/api/login', {
      username: this.username.trim(),
      password: this.password
    }).subscribe({
      next: session => {
        this.password = '';
        this.loginBusy = false;
        this.authenticated.set(true);
        this.session.set(session);

        if (session.active.role !== 'MANAGER') {
          this.error.set(`Ruolo attivo: ${session.active.role}. Selezionare il ruolo Manager.`);
          this.loading.set(false);
          return;
        }

        this.loading.set(true);
        this.http.get<Practice[]>('/api/manager/practices').subscribe({
          next: practices => {
            this.practices.set(practices);
            this.loading.set(false);
          },
          error: err => this.fail(err)
        });
      },
      error: err => {
        this.loginBusy = false;
        this.error.set(err.error?.error || 'Accesso non riuscito.');
      }
    });
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
