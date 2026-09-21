import { ChangeDetectionStrategy, Component, ElementRef, NgZone, inject, computed, signal, input, output, viewChild } from '@angular/core';
import { FFlowModule, FFlowComponent, FCanvasComponent, FZoomDirective, FCreateConnectionEvent, FSelectionChangeEvent } from '@foblex/flow';
import { AuditEvent, Result } from '../core/models';
import { GraphTask, GraphEdge, GraphNode, Point, graphEdges, graphNodes, graphIssues, graphNodeKinds, graphKindBackground, graphNodeSummary } from './workflow-graph-model';

@Component({selector:'wms-workflow-graph',imports:[FFlowModule],templateUrl:'./workflow-graph.html',changeDetection:ChangeDetectionStrategy.OnPush})
export class WorkflowGraph {
  private zone=inject(NgZone);
  tasks=input<GraphTask[]>([]); design=input(false); disabled=input(false);
  results=input<Result[]>([]); audit=input<AuditEvent[]>([]); practiceStatus=input('');
  newNode=output<Point>();
  flow=viewChild(FFlowComponent);flowHost=viewChild('flowHost',{read:ElementRef<HTMLElement>});
  nodeOpen=output<string>(); edgeOpen=output<GraphEdge>(); connect=output<{from:string;to:string;outcome:string}>();
  positionChange=output<{code:string;position:Point}>(); arrange=output<void>();
  canvas=viewChild(FCanvasComponent); zoom=viewChild(FZoomDirective);
  initialNodes=computed(()=>this.nodes().filter(n=>n.code!=='@END' && n.initial));
  issues=computed(()=>this.design() ? graphIssues(this.tasks()) : []);
  orphan(code:string) { return this.issues().some(i=>i.code===code); }
  edges=computed(()=>graphEdges(this.tasks(),this.results(),this.audit()));
  private endPosition=signal<Point|null>(null);
  nodes=computed(()=>graphNodes(this.tasks(),this.edges(),this.design(),this.practiceStatus()).map(node=>
    node.code==='@END' && this.endPosition() ? {...node,position:this.endPosition()!} : node));
  responsibleGroups=computed(()=>{
    const groups=new Map<string,{id:string;name:string;color:string}>();
    for(const task of this.tasks()) if(task.assigned_group) groups.set(task.assigned_group,{id:task.assigned_group,name:task.assigned_group_name || task.assigned_group,color:task.assigned_group_color || '#edf1f5'});
    return [...groups.values()];
  });
  nodeGroup(node:GraphNode) { const task=this.tasks().find(t=>t.code===node.code);return this.responsibleGroups().find(g=>g.id===task?.assigned_group); }
  nodeKinds(node:GraphNode) { return graphNodeKinds(node,this.edges()); }
  nodeSummary(node:GraphNode) { return graphNodeSummary(this.tasks().find(t=>t.code===node.code),this.nodeKinds(node)); }
  nodeBackground(node:GraphNode) { return graphKindBackground(this.nodeKinds(node)); }
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
    this.zone.run(()=>this.connect.emit({from,to,outcome}));
  }
  select(event:FSelectionChangeEvent) {
    const edge=this.edges().find(e=>e.id===event.connectionIds[0]);
    if(edge && this.design() && !this.disabled()) this.zone.run(()=>this.edgeOpen.emit(edge));
  }
  moved(code:string, position:Point) {
    if(!this.design() || this.disabled()) return;
    this.zone.run(()=>{
      if(code==='@END') this.endPosition.set({...position});
      else this.positionChange.emit({code,position});
    });
  }
  open(code:string) { if(code!=='@END' && !this.disabled()) this.nodeOpen.emit(code); }
}
