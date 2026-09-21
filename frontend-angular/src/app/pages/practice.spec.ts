import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { EMPTY } from 'rxjs';
import { Practice } from './practice';
import { Api } from '../core/api';
import { Auth } from '../core/auth';
import { Practice as PracticeData, Task, Result, Evidence } from '../core/models';
const task=(code:string,extra:Partial<Task>={}):Task=>({code,title:'Attività '+code,instructions:'Istruzioni',status:'DA_FARE',active:true,required:true,assigned_group:'g',claimed_by:null,completed_by:null,due_date:'2099-12-31',depends_on:[],outcomes:[],transitions:{},result_id:null,work_note:'',reopen_reason:'',...extra});
const result=(id:string,code:string,time:string,note:string):Result=>({id,action:'TASK',related_task_code:code,outcome:'OK',note,actor:'Anna',actor_role:'OPERATORE',timestamp:time,evidence_ids:[]});
function data():PracticeData {
 return {id:'P1',client_id:'C1',client_name:'Studio cliente',practice_type_code:'LIPE',period_start:'2026-01-01',period_end:'2026-03-31',due_date:'2099-12-31',status:'IN_LAVORAZIONE',requires_validation:false,nonconformities:[],progress:{completed:1,total:2},tasks:[task('B',{status:'IN_LAVORAZIONE',claimed_by:'Luca',work_notes:[{actor:'Luca',note:'Documento richiesto',at:'2026-09-20T10:00:00Z'}]}),task('X',{active:false}),task('A',{status:'COMPLETATO',result_id:'R2',completed_by:'Anna'})],results:[result('R2','A','2026-09-19T11:00:00Z','Esito corrente'),result('R1','A','2026-09-18T11:00:00Z','Prima verifica')],evidence:[{id:'E1',filename:'prova.pdf',content_type:'application/pdf',description:'',document_type:'DOCUMENTO',actor:'Anna',created_at:'2026-09-18T11:00:00Z',preview_url:'/api/evidence/E1',download_url:'/api/evidence/E1',related_task_code:'A'}],audit:[{event_type:'TASK_PROGRESS_SAVED',actor:'Luca',at:'2026-09-20T10:00:00Z',details:{task_code:'B',note:'Documento richiesto'}}]};
}
describe('Practice dossier',()=>{
 beforeEach(()=>TestBed.configureTestingModule({providers:[provideRouter([]),{provide:ActivatedRoute,useValue:{paramMap:EMPTY}},{provide:Api,useValue:{}},{provide:Auth,useValue:{session:signal(null)}}]}));
 function page() { const fixture=TestBed.createComponent(Practice);fixture.componentInstance.data.set(data());fixture.componentInstance.loading.set(false);return fixture; }
 it('defaults to the dossier, orders reached activities and leaves the full graph accessible',()=>{
   const f=page(),p=f.componentInstance;f.detectChanges();
   expect(p.visibleTasks().map(t=>t.code)).toEqual(['A','B']);
   expect(f.nativeElement.querySelectorAll('.dossier-activity').length).toBe(2);
   expect(f.nativeElement.querySelector('wms-workflow-graph')).toBeNull();
   expect(f.nativeElement.textContent).toContain('Studio cliente');
   f.nativeElement.querySelector('#practice-graph-tab').click();f.detectChanges();
   expect(f.nativeElement.querySelector('wms-workflow-graph')).not.toBeNull();
   expect(f.nativeElement.querySelector('#practice-dossier').hidden).toBeTrue();
   f.nativeElement.querySelector('#practice-dossier-tab').click();f.detectChanges();
   expect(f.nativeElement.querySelector('#practice-dossier').hidden).toBeFalse();
 });
 it('preserves historical outcomes, all notes and unique documents in each activity',()=>{
   const f=page(),p=f.componentInstance,a=p.data()!.tasks[2],b=p.data()!.tasks[0];
   expect(p.taskResults(a).map(r=>r.id)).toEqual(['R2','R1']);
   expect(p.taskNotes(b).length).toBe(1);
   expect(p.noteCount(a)).toBe(2);
   p.data()!.results[0].evidence_ids=['E1'];
   expect(p.taskEvidence(a).map(e=>e.id)).toEqual(['E1']);
   expect(p.latestNotes()[0].note).toBe('Documento richiesto');
   f.detectChanges();
   expect(f.nativeElement.querySelector('.dossier-activity-body').textContent).toContain('Prima verifica');
   expect(f.nativeElement.querySelector('.dossier-activity-body').textContent).toContain('prova.pdf');
 });
 it('does not treat unreached branches as overdue and retains direct access to their detail',()=>{
   const f=page(),p=f.componentInstance;p.data()!.tasks[1].due_date='2000-01-01';
   expect(p.attentionItems()).toEqual([]);
   p.taskCode='X';expect(p.visibleTasks().map(t=>t.code)).toEqual(['X']);
   p.data()!.status='DA_VALIDARE';expect(p.operational()).toBeFalse();
   expect(p.phaseDescription()).toContain('validatore');
 });
});
