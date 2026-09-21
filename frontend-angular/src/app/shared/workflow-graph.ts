import { ChangeDetectionStrategy, Component, ElementRef, NgZone, inject, computed, signal, input, output, viewChild } from '@angular/core';
import { FFlowModule, FFlowComponent, FCanvasComponent, FZoomDirective, FCreateConnectionEvent, FSelectionChangeEvent } from '@foblex/flow';
import { AuditEvent, Result } from '../core/models';
import { GraphTask, GraphEdge, GraphNode, Point, workflowEdges, graphNodes, graphIssues, graphNodeKinds, graphKindBackground, graphNodeSummary } from './workflow-graph-model';

@Component({selector:'wms-workflow-graph',imports:[FFlowModule],templateUrl:'./workflow-graph.html',changeDetection:ChangeDetectionStrategy.OnPush})
export class WorkflowGraph {
  private zone=inject(NgZone);
  requiresValidation=input(false);
  tasks=input<GraphTask[]>([]); design=input(false); disabled=input(false);
  results=input<Result[]>([]); audit=input<AuditEvent[]>([]); practiceStatus=input('');
  newNode=output<Point>(); validationOpen=output<void>();
  flow=viewChild(FFlowComponent);flowHost=viewChild('flowHost',{read:ElementRef<HTMLElement>});
  nodeOpen=output<string>(); edgeOpen=output<GraphEdge>(); connect=output<{from:string;to:string;outcome:string}>();
  positionChange=output<{code:string;position:Point}>(); arrange=output<void>();
  canvas=viewChild(FCanvasComponent); zoom=viewChild(FZoomDirective);
  initialNodes=computed(()=>this.nodes().filter(n=>n.code!=='@END' && n.initial));
  issues=computed(()=>this.design() ? graphIssues(this.tasks()) : []);
  orphan(code:string) { return this.issues().some(i=>i.code===code); }
  edges=computed(()=>workflowEdges(this.tasks(),this.results(),this.audit(),this.requiresValidation(),this.practiceStatus()));
  private endPosition=signal<Point|null>(null);
  nodes=computed(()=>{
    const nodes=graphNodes(this.tasks(),this.edges(),this.design(),this.practiceStatus());
    const tasks=nodes.filter(n=>!this.isMeta(n.code));
    if(!tasks.length) return nodes;
    const left=Math.min(...tasks.map(n=>n.position.x)),right=Math.max(...tasks.map(n=>n.position.x));
    return nodes.map(node=>{
      if(node.code==='@START') return {...node,position:{x:left-360,y:40}};
      if(node.code==='@VALIDATION') return {...node,position:{x:right+360,y:40}};
      if(node.code==='@END') return {...node,position:this.endPosition() || {x:right+(this.requiresValidation()?720:360),y:40}};
      return node;
    });
  });
  responsibleGroups=computed(()=>{
    const groups=new Map<string,{id:string;name:string;color:string}>();
    for(const task of this.tasks()) if(task.assigned_group) groups.set(task.assigned_group,{id:task.assigned_group,name:task.assigned_group_name || task.assigned_group,color:task.assigned_group_color || '#edf1f5'});
    return [...groups.values()];
  });
  nodeGroup(node:GraphNode) { const task=this.tasks().find(t=>t.code===node.code);return this.responsibleGroups().find(g=>g.id===task?.assigned_group); }
  nodeKinds(node:GraphNode) { return graphNodeKinds(node,this.edges()); }
  validationState() {
    return ({DA_VALIDARE:'Da eseguire',VALIDATA:'Validata',CHIUSA:'Validata',NON_VALIDATA:'Non validata — correzione richiesta'} as Record<string,string>)[this.practiceStatus()] || 'In attesa delle attività precedenti';
  }
  validationResult() { return this.results().filter(r=>r.action==='VALIDATION').sort((a,b)=>b.timestamp.localeCompare(a.timestamp))[0]; }
  openValidation() { if(!this.disabled()) this.zone.run(()=>this.validationOpen.emit()); }
  isMeta(code:string) {return ['@START','@END','@VALIDATION'].includes(code);}
  editEdge(edge:GraphEdge) {
    if(!this.design() || this.disabled() || edge.automatic) return;
    this.edgeOpen.emit({...edge,to:edge.originalTo || edge.to});
  }
  nodeSummary(node:GraphNode) {
    if(node.code==='@START') return 'INIZIO · Avvia tutte le attività contrassegnate come iniziali.';
    if(node.code==='@END') return 'FINE · La pratica termina dopo il completamento dei rami, l’eventuale validazione e la chiusura.';
    if(node.code==='@VALIDATION') return 'VALIDAZIONE FINALE · Attività del VALIDATORE. Registra esito, autore, data, note ed evidenze dopo il completamento dei rami raggiunti.';
    return graphNodeSummary(this.tasks().find(t=>t.code===node.code),this.nodeKinds(node)); }
  nodeBackground(node:GraphNode) { if(node.code==='@START') return '#dcfce7'; if(node.code==='@END') return '#fee2e2'; if(node.code==='@VALIDATION') return '#fef3c7'; return graphKindBackground(this.nodeKinds(node)); }
  arrangeNodes() { this.endPosition.set(null); this.arrange.emit(); }
  readonly zoomGesture=(event:{ctrlKey?:boolean;metaKey?:boolean})=>!!(event.ctrlKey || event.metaKey);
  private fitted=false;
  ready() { if(!this.fitted && this.nodes().length) { this.fitted=true; this.fit(); } }
  fit() { this.canvas()?.fitToScreen({x:35,y:35},false); }
  labelOffset(edge:GraphEdge) { return -24-30*this.edges().filter(e=>e.from===edge.from && e.to===edge.to).findIndex(e=>e.id===edge.id); }
  port(code:string, side:string) { return side+encodeURIComponent(code); }
  outputPort(code:string,outcome:string) { return 'out:'+encodeURIComponent(JSON.stringify([code,outcome])); }
  createAt(event:MouseEvent) {
    if(!this.design() || this.disabled() || (event.target as Element).closest('.graph-node,f-connection,button,.f-connection')) return;
    event.preventDefault();event.stopPropagation();this.emitNewNode(event.clientX,event.clientY);
  }
  addInCenter() {const rect=this.flowHost()?.nativeElement.getBoundingClientRect();if(rect)this.emitNewNode(rect.left+rect.width/2,rect.top+rect.height/2);}
  private emitNewNode(x:number,y:number) {
    if(!this.design() || this.disabled())return;
    const point=this.flow()?.getPositionInFlow({x,y});
    if(point) {this.fitted=true;this.zone.run(()=>this.newNode.emit({x:point.x,y:point.y}));}
  }
  create(event:FCreateConnectionEvent) {
    if(!this.design() || this.disabled() || !event.targetId) return;
    const to=decodeURIComponent(event.targetId.slice(3));
    const [from,outcome]=JSON.parse(decodeURIComponent(event.sourceId.slice(4))) as [string,string];
    if(this.isMeta(from) || to==='@START') return;
    this.zone.run(()=>this.connect.emit({from,to:to==='@VALIDATION'?'@END':to,outcome}));
  }
  select(event:FSelectionChangeEvent) {
    const edge=this.edges().find(e=>e.id===event.connectionIds[0]);
    if(edge && this.design() && !this.disabled()) this.zone.run(()=>this.editEdge(edge));
  }
  moved(code:string, position:Point) {
    if(!this.design() || this.disabled()) return;
    this.zone.run(()=>{
      if(code==='@END') this.endPosition.set({...position});
      else if(!this.isMeta(code)) this.positionChange.emit({code,position});
    });
  }
  open(code:string) { if(!this.isMeta(code) && !this.disabled()) this.zone.run(()=>this.nodeOpen.emit(code)); }
}
