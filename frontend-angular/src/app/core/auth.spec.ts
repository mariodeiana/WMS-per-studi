import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { Api } from './api';
import { Auth, home, sessionInterceptor } from './auth';
import { Session } from './models';

const session: Session = { user:{username:'operator',display_name:'Operatore'}, active:{id:'op',group_id:'g',group:'Contabili',role:'OPERATORE',label:'Operatore'}, memberships:[] };
describe('Session lifecycle', () => {
  let auth: Auth, http: HttpTestingController, router: jasmine.SpyObj<Router>;
  beforeEach(() => {
    router = jasmine.createSpyObj('Router',['navigateByUrl']); router.navigateByUrl.and.resolveTo(true);
    TestBed.configureTestingModule({providers:[provideHttpClient(withInterceptors([sessionInterceptor])),provideHttpClientTesting(),{provide:Router,useValue:router}]});
    auth=TestBed.inject(Auth); http=TestBed.inject(HttpTestingController);
  });
  afterEach(()=>http.verify());
  it('restores the server session', async()=>{ const result=auth.restore(); http.expectOne('/api/session').flush(session); expect(await result).toEqual(session); });
  it('does not treat network failure as invalid credentials', async()=>{ const result=auth.restore(); http.expectOne('/api/session').error(new ProgressEvent('error')); expect(await result).toBeNull(); expect(auth.error()).toContain('Connessione'); });
  it('login sends credentials only to the login endpoint and routes by server role', async()=>{
    const result=auth.login('operator','secret'); const req=http.expectOne('/api/login'); expect(req.request.body).toEqual({username:'operator',password:'secret'}); req.flush(session); await result;
    expect(router.navigateByUrl).toHaveBeenCalledWith('/work'); expect(auth.session()?.active.role).toBe('OPERATORE');
  });
  it('keeps the current role when switching is rejected', async()=>{
    auth.session.set(session); const result=auth.switchRole('foreign').catch(()=>undefined); http.expectOne('/api/session/role').flush({error:'Non consentito'},{status:403,statusText:'Forbidden'}); await result;
    expect(auth.session()).toEqual(session); expect(router.navigateByUrl).not.toHaveBeenCalled();
  });
  it('clears stale identity and redirects when an API session expires', async()=>{
    auth.session.set(session); const result=TestBed.inject(Api).get('/work-queue').catch(()=>undefined); http.expectOne('/api/work-queue').flush({error:'Scaduta'},{status:401,statusText:'Unauthorized'}); await result;
    expect(auth.session()).toBeNull(); expect(router.navigateByUrl).toHaveBeenCalledWith('/login');
  });
  it('does not redirect on a rejected login', async()=>{ const result=auth.login('operator','wrong').catch(()=>undefined); http.expectOne('/api/login').flush({error:'Credenziali non valide'},{status:401,statusText:'Unauthorized'}); await result; expect(router.navigateByUrl).not.toHaveBeenCalled(); });
  it('invalidates the server session before clearing local identity', async()=>{ auth.session.set(session); const result=auth.logout(); expect(auth.session()).not.toBeNull(); http.expectOne('/api/logout').flush({ok:true}); await result; expect(auth.session()).toBeNull(); });
  it('routes every supported role',()=>{ expect(['MANAGER','OPERATORE','VALIDATORE','AMMINISTRATORE'].map(home)).toEqual(['/manager','/work','/validation','/admin']); });
});
