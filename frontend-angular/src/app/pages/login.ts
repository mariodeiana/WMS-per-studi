import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Auth } from '../core/auth';
import { message } from '../core/api';
@Component({ selector: 'wms-login', imports: [FormsModule], template: `
  <section class="login-shell"><div class="login-card"><p class="eyebrow">WMS</p><h1>Accesso</h1>
    <p>Accedi con il tuo utente WMS.</p>
    <form class="login-form" (ngSubmit)="login()">
      <label>Utente<input name="username" [(ngModel)]="username" autocomplete="username" required></label>
      <label>Password<input name="password" type="password" [(ngModel)]="password" autocomplete="current-password" required></label>
      <button [disabled]="busy()">{{ busy() ? 'Accesso…' : 'Accedi' }}</button>
    </form>
    @if (error() || auth.error()) { <p class="message error" role="alert">{{ error() || auth.error() }}</p> }
  </div></section>` })
export class Login {
  auth = inject(Auth); username = ''; password = ''; busy = signal(false); error = signal('');
  async login() {
    if (this.busy() || !this.username.trim() || !this.password) return;
    this.busy.set(true); this.error.set('');
    try { await this.auth.login(this.username.trim(), this.password); this.password = ''; }
    catch (e) { this.error.set(message(e)); }
    finally { this.busy.set(false); }
  }
}
