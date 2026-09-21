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
      {code:'B',title:'Seconda',instructions:'',assigned_group:'g',days_before_due:0,required:true,depends_on:[],outcomes:[],transitions:{}}
    ]});
  });
  it('blocks submitting an incomplete client form',fakeAsync(()=>{
    const fixture=TestBed.createComponent(Admin); const page=fixture.componentInstance;
    api.get.and.returnValues(Promise.resolve({roles:[]}),Promise.resolve([]));
    page.entity='clients'; page.open();
    fixture.detectChanges(); tick(); fixture.detectChanges(); tick(); fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelector('dialog');
    if (!dialog.open) dialog.showModal();
    const bounds = dialog.getBoundingClientRect();
    const tabs = dialog.querySelector('[aria-label="Scheda cliente"]').getBoundingClientRect();
    const name = dialog.querySelectorAll('#client-general input')[1].getBoundingClientRect();
    expect(bounds.height).toBeGreaterThan(300);
    expect(tabs.height).toBeGreaterThan(20);
    expect(tabs.bottom).toBeLessThanOrEqual(bounds.bottom);
    expect(name.height).toBeGreaterThan(20);
    expect(name.bottom).toBeLessThanOrEqual(bounds.bottom);
    expect(fixture.nativeElement.querySelector('button[type=submit]').disabled).toBeTrue();
    page.draft['id']='000999'; page.draft['name']='Cliente'; fixture.detectChanges(); tick(); fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('button[type=submit]').disabled).toBeFalse();
  }));
  it('renames references without losing workflow edges',()=>{ admin.renameTask(admin.tasks[1],'C'); expect(admin.tasks[0].choices[0].destinations).toEqual(['C']);  });
  it('preserves unconditional transitions without creating a selectable star outcome',async()=>{ admin.open({id:'m',tasks:[{code:'A',outcomes:[],transitions:{'*':['@END']}}]}); api.post.and.rejectWith(new Error('Stop')); await admin.save(); const body=api.post.calls.mostRecent().args[1] as {tasks:{outcomes:string[];transitions:Record<string,string[]>}[]}; expect(body.tasks[0].outcomes).toEqual([]); expect(body.tasks[0].transitions).toEqual({'*':['@END']}); expect(admin.initial(admin.tasks[0])).toBeTrue(); });
  it('does not remove a referenced activity',()=>{ admin.removeTask(1); expect(admin.tasks.length).toBe(2); expect(admin.formError()).toContain('transizioni'); });
  it('reorders only presentation, preserving transitions',()=>{ admin.move(0,1); expect(admin.tasks.map(t=>t.code)).toEqual(['B','A']); expect(admin.tasks[1].choices[0].destinations).toEqual(['B']); });
  it('preserves the draft after a server validation failure',async()=>{ api.post.and.rejectWith(new Error('Modello non valido')); await admin.save(); expect(admin.editor()).toBeTrue(); expect(admin.tasks.length).toBe(2); expect(admin.formError()).toBe('Modello non valido'); expect(admin.busy()).toBeFalse(); });
  it('serializes configured outcomes and forward transitions for backend validation',async()=>{ api.post.and.rejectWith(new Error('Stop after request')); await admin.save(); const body=api.post.calls.mostRecent().args[1] as {tasks:{outcomes:string[];transitions:Record<string,string[]>;depends_on:string[]}[]}; expect(body.tasks[0].transitions).toEqual({SI:['B']}); expect(body.tasks[1].depends_on).toEqual([]); });
});

describe('Graph designer',()=>{
  let page:Admin, api:jasmine.SpyObj<Api>;
  beforeEach(()=>{
    api=jasmine.createSpyObj('Api',['get','post']);
    TestBed.configureTestingModule({providers:[provideRouter([]),{provide:Api,useValue:api}]});
    page=TestBed.runInInjectionContext(()=>new Admin()); page.entity='practice_types';
    page.open({id:'G',tasks:['A','B','C'].map(code=>({code,title:code,outcomes:[],transitions:{}}))});
  });
  it('adds parallel branches without replacing existing destinations',()=>{
    page.newEdge({from:'A',to:'B',outcome:'OK'}); expect(page.edgeDraft!.outcome).toBe('OK'); page.saveEdge();
    page.newEdge({from:'A',to:'C',outcome:'OK'}); page.saveEdge();
    expect(page.tasks[0].choices).toEqual([{name:'OK',destinations:['B','C']}]);
  });
  it('rejects a cycle without mutating the draft',()=>{
    page.newEdge({from:'A',to:'B'});page.saveEdge();
    page.newEdge({from:'B',to:'A'});page.saveEdge();
    expect(page.edgeError).toContain('ciclo'); expect(page.tasks[1].choices).toEqual([]);
  });
  it('edits one edge without deleting the other branch',()=>{
    page.tasks[0].choices=[{name:'OK',destinations:['B','C']}];
    page.editEdge({id:'edge',from:'A',to:'B',outcome:'OK',implicit:false,traversed:false});
    page.edgeDraft!.outcome='KO';page.saveEdge();
    expect(page.tasks[0].choices).toEqual([{name:'OK',destinations:['C']},{name:'KO',destinations:['B']}]);
  });
  it('stores layout independently and includes it in the saved model',async()=>{
    page.moveGraphNode({code:'A',position:{x:480,y:90}});
    expect(page.tasks[0].choices).toEqual([]);
    api.post.and.callFake(async <T>(path:string,body?:unknown)=>{if(path==='/admin/model-drafts')return {...body as object,revision:1,updated_at:new Date().toISOString()} as T;throw new Error('Stop');});await page.save();
    const body=api.post.calls.mostRecent().args[1] as {tasks:{graph_position:{x:number;y:number}}[]};
    expect(body.tasks[0].graph_position).toEqual({x:480,y:90});
    page.arrangeGraph();expect(page.tasks[0].graph_position).toBeUndefined();
  });
  it('prevents saving a model with a pending connection form',async()=>{
    page.newEdge({from:'A',to:'B'});await page.save();expect(api.post).not.toHaveBeenCalled();
  });
});

describe('Recoverable designer drafts',()=>{
  let page:Admin,api:jasmine.SpyObj<Api>;
  beforeEach(()=>{
    api=jasmine.createSpyObj('Api',['get','post']);
    TestBed.configureTestingModule({providers:[provideRouter([]),{provide:Api,useValue:api}]});
    page=TestBed.runInInjectionContext(()=>new Admin());page.entity='practice_types';page.open({id:'M',code:'M',name:'Modello',tasks:[]});
    api.post.and.callFake(async <T>(path:string,body?:unknown)=>({...body as object,revision:((body as {revision:number}).revision || 0)+1,updated_at:new Date().toISOString()} as T));
  });
  it('saves an incomplete graphical node as a private draft and restores its position',async()=>{
    page.addTask({x:450,y:210});page.graphTask!.title='Verifica';
    expect(page.graphTask).toBe(page.tasks[0]);
    expect(await page.persistDraft()).toBeTrue();
    expect(api.post.calls.mostRecent().args[0]).toBe('/admin/model-drafts');
    const saved=page.savedDrafts()[0];expect(saved.snapshot.tasks[0].graph_position).toEqual({x:450,y:210});
    page.resumeDraft(saved);expect(page.tasks[0].title).toBe('Verifica');
    expect(page.modelTab).toBe('tasks');expect(page.editor()).toBeTrue();
  });
  it('keeps the editor and its content after a failed autosave and refuses to close',async()=>{
    page.addTask();api.post.and.rejectWith(new Error('Sessione scaduta'));
    expect(await page.closeEditor()).toBeFalse();expect(page.editor()).toBeTrue();expect(page.tasks.length).toBe(1);
    expect(page.draftProblem()).toBeTrue();expect(api.post.calls.mostRecent().args[2]).toBeTrue();
  });
  it('does not send unchanged drafts repeatedly',async()=>{
    page.addTask();await page.persistDraft();await page.persistDraft();expect(api.post.calls.count()).toBe(1);
  });
  it('serializes saves so edits made during a request are not lost',async()=>{
    page.addTask();let finish!:(value:any)=>void;
    api.post.and.callFake(<T>(path:string,body?:unknown)=>new Promise<T>(resolve=>{finish=resolve;}));
    const first=page.persistDraft();page.tasks[0].title='Aggiornata durante il salvataggio';
    const sent=api.post.calls.mostRecent().args[1] as object;
    api.post.and.callFake(async <T>(path:string,body?:unknown)=>({...body as object,revision:2,updated_at:new Date().toISOString()} as T));
    finish({...sent,revision:1,updated_at:new Date().toISOString()});await first;
    await page.persistDraft();expect(page.savedDrafts()[0].snapshot.tasks[0].title).toBe('Aggiornata durante il salvataggio');
  });
});

describe('Client repertoire editor',()=>{
  let page:Admin, api:jasmine.SpyObj<Api>;
  beforeEach(()=>{
    api=jasmine.createSpyObj('Api',['get','post']);
    TestBed.configureTestingModule({providers:[provideRouter([]),{provide:Api,useValue:api}]});
    page=TestBed.runInInjectionContext(()=>new Admin());page.entity='clients';
  });
  it('saves fiscal data and repertoire together without mutating the original',async()=>{
    const client={id:'C',name:'Cliente',gis_company_code:'00123',repertoire:['LIPE']};
    page.open(client);page.toggle(page.repertoire,'IVA',true);page.draft['accounting_regime']='Ordinario';
    api.post.and.rejectWith(new Error('Errore di salvataggio'));await page.save();
    const body=api.post.calls.mostRecent().args[1] as Record<string,unknown>;
    expect(body['repertoire']).toEqual(['LIPE','IVA']);expect(body['gis_company_code']).toBe('00123');
    expect(client.repertoire).toEqual(['LIPE']);expect(page.editor()).toBeTrue();
    page.open(client);expect(page.repertoire).toEqual(['LIPE']);
  });
  it('shows only practices for the selected client and does not infer history',()=>{
    page.practices.set([{id:'P',client_id:'C',economic_regime:'IN_REPERTORIO'},{id:'Q',client_id:'OTHER'}]);
    page.open({id:'C'});expect(page.clientPractices().map(p=>p.id)).toEqual(['P']);
    expect(page.economicLabel(null)).toContain('storico');
  });
});
