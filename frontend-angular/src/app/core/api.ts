import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpContext, HttpContextToken } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export function message(error: unknown): string {
  if (error instanceof Error && /dynamically imported module|Loading chunk/i.test(error.message)) return 'La versione dell’interfaccia è cambiata. Ricarica la pagina.';
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) return 'Connessione non disponibile. Riprova tra poco.';
    return error.error?.error || `Operazione non riuscita (${error.status}).`;
  }
  return error instanceof Error ? error.message : 'Operazione non riuscita.';
}
export const segment = (value: string) => encodeURIComponent(value);

export const KEEP_EDITOR = new HttpContextToken<boolean>(()=>false);

@Injectable({ providedIn: 'root' })
export class Api {
  private http = inject(HttpClient);
  get<T>(path: string): Promise<T> { return firstValueFrom(this.http.get<T>('/api' + path)); }
  post<T>(path: string, body: unknown = {}, keepEditor=false): Promise<T> { return firstValueFrom(this.http.post<T>('/api' + path, body, {context:new HttpContext().set(KEEP_EDITOR,keepEditor)})); }
}
