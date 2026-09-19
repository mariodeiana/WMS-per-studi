import { TestBed } from '@angular/core/testing';
import { Work } from './work';
import { Api } from '../core/api';
import { QueueTask } from '../core/models';
describe('Operator queue',()=>{
  let page:Work;
  const task=(values:Partial<QueueTask>)=>({code:'T1',title:'Controllo documenti',practice_id:'P1',practice_type_code:'F24',client_id:'000001',queue_section:'ACTIVE',active:true,status:'DA_FARE',due_date:'2026-01-01',...values} as QueueTask);
  beforeEach(()=>{TestBed.configureTestingModule({providers:[{provide:Api,useValue:{}}]});page=TestBed.runInInjectionContext(()=>new Work());});
  it('puts active work before inactive paths and orders each by deadline',()=>{page.tasks.set([task({code:'WAIT',active:false,due_date:'2025-01-01'}),task({code:'LATER',due_date:'2026-02-01'}),task({code:'FIRST'})]);expect(page.rows('ACTIVE').map(t=>t.code)).toEqual(['FIRST','LATER','WAIT']);});
  it('searches notes and client identifiers without dropping the status filter',()=>{page.tasks.set([task({work_note:'Documento ricevuto',status:'IN_LAVORAZIONE'}),task({code:'T2',work_note:'Documento ricevuto'})]);page.search=' RICEVUTO ';page.filter='working';expect(page.rows('ACTIVE').map(t=>t.code)).toEqual(['T1']);page.search='000001';expect(page.rows('ACTIVE').length).toBe(1);});
  it('keeps inactive paths out of overdue work and preserves recent results regardless of active filter',()=>{spyOn(page,'days').and.returnValue(-2);page.tasks.set([task({active:false}),task({code:'DONE',queue_section:'RECENT_COMPLETED',completed_at:'2026-01-02',status:'COMPLETATO'})]);page.filter='late';expect(page.total('late')).toBe(0);expect(page.rows('ACTIVE').length).toBe(0);expect(page.rows('RECENT_COMPLETED').length).toBe(1);});
});
