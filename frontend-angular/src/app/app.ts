import { Component, inject, signal } from '@angular/core';
import { NavigationError, Router, RouterLink, RouterOutlet } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Auth, home } from './core/auth';
import { Api, message } from './core/api';
@Component({ selector: 'app-root', imports: [RouterOutlet, RouterLink, FormsModule], templateUrl: './app.html' })
export class App {
  environment = signal(''); revision = signal('');
  private api = inject(Api);
  auth = inject(Auth); home = home; busy = signal(false); error = signal('');
  constructor() { void this.api.get<{environment:string;version?:string;revision?:number}>('/runtime').then(r=>{this.environment.set(r.environment);this.revision.set(r.version && typeof r.revision==='number' ? 'Versione '+r.version+' · Revisione '+r.revision : 'Versione non rilevata');}).catch(()=>{}); inject(Router).events.pipe(takeUntilDestroyed()).subscribe(event => { if (event instanceof NavigationError) this.error.set(message(event.error)); }); }
  reload() { location.reload(); }
  async switchRole(id: string) { await this.run(() => this.auth.switchRole(id)); }
  async logout() { await this.run(() => this.auth.logout()); }
  private async run(action: () => Promise<unknown>) {
    if (this.busy()) return;
    this.busy.set(true); this.error.set('');
    try { await action(); } catch (e) { this.error.set(message(e)); }
    finally { this.busy.set(false); }
  }
}
