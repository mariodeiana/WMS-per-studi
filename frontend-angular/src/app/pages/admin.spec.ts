import { fakeAsync, tick, TestBed } from '@angular/core/testing';
import { Admin } from './admin';
import { Api } from '../core/api';
import { provideRouter } from '@angular/router';

describe('Practice model editor',()=>{
  let admin: Admin, api: jasmine.SpyObj<Api>;
  beforeEach(()=>{
    api=jasmine.createSpyObj('Api',['get','post']);
    TestBed.configureTestingModule({providers:[provideRouter([]),{provide:Api,useValue:api}]});
    admin=TestBed.runInInjectionContext(()=>new Admin()); admin.entity='practice_types';
    admin.open({id:'model',code:'MODEL',name:'Modello',tasks:[
      {code:'A',title:'Prima',instructions:'',assigned_group:'g',days_before_due:0,required:true,depends_on:[],outcomes:['SI'],transitions:{SI:['B']}},
      {code:'B',title:'Seconda',instructions:'',assigned_group:'g',days_before_due:0,required:true,depends_on:['A'],outcomes:[],transitions:{}}
    ]});
  });
  it('blocks submitting an incomplete client form',fakeAsync(()=>{
    const fixture=TestBed.createComponent(Admin); const page=fixture.componentInstance;
    api.get.and.returnValues(Promise.resolve({roles:[]}),Promise.resolve([]));
    page.entity='clients'; page.open();
    fixture.detectChanges(); tick(); fixture.detectChanges(); tick(); fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('button[type=submit]').disabled).toBeTrue();
    page.draft['id']='000999'; page.draft['name']='Cliente'; fixture.detectChanges(); tick(); fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('button[type=submit]').disabled).toBeFalse();
  }));
  it('renames references without losing workflow edges',()=>{ admin.renameTask(admin.tasks[1],'C'); expect(admin.tasks[0].choices[0].destinations).toEqual(['C']); admin.renameTask(admin.tasks[0],'FIRST'); expect(admin.tasks[1].depends_on).toEqual(['FIRST']); });
  it('does not remove a referenced activity',()=>{ admin.removeTask(1); expect(admin.tasks.length).toBe(2); expect(admin.formError()).toContain('transizioni'); });
  it('reorders only presentation, preserving transitions',()=>{ admin.move(0,1); expect(admin.tasks.map(t=>t.code)).toEqual(['B','A']); expect(admin.tasks[1].choices[0].destinations).toEqual(['B']); });
  it('preserves the draft after a server validation failure',async()=>{ api.post.and.rejectWith(new Error('Modello non valido')); await admin.save(); expect(admin.editor()).toBeTrue(); expect(admin.tasks.length).toBe(2); expect(admin.formError()).toBe('Modello non valido'); expect(admin.busy()).toBeFalse(); });
  it('serializes configured outcomes and dependencies for backend validation',async()=>{ api.post.and.rejectWith(new Error('Stop after request')); await admin.save(); const body=api.post.calls.mostRecent().args[1] as {tasks:{outcomes:string[];transitions:Record<string,string[]>;depends_on:string[]}[]}; expect(body.tasks[0].transitions).toEqual({SI:['B']}); expect(body.tasks[1].depends_on).toEqual(['A']); });
});
