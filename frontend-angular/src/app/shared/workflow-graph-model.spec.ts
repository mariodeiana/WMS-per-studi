import { graphEdges, graphNodes, graphIssues, GraphTask, wouldCreateCycle } from './workflow-graph-model';
import { Result } from '../core/models';
const task=(code:string,transitions:Record<string,string[]>={}):GraphTask=>({code,title:code,transitions});
const result=(code:string,outcome:string)=>({action:'TASK',related_task_code:code,outcome,timestamp:'2026-09-19T10:00:00Z'} as Result);
describe('Workflow graph projection',()=>{
  it('shows all branches but highlights only the outcome actually taken',()=>{
    const tasks=[task('A',{OK:['B'],KO:['C']}),task('B'),task('C')];
    const edges=graphEdges(tasks,[result('A','KO')]);
    expect(edges.filter(e=>e.traversed).map(e=>e.to)).toEqual(['C']);
    expect(edges.filter(e=>e.from==='A').length).toBe(2);
  });
  it('preserves parallel edges and explicit and implicit terminals',()=>{
    const tasks=[task('A',{'*':['B','C']}),task('B',{'*':['@END']}),task('C')];
    const edges=graphEdges(tasks,[result('A','OK')]);
    expect(edges.filter(e=>e.traversed).map(e=>e.to)).toEqual(['B','C']);
    expect(edges.find(e=>e.from==='C')?.implicit).toBeTrue();
    expect(edges.find(e=>e.from==='B')?.implicit).toBeFalse();
  });
  it('handles outcome terminals and default fallback exactly like the engine',()=>{
    const a={...task('A',{GO:['B']}),outcomes:['GO','STOP']};
    expect(graphEdges([a,task('B')],[result('A','STOP')]).find(e=>e.outcome==='STOP')?.traversed).toBeTrue();
    const fallback={...task('A',{'*':['B']}),outcomes:['GO','STOP']};
    const edges=graphEdges([fallback,task('B')],[result('A','STOP')]);
    expect(edges.filter(e=>e.from==='A').map(e=>e.outcome)).toEqual(['*']);
    expect(edges[0].traversed).toBeTrue();
  });
  it('distinguishes reached nodes from active work and keeps stored positions',()=>{
    const tasks=[{...task('A',{'*':['B']}),active:true,status:'COMPLETATO',graph_position:{x:99,y:44}},
      {...task('B',{'*':['C']}),active:true,status:'DA_FARE'}, {...task('C'),active:false,status:'DA_FARE'}];
    const nodes=graphNodes(tasks,graphEdges(tasks),false,'IN_LAVORAZIONE');
    expect(nodes.slice(0,3).map(n=>n.state)).toEqual(['done','active','unreached']);
    expect(nodes[0].position).toEqual({x:99,y:44});
    expect(graphNodes(tasks,graphEdges(tasks),false,'NON_VALIDATA')[1].state).toBe('paused');
  });
  it('lays out joins after predecessors regardless of list order and rejects cycles',()=>{
    const tasks=[task('C'),task('A',{'*':['B']}),task('B',{'*':['C']})];
    const nodes=graphNodes(tasks,graphEdges(tasks),true);
    expect(nodes.find(n=>n.code==='A')!.position.x).toBeLessThan(nodes.find(n=>n.code==='B')!.position.x);
    expect(wouldCreateCycle(tasks,'C','A')).toBeTrue();
    expect(wouldCreateCycle(tasks,'B','B')).toBeTrue();
    expect(wouldCreateCycle(tasks,'C','@END')).toBeFalse();
  });
});

describe('Explicit graph start nodes',()=>{
  it('flags disconnected branches without confusing legitimate multiple starts',()=>{
    const tasks=[{...task('A'),is_initial:true},{...task('B',{'*':['C']}),is_initial:false},{...task('C'),is_initial:false}];
    expect(graphIssues(tasks).map(i=>i.code)).toEqual(['B','C']);
    tasks[1].is_initial=true; expect(graphIssues(tasks)).toEqual([]);
    tasks[0].is_initial=false;tasks[1].is_initial=false;
    expect(graphIssues(tasks)[0].message).toContain('Nessun nodo iniziale');
  });
  it('keeps both outcome branches reachable and does not flag terminal nodes',()=>{
    const tasks=[{...task('A',{OK:['B'],KO:['C']}),is_initial:true},{...task('B'),is_initial:false},{...task('C'),is_initial:false}];
    expect(graphIssues(tasks)).toEqual([]);
  });
});
