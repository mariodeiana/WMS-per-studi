import { AuditEvent, Result } from '../core/models';

export interface Point { x: number; y: number; }
export interface GraphTask {
  code: string; title: string; transitions: Record<string, string[]>;
  instructions?: string; assigned_group?: string; assigned_group_name?: string; assigned_group_color?: string; days_before_due?: number; due_date?: string;
  is_initial?: boolean; outcomes?: string[]; graph_position?: Point | null; active?: boolean; status?: string;
}
export interface GraphEdge { id: string; from: string; outcome: string; to: string; implicit: boolean; traversed: boolean; automatic?: boolean; originalTo?: string; }
export interface GraphNode { code: string; title: string; position: Point; state: string; label: string; initial: boolean; outcomes: string[]; }

export function graphIssues(tasks: GraphTask[]): {code:string;message:string}[] {
  const initial=tasks.filter(t=>t.is_initial ?? !tasks.some(s=>Object.values(s.transitions || {}).flat().includes(t.code)));
  const reached=new Set<string>(), pending=initial.map(t=>t.code);
  while(pending.length) {
    const code=pending.pop()!; if(reached.has(code)) continue; reached.add(code);
    const task=tasks.find(t=>t.code===code); if(task) pending.push(...Object.values(task.transitions || {}).flat());
  }
  const issues=tasks.length && !initial.length ? [{code:'',message:'Nessun nodo iniziale: scegli almeno un punto di avvio.'}] : [];
  for(const task of tasks) if(!reached.has(task.code)) issues.push({code:task.code,message:tasks.some(t=>Object.values(t.transitions || {}).flat().includes(task.code)) ? 'Non raggiungibile da un nodo iniziale' : 'Senza ingressi e non iniziale'});
  return issues;
}

export function graphOutcomes(task: GraphTask): string[] {
  const outcomes=[...new Set([...(task.outcomes || []), ...Object.keys(task.transitions || {})])];
  return outcomes.length ? outcomes : ['*'];
}

export function graphEdges(tasks: GraphTask[], results: Result[] = [], audit: AuditEvent[] = []): GraphEdge[] {
  const codes = new Set(tasks.map(t=>t.code));
  return tasks.flatMap(task => {
    const transitions = task.transitions || {};
    const choices = [...new Set([...Object.keys(transitions), ...(Object.hasOwn(transitions,'*') ? [] : task.outcomes || [])])];
    const last = results.filter(r=>r.action==='TASK' && r.related_task_code===task.code)
      .sort((a,b)=>b.timestamp.localeCompare(a.timestamp))[0];
    const selected = last && (Object.hasOwn(transitions,last.outcome) ? last.outcome : Object.hasOwn(transitions,'*') ? '*' : choices.includes(last.outcome) ? last.outcome : '*');
    return (choices.length ? choices : ['*']).flatMap(outcome => {
      const destinations = transitions[outcome] || [];
      return [...new Set(destinations.length ? destinations : ['@END'])]
        .filter(to=>to==='@END' || codes.has(to)).map(to=>({
          id: JSON.stringify([task.code,outcome,to]), from: task.code, outcome, to,
          implicit: !destinations.length,
          traversed: !!(last && selected===outcome) || audit.some(e=>e.event_type==='TASK_TRANSITION_SELECTED'
            && e.details['task_code']===task.code && (outcome==='*' ? !Object.hasOwn(transitions,String(e.details['outcome'])) : e.details['outcome']===outcome)
            && (e.details['destinations'] as string[] || []).includes(to))
        }));
    });
  });
}

// Presentation-only milestones: never persisted as tasks or workflow transitions.
export function workflowEdges(tasks: GraphTask[], results: Result[] = [], audit: AuditEvent[] = [], validation = false, status = ''): GraphEdge[] {
  if (!tasks.length) return [];
  const edges = graphEdges(tasks, results, audit).map(edge =>
    validation && edge.to === '@END' ? {...edge, to:'@VALIDATION', originalTo:'@END'} : edge);
  const starts = tasks.filter(t=>t.is_initial ?? !tasks.some(s=>Object.values(s.transitions || {}).flat().includes(t.code)));
  for (const task of starts) edges.push({
    id:JSON.stringify(['@START','*',task.code]), from:'@START',to:task.code,outcome:'*',
    implicit:false,traversed:task.active===true,automatic:true
  });
  if (validation) edges.push({
    id:'@VALIDATION-END',from:'@VALIDATION',to:'@END',outcome:'*',
    implicit:false,traversed:['VALIDATA','CHIUSA'].includes(status),automatic:true
  });
  return edges;
}

// Deterministic layered layout; stored positions override it without changing edges.
export function graphNodes(tasks: GraphTask[], edges: GraphEdge[], design: boolean, practiceStatus = ''): GraphNode[] {
  const codes = [...tasks.map(t=>t.code), ...(tasks.length ? ['@END'] : []), ...(['@START','@VALIDATION'].filter(c=>edges.some(e=>e.from===c || e.to===c)))];
  const ranks = new Map(codes.map(c=>[c,0]));
  const incoming = new Map(codes.map(c=>[c,new Set(edges.filter(e=>e.to===c).map(e=>e.from))]));
  const queue = codes.filter(c=>!incoming.get(c)?.size);
  const seen = new Set<string>();
  while(queue.length) {
    const code = queue.shift()!; if(seen.has(code)) continue; seen.add(code);
    for(const e of edges.filter(e=>e.from===code)) {
      ranks.set(e.to,Math.max(ranks.get(e.to)||0,(ranks.get(code)||0)+1));
      incoming.get(e.to)?.delete(code);
      if(!incoming.get(e.to)?.size) queue.push(e.to);
    }
  }
  const rows = new Map<number,number>();
  return codes.map(code=>{
    const t=tasks.find(t=>t.code===code), rank=ranks.get(code)||0, row=rows.get(rank)||0;
    const outcomes=t ? graphOutcomes(t) : code==='@END' ? [] : ['*'];
    rows.set(rank,row+Math.max(170,120+outcomes.length*34));
    const initial=t?.is_initial ?? !edges.some(e=>e.to===code);
    const state=design?'design':code==='@END' ? (edges.some(e=>e.to===code&&e.traversed)?'done':'unreached')
      : t?.active===false?'unreached':t?.status==='COMPLETATO'?'done'
      : ['DA_FARE','IN_LAVORAZIONE'].includes(practiceStatus)?'active':'paused';
    const label=design?(code==='@END'?'Fine ramo':initial?'Iniziale':'Attività'):
      ({design:'Attività',done:'Completata',active:'Attiva',unreached:'Non raggiunta',paused:'Sospesa'}[state]||'');
    const meta = code==='@START' || code==='@END' || code==='@VALIDATION';
    const metaState = design ? 'design' : code==='@START' ? 'done' : code==='@END' ? (practiceStatus==='CHIUSA'?'done':'unreached') : ['VALIDATA','CHIUSA'].includes(practiceStatus)?'done':practiceStatus==='DA_VALIDARE'?'active':practiceStatus==='NON_VALIDATA'?'paused':'unreached';
    return {code,title:t?.title || (code==='@START'?'INIZIO':code==='@VALIDATION'?'VALIDAZIONE FINALE':'FINE'),position:t?.graph_position || {x:40+rank*360,y:40+row},state:meta?metaState:state,label,initial:!!t && initial,outcomes};
  });
}

export function wouldCreateCycle(tasks: GraphTask[], from: string, to: string): boolean {
  const stack=[to], seen=new Set<string>();
  while(stack.length) {
    const code=stack.pop()!; if(code===from) return true; if(seen.has(code)) continue;
    seen.add(code); const task=tasks.find(t=>t.code===code);
    if(task) stack.push(...Object.values(task.transitions).flat().filter(c=>c!=='@END'));
  }
  return false;
}

export function graphNodeKinds(node:Pick<GraphNode,'code'|'initial'|'outcomes'>,edges:GraphEdge[]) {
  const kinds:{label:string;color:string}[]=[];
  if(node.code!=='@END' && node.initial) kinds.push({label:'Iniziale',color:'#dbeafe'});
  if(node.code==='@END' || !edges.some(e=>e.from===node.code && e.to!=='@END')) kinds.push({label:'Finale',color:'#fce1de'});
  if(node.outcomes.filter(o=>o!=='*').length>1) kinds.push({label:'Più esiti',color:'#eee1fa'});
  return kinds;
}
export function graphKindBackground(kinds:{color:string}[]) {
  if(!kinds.length) return '#ffffff';
  if(kinds.length===1) return kinds[0].color;
  return 'linear-gradient(135deg,'+kinds.map((k,i)=>k.color+' '+(i*100/kinds.length)+'%,'+k.color+' '+((i+1)*100/kinds.length)+'%').join(',')+')';
}

export function graphNodeSummary(task:GraphTask|undefined,kinds:{label:string}[]=[]) {
  if(!task) return 'TERMINE · Fine ramo\nGli altri rami attivi devono essere completati prima della conclusione della pratica.';
  const lines=[task.code+' · '+task.title];
  if(kinds.length) lines.push(kinds.map(k=>k.label).join(' · '));
  if(task.assigned_group) lines.push('Gruppo: '+(task.assigned_group_name || task.assigned_group));
  if(task.due_date) lines.push('Scadenza: '+task.due_date);
  else if(task.days_before_due !== undefined) lines.push('Scadenza: '+task.days_before_due+' giorni prima della pratica');
  if(task.status) lines.push('Stato: '+(task.active===false?'Non raggiunta':task.status));
  for(const outcome of graphOutcomes(task)) {
    const destinations=task.transitions[outcome] ?? task.transitions['*'] ?? [];
    lines.push((outcome==='*'?'Al completamento':outcome)+' → '+(destinations.length?destinations.map(d=>d==='@END'?'Fine ramo':d).join(', '):'Fine ramo'));
  }
  if(task.instructions) lines.push('Istruzioni: '+task.instructions);
  return lines.join('\n');
}
