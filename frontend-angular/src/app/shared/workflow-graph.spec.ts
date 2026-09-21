import { NgZone } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { FCreateConnectionEvent } from '@foblex/flow';
import { WorkflowGraph } from './workflow-graph';

describe('Workflow graph interaction',()=>{
  it('uses the responsible group color in headers and legend without coloring the terminal',()=>{
    const fixture=TestBed.createComponent(WorkflowGraph);
    fixture.componentRef.setInput('tasks',[{code:'A',title:'A',assigned_group:'g',assigned_group_name:'Contabili',assigned_group_color:'#c4edce',transitions:{'*':['B']}},{code:'B',title:'B',assigned_group:'g',assigned_group_name:'Contabili',assigned_group_color:'#c4edce',transitions:{}}]);
    fixture.detectChanges();
    const headers=fixture.nativeElement.querySelectorAll('.graph-node header');
    expect(headers[0].style.backgroundColor).toBe('rgb(196, 237, 206)');
    expect(headers[0].textContent).toContain('Contabili');
    expect(fixture.nativeElement.querySelector('.graph-end').textContent).toContain('FINE');
    const legend=fixture.nativeElement.querySelectorAll('.graph-group-legend .group-color-chip');
    expect(legend.length).toBe(1);expect(legend[0].style.backgroundColor).toBe(headers[0].style.backgroundColor);
  });
  it('automatically toggles validation and protects generated nodes and edges',()=>{
    const fixture=TestBed.createComponent(WorkflowGraph),graph=fixture.componentInstance;
    fixture.componentRef.setInput('design',true);
    fixture.componentRef.setInput('tasks',[{code:'A',title:'A',is_initial:true,graph_position:{x:0,y:0},transitions:{}}]);
    fixture.componentRef.setInput('requiresValidation',true);fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.graph-start').textContent).toContain('INIZIO');
    expect(fixture.nativeElement.textContent).toContain('VALIDAZIONE FINALE');
    expect(graph.nodes().find(n=>n.code==='@START')!.position.x).toBeLessThan(0);
    const open=jasmine.createSpy(),edge=jasmine.createSpy();graph.nodeOpen.subscribe(open);graph.edgeOpen.subscribe(edge);
    graph.open('@START');graph.open('@VALIDATION');
    graph.editEdge(graph.edges().find(e=>e.from==='@START')!);
    expect(open).not.toHaveBeenCalled();expect(edge).not.toHaveBeenCalled();
    graph.editEdge(graph.edges().find(e=>e.from==='A')!);
    expect(edge.calls.mostRecent().args[0].to).toBe('@END');
    fixture.componentRef.setInput('requiresValidation',false);fixture.detectChanges();
    expect(graph.nodes().some(n=>n.code==='@VALIDATION')).toBeFalse();
  });
  it('renders one labelled port per outcome and shares it between parallel edges',()=>{
    const fixture=TestBed.createComponent(WorkflowGraph), graph=fixture.componentInstance;
    fixture.componentRef.setInput('tasks',[{code:'A',title:'A',outcomes:['OK','KO'],transitions:{OK:['B','C'],KO:['@END']}},{code:'B',title:'B',transitions:{}},{code:'C',title:'C',transitions:{}}]);
    fixture.detectChanges();
    const node=fixture.nativeElement.querySelector('[fnodeid="A"]') || fixture.nativeElement.querySelector('.graph-node');
    expect(node.querySelectorAll('.graph-output').length).toBe(2);
    expect(node.textContent).toContain('OK'); expect(node.textContent).toContain('KO');
    const edges=graph.edges().filter(e=>e.from==='A' && e.outcome==='OK');
    expect(edges.length).toBe(2);
    expect(new Set(edges.map(e=>graph.outputPort(e.from,e.outcome))).size).toBe(1);
  });
  it('keeps the terminal position while editing and resets it on automatic layout',()=>{
    const fixture=TestBed.createComponent(WorkflowGraph), graph=fixture.componentInstance;
    fixture.componentRef.setInput('design',true);
    fixture.componentRef.setInput('tasks',[{code:'A',title:'A',transitions:{}}]);
    graph.moved('@END',{x:700,y:240});
    expect(graph.nodes().find(n=>n.code==='@END')!.position).toEqual({x:700,y:240});
    fixture.componentRef.setInput('tasks',[{code:'A',title:'Renamed',transitions:{}}]);
    expect(graph.nodes().find(n=>n.code==='@END')!.position).toEqual({x:700,y:240});
    fixture.componentRef.setInput('disabled',true);
    graph.moved('@END',{x:1,y:1});
    expect(graph.nodes().find(n=>n.code==='@END')!.position).toEqual({x:700,y:240});
    graph.arrangeNodes();
    expect(graph.nodes().find(n=>n.code==='@END')!.position).not.toEqual({x:700,y:240});
  });
  it('delivers connector gestures inside Angular so the editor opens immediately',()=>{
    const fixture=TestBed.createComponent(WorkflowGraph), graph=fixture.componentInstance;
    fixture.componentRef.setInput('design',true);
    let received:unknown; let inZone=false;
    graph.connect.subscribe(event=>{received=event;inZone=NgZone.isInAngularZone();});
    TestBed.inject(NgZone).runOutsideAngular(()=>graph.create(new FCreateConnectionEvent(graph.outputPort('A 1','OK'),'in:B',{x:0,y:0})));
    expect(received).toEqual({from:'A 1',to:'B',outcome:'OK'});expect(inZone).toBeTrue();
  });
  it('opens task editors inside Angular after repeated external pointer callbacks',()=>{
    const fixture=TestBed.createComponent(WorkflowGraph),graph=fixture.componentInstance;
    const received:string[]=[];let inside=true;
    graph.nodeOpen.subscribe(code=>{received.push(code);inside=inside && NgZone.isInAngularZone();});
    TestBed.inject(NgZone).runOutsideAngular(()=>{graph.open('A');graph.open('B');graph.open('A');});
    expect(received).toEqual(['A','B','A']);expect(inside).toBeTrue();
  });
  it('never changes nodes or creates edges from a practice view or a busy editor',()=>{
    const fixture=TestBed.createComponent(WorkflowGraph), graph=fixture.componentInstance;
    const connect=jasmine.createSpy(),move=jasmine.createSpy();
    graph.connect.subscribe(connect); graph.positionChange.subscribe(move);
    graph.create(new FCreateConnectionEvent(graph.outputPort('A','OK'),'in:B',{x:0,y:0}));graph.moved('A',{x:4,y:5});
    fixture.componentRef.setInput('design',true);fixture.componentRef.setInput('disabled',true);
    graph.create(new FCreateConnectionEvent(graph.outputPort('A','OK'),'in:B',{x:0,y:0}));graph.moved('A',{x:4,y:5});
    expect(connect).not.toHaveBeenCalled();expect(move).not.toHaveBeenCalled();
  });
});
