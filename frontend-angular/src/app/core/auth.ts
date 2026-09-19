import { Injectable, inject, signal } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { Api, message } from './api';
import { Session } from './models';

export function home(role?: string): string {
  return ({ MANAGER: '/manager', OPERATORE: '/work', VALIDATORE: '/validation', AMMINISTRATORE: '/admin' } as Record<string, string>)[role || ''] || '/context';
}
@Injectable({ providedIn: 'root' })
export class Auth {
  private api = inject(Api);
  private router = inject(Router);
  readonly session = signal<Session | null>(null);
  readonly error = signal('');
  async restore(): Promise<Session | null> {
    if (this.session()) return this.session();
    try { const session = await this.api.get<Session>('/session'); this.session.set(session); this.error.set(''); return session; }
    catch (e) { if (!(e instanceof HttpErrorResponse) || e.status !== 401) this.error.set(message(e)); return null; }
  }
  async login(username: string, password: string) {
    const s = await this.api.post<Session>('/login', { username, password });
    this.session.set(s); this.error.set(''); await this.router.navigateByUrl(home(s.active.role));
  }
  async switchRole(id: string) {
    const s = await this.api.post<Session>('/session/role', { membership_id: id });
    this.session.set(s); await this.router.navigateByUrl(home(s.active.role));
  }
  async logout() { await this.api.post('/logout'); this.expire(); }
  expire() { this.session.set(null); void this.router.navigateByUrl('/login'); }
}
export const authGuard: CanActivateFn = async route => {
  const auth = inject(Auth), router = inject(Router);
  const s = await auth.restore();
  if (!s) return router.parseUrl('/login');
  const roles = route.data['roles'] as string[] | undefined;
  return !roles || roles.includes(s.active.role) ? true : router.parseUrl(home(s.active.role));
};
export const sessionInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(Auth);
  return next(request).pipe(catchError(error => {
    if (error.status === 401 && !['/api/login', '/api/session'].includes(request.url)) auth.expire();
    return throwError(() => error);
  }));

};
