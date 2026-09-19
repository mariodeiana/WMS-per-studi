import { Routes } from '@angular/router';
import { authGuard } from './core/auth';
export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./pages/login').then(m => m.Login) },
  { path: 'manager', canActivate: [authGuard], data: { roles: ['MANAGER'] }, loadComponent: () => import('./pages/manager').then(m => m.Manager) },
  { path: 'practices/:id/tasks/:code', canActivate: [authGuard], data: { roles: ['MANAGER', 'VALIDATORE', 'AMMINISTRATORE'] }, loadComponent: () => import('./pages/practice').then(m => m.Practice) },
  { path: 'practices/:id', canActivate: [authGuard], data: { roles: ['MANAGER', 'VALIDATORE', 'AMMINISTRATORE'] }, loadComponent: () => import('./pages/practice').then(m => m.Practice) },
  { path: 'work/:id/:code', canActivate: [authGuard], data: { roles: ['OPERATORE'] }, loadComponent: () => import('./pages/task').then(m => m.TaskPage) },
  { path: 'work', canActivate: [authGuard], data: { roles: ['OPERATORE'] }, loadComponent: () => import('./pages/work').then(m => m.Work) },
  { path: 'validation', canActivate: [authGuard], data: { roles: ['VALIDATORE'] }, loadComponent: () => import('./pages/validation').then(m => m.Validation) },
  { path: 'admin', canActivate: [authGuard], data: { roles: ['AMMINISTRATORE'] }, loadComponent: () => import('./pages/admin').then(m => m.Admin) },
  { path: 'context', canActivate: [authGuard], loadComponent: () => import('./pages/context').then(m => m.Context) },
  { path: '', pathMatch: 'full', redirectTo: 'manager' },
  { path: '**', redirectTo: 'context' }
];
