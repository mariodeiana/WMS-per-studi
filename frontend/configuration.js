const ENTITY_META = {
  users: {title:'Utenti', fields:[['id','ID'],['username','Login'],['display_name','Nome visualizzato'],['default_membership_id','Appartenenza predefinita']]},
  groups: {title:'Gruppi', fields:[['id','Codice'],['name','Nome'],['role','Ruolo']]},
  memberships: {title:'Appartenenze', fields:[['id','ID'],['user_id','Utente'],['group_id','Gruppo'],['label','Etichetta']]},
  assignment_policies: {title:'Politiche di assegnazione', fields:[['id','Codice'],['name','Nome'],['strategy','Strategia'],['description','Descrizione']]},
  practice_types: {title:'Tipi di pratica', fields:[['id','ID'],['code','Codice'],['name','Nome'],['description','Descrizione']]},
  clients: {title:'Clienti', fields:[['id','Codice cliente'],['name','Nome / Ragione sociale'],['tax_code','Codice fiscale'],['vat_number','Partita IVA'],['email','Email']]},
  practices: {title:'Pratiche', fields:[['id','Codice'],['client_id','Cliente'],['practice_type_code','Tipo'],['period_start','Dal'],['period_end','Al'],['due_date','Scadenza']]}
};
let configData, currentEntity='groups', practiceRows=[], editorEntity, editingRow, taskDraft=[], activeTask=0;
const $ = id => document.getElementById(id);
function escapeHtml(value) { return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const escapeAttr=escapeHtml;
async function api(url,options) { const r=await fetch(url,options);const p=await r.json();if(!r.ok)throw new Error(p.error||'Operazione non riuscita');return p; }
const post=(url,body)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
async function load() {
  [configData,practiceRows]=await Promise.all([api('/api/admin/config'),api('/api/admin/practices')]);
  renderNav();renderTable();
}
function renderNav() {
  const tabs=[...document.querySelectorAll('.cfg-nav [role="tab"]')];
  function activate(tab) {
    currentEntity=tab.dataset.entity;
    renderNav();renderTable();
    tab.scrollIntoView({block:'nearest',inline:'nearest'});
  }
  tabs.forEach((tab,index)=>{
    const selected=tab.dataset.entity===currentEntity;
    tab.classList.toggle('active',selected);
    tab.setAttribute('aria-selected',String(selected));
    tab.tabIndex=selected?0:-1;
    tab.onclick=()=>activate(tab);
    tab.onkeydown=event=>{
      let next;
      if(event.key==='ArrowRight')next=(index+1)%tabs.length;
      else if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;
      else if(event.key==='Home')next=0;
      else if(event.key==='End')next=tabs.length-1;
      else return;
      event.preventDefault();tabs[next].focus();activate(tabs[next]);
    };
  });
  $('cfg-panel').setAttribute('aria-labelledby','cfg-tab-'+currentEntity);
}
function lookup(entity,id,field='name') {const r=(configData[entity]||[]).find(x=>x.id===id);return r?(r[field]||id):id||'';}
function displayValue(field,value) {
  if(field==='user_id')return lookup('users',value,'display_name');
  if(field==='group_id')return lookup('groups',value);
  if(field==='client_id')return lookup('clients',value);
  return value==='MANAGER'?'Supervisore':value??'';
}
function renderTable() {
  const meta=ENTITY_META[currentEntity],practices=currentEntity==='practices';
  $('cfg-title').textContent=meta.title;
  $('cfg-new').textContent=practices?'Nuova pratica':'Nuovo';
  $('cfg-help').textContent={clients:'Anagrafica dei clienti. I codici importati dalle pratiche esistenti possono essere completati con i dati anagrafici.',practice_types:'Modelli di pratica: configura attività, gruppi, esiti, transizioni e scadenze con Modifica. Le modifiche si applicano alle nuove pratiche.',practices:'Crea una pratica scegliendo cliente, modello, periodo e scadenza. Il grafo viene copiato dal modello; solo le attività attivate compaiono nelle code operative.'}[currentEntity]||'';
  $('cfg-error').textContent='';
  const rows=practices?practiceRows:(configData[currentEntity]||[]);
  const fields=currentEntity==='practice_types'?[...meta.fields,['task_count','Attività']]:meta.fields;
  $('cfg-head').innerHTML='<tr>'+fields.map(f=>`<th scope="col">${f[1]}</th>`).join('')+'<th scope="col">Stato</th><th scope="col">Azioni</th></tr>';
  $('cfg-body').innerHTML='';
  for(const row of rows) {
    const tr=document.createElement('tr');
    tr.innerHTML=fields.map(f=>`<td>${escapeHtml(f[0]==='task_count'?(row.tasks||[]).length:displayValue(f[0],row[f[0]]))}</td>`).join('')+`<td>${escapeHtml(practices?row.status.replaceAll('_',' '):(row.active===false?'Disattivo':'Attivo'))}</td><td><div class="row-actions"></div></td>`;
    const actions=tr.querySelector('.row-actions');
    function action(label,callback){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=callback;actions.appendChild(b);}
    if(practices) action('Attività',()=>showPractice(row));
    else {action('Modifica',()=>openEditor(row));action('Elimina',()=>removeItem(row));}
    $('cfg-body').appendChild(tr);
  }
  $('cfg-empty').hidden=rows.length>0;
}
function input(name,label,value='',type='text',extra='') {
  return `<label>${label}<input name="${name}" type="${type}" value="${escapeAttr(value)}" ${extra}></label>`;
}
function check(name,label,checked){return `<label class="check"><input type="checkbox" name="${name}" ${checked?'checked':''}>${label}</label>`;}
function selectHtml(name,label,options,value,extra='') {
  return `<label>${label}<select aria-label="${label}" name="${name}" ${extra}>${options.map(o=>`<option value="${escapeAttr(o.value)}" ${o.value===value?'selected':''}>${escapeHtml(o.label)}</option>`).join('')}</select></label>`;
}
function setupDialog(title,wide=false) {
  $('editor-title').textContent=title;
  $('cfg-dialog').classList.toggle('model-editor',wide);
  $('cfg-dialog').classList.remove('model-config');
  $('cfg-form').innerHTML='';
  $('cfg-form').noValidate=false;
}
function finishDialog(html,submit) {
  $('cfg-form').innerHTML=html+'<p id="form-error" class="form-error" role="alert"></p><div class="dialog-actions"><button type="button" id="cfg-cancel">Annulla</button><button type="submit">Salva</button></div>';
  $('cfg-cancel').onclick=()=>$('cfg-dialog').close();
  $('cfg-form').onsubmit=submit;
  $('cfg-dialog').showModal();
}
function openEditor(row={}) {
  if(currentEntity==='practices'){openNewPractice();return;}
  editorEntity=currentEntity;editingRow=row;
  const meta=ENTITY_META[editorEntity],isModel=editorEntity==='practice_types';
  setupDialog((row.id?'Modifica · ':'Nuovo · ')+meta.title,isModel);
  let html='<div class="cfg-fields">';
  for(const [name,label] of meta.fields) {
    if(editorEntity==='groups'&&name==='role')html+=selectHtml(name,label,configData.roles.map(x=>({value:x,label:x==='MANAGER'?'Supervisore':x})),row[name]||'OPERATORE');
    else if(editorEntity==='memberships'&&['user_id','group_id'].includes(name)) {
      const entity=name==='user_id'?'users':'groups';
      html+=selectHtml(name,label,configData[entity].map(x=>({value:x.id,label:x.name||x.display_name})),row[name]||'');
    } else if(name==='description')html+=`<label class="cfg-wide">${label}<textarea name="${name}">${escapeHtml(row[name])}</textarea></label>`;
    else html+=input(name,label,row[name]||'',name==='email'?'email':'text',(row.id&&name==='id'?'readonly ':'')+(['id','name','code'].includes(name)?'required':''));
  }
  html+='</div>'+check('active','Attivo',row.active!==false);
  if(isModel) {
    taskDraft=structuredClone(row.tasks||[]);activeTask=-1;
    $('cfg-dialog').classList.add('model-config');
    html+=check('requires_validation','Richiede validazione finale',row.requires_validation!==false);
    html='<div class="model-tabs" role="tablist" aria-label="Modello di pratica"><button type="button" id="model-tab-general" role="tab" aria-controls="model-general">Dati generali</button><button type="button" id="model-tab-tasks" role="tab" aria-controls="model-tasks">Attività</button></div><div class="model-content"><section id="model-general" role="tabpanel" aria-labelledby="model-tab-general">'+html+'</section><section id="model-tasks" role="tabpanel" aria-labelledby="model-tab-tasks" hidden><div class="model-task-toolbar"><p id="model-task-count"></p><button type="button" id="task-add">Aggiungi attività</button></div><p class="model-hint">Apri un’attività per modificarla. Sposta su/giù cambia solo l’ordine visuale; gli esiti determinano le attività successive.</p><div id="task-list"></div></section></div>';
  }
  finishDialog(html,saveItem);
  if(isModel){
    for(const key of ['general','tasks']) {
      const button=$('model-tab-'+key);button.onclick=()=>selectModelTab(key);
      button.onkeydown=event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?'general':event.key==='End'?'tasks':key==='general'?'tasks':'general';selectModelTab(next);$('model-tab-'+next).focus();}};
    }
    $('cfg-form').noValidate=true;
    selectModelTab('general');renderTasks();$('task-add').onclick=()=>{captureTasks();activeTask=taskDraft.length;taskDraft.push({code:'',title:'',instructions:'',assigned_group:'contabili',required:true,outcomes:[],transitions:{},days_before_due:0});renderTasks();$('task-list').lastElementChild.scrollIntoView({block:'nearest'});$('task-list').lastElementChild.querySelector('input').focus();};}
}
function selectModelTab(key) {
  for(const name of ['general','tasks']) {
    const selected=name===key;
    $('model-'+name).hidden=!selected;
    $('model-tab-'+name).setAttribute('aria-selected',String(selected));
    $('model-tab-'+name).tabIndex=selected?0:-1;
  }
}
$('cfg-form').addEventListener('invalid',event=>{
  if(!$('cfg-dialog').classList.contains('model-config'))return;
  const activity=event.target.closest('.task-detail');
  selectModelTab(activity?'tasks':'general');
  if(activity){activity.open=true;activeTask=Number(activity.dataset.index);}
},true);
function normalizeTaskWorkflow(task) {
  task.outcomes=Array.isArray(task.outcomes)?task.outcomes:[];
  task.transitions=task.transitions&&typeof task.transitions==='object'?task.transitions:{};
  for(const outcome of task.outcomes) {
    if(!Array.isArray(task.transitions[outcome]))task.transitions[outcome]=[];
  }
  for(const outcome of Object.keys(task.transitions)) {
    if(outcome!=='*'&&!task.outcomes.includes(outcome))task.outcomes.push(outcome);
  }
  return task;
}

function addTaskOutcome(taskIndex) {
  captureTasks();
  const task=normalizeTaskWorkflow(taskDraft[taskIndex]);
  let base='NUOVO ESITO',name=base,n=2;
  while(task.outcomes.includes(name))name=base+' '+n++;
  task.outcomes.push(name);
  task.transitions[name]=[];
  activeTask=taskIndex;
  renderTasks();
}

function removeTaskOutcome(taskIndex,outcome) {
  captureTasks();
  const task=normalizeTaskWorkflow(taskDraft[taskIndex]);
  task.outcomes=task.outcomes.filter(x=>x!==outcome);
  delete task.transitions[outcome];
  activeTask=taskIndex;
  renderTasks();
}

function renameTaskOutcome(taskIndex,oldName,newName) {
  const task=normalizeTaskWorkflow(taskDraft[taskIndex]);
  newName=newName.trim();
  if(!newName||newName===oldName)return;
  if(task.outcomes.includes(newName))throw new Error('Esito già presente: '+newName);
  const destinations=task.transitions[oldName]||[];
  task.outcomes=task.outcomes.map(x=>x===oldName?newName:x);
  delete task.transitions[oldName];
  task.transitions[newName]=destinations;
}

function captureTasks() {
  document.querySelectorAll('.task-editor').forEach((el,i)=>{
    const val=n=>el.querySelector(`[data-field="${n}"]`).value;
    const task=normalizeTaskWorkflow(taskDraft[i]);
    const outcomes=[...el.querySelectorAll('.task-outcome')].map(row=>row.querySelector('[data-outcome-name]').value.trim()).filter(Boolean);
    const transitions={};
    [...el.querySelectorAll('.task-outcome')].forEach(row=>{
      const outcome=row.querySelector('[data-outcome-name]').value.trim();
      if(outcome)transitions[outcome]=[...row.querySelectorAll('[data-transition]:checked')].map(e=>e.value);
    });
    taskDraft[i]={...task,code:val('code').trim(),title:val('title'),instructions:val('instructions'),assigned_group:val('assigned_group'),days_before_due:Number(val('days_before_due')),required:true,depends_on:[],outcomes:outcomes.filter(o=>o!=='*'),transitions};
  });
}
function renderTasks() {
  const groups=configData.groups.filter(g=>g.role==='OPERATORE');
  $('model-task-count').textContent=taskDraft.length+' attività nel modello';
  $('model-tab-tasks').textContent='Attività ('+taskDraft.length+')';
  $('task-list').innerHTML=taskDraft.map((t,i)=>`<details class="task-detail" name="model-activity" data-index="${i}" ${i===activeTask?'open':''}><summary><span class="task-number">${i+1}</span><span class="task-summary-title"><strong>${escapeHtml(t.code||'Nuova attività')} — ${escapeHtml(t.title||'Da compilare')}</strong><small>${escapeHtml(lookup('groups',t.assigned_group))} · ${t.days_before_due||0} giorni prima · ${t.required!==false?'Obbligatoria':'Facoltativa'}</small></span><span class="task-disclosure" aria-hidden="true">⌄</span></summary><fieldset class="task-editor"><legend>Dettagli attività</legend><div class="task-fields">
    <label>Codice attività<input data-field="code" value="${escapeAttr(t.code)}" required></label>
    <label>Titolo<input data-field="title" value="${escapeAttr(t.title)}" required></label>
    <label>Gruppo responsabile<select aria-label="Gruppo responsabile" data-field="assigned_group" required><option value="">Scegli gruppo</option>${groups.map(g=>`<option value="${escapeAttr(g.id)}" ${g.id===t.assigned_group?'selected':''}>${escapeHtml(g.name)}${g.active===false?' (disattivato)':''}</option>`).join('')}</select></label>
    <label>Giorni prima della scadenza<input data-field="days_before_due" type="number" min="0" max="3650" step="1" value="${t.days_before_due||0}" required></label>
    <label class="cfg-wide">Istruzioni operative<textarea data-field="instructions">${escapeHtml(t.instructions)}</textarea></label>
    <p>Ogni attività raggiunta deve essere completata.</p>
    <div class="cfg-wide task-workflow"><div class="task-workflow-head"><strong>Esiti e attività successive</strong><button type="button" data-add-outcome>Aggiungi esito</button></div>
      <p class="model-hint">Al completamento l’operatore sceglie un esito; il WMS attiva le attività successive associate.</p>
      <div class="task-outcomes">${Object.keys(normalizeTaskWorkflow(t).transitions).map(outcome=>`<div class="task-outcome" data-outcome="${escapeAttr(outcome)}">
        <div class="task-outcome-head"><label>Esito (* = qualsiasi esito)<input data-outcome-name value="${escapeAttr(outcome)}" required></label><button type="button" data-remove-outcome>Rimuovi esito</button></div>
        <div class="task-next"><span>Attività successive:</span><label class="check"><input data-transition type="checkbox" value="@END" ${(t.transitions[outcome]||[]).includes('@END')?'checked':''}>Fine ramo</label>${taskDraft.filter((d,j)=>j!==i&&d.code).map(d=>`<label class="check"><input data-transition type="checkbox" value="${escapeAttr(d.code)}" ${(t.transitions[outcome]||[]).includes(d.code)?'checked':''}>${escapeHtml(d.code)} — ${escapeHtml(d.title)}</label>`).join('')||'<small>Nessun’altra attività con codice disponibile.</small>'}</div>
      </div>`).join('')||'<small>Nessuna transizione: il completamento termina questo ramo.</small>'}</div>
    </div>
    </div><div class="task-controls"><button type="button" data-up ${i===0?'disabled':''}>Sposta su</button><button type="button" data-down ${i===taskDraft.length-1?'disabled':''}>Sposta giù</button><button type="button" data-remove>Rimuovi attività</button></div></fieldset></details>`).join('');
  document.querySelectorAll('.task-detail').forEach(el=>{el.ontoggle=()=>{
    if(!el.isConnected)return;
    const index=Number(el.dataset.index);
    if(el.open)activeTask=index;
    else {
      captureTasks();
      if(activeTask===index)activeTask=-1;
      const t=taskDraft[index];
      el.querySelector('summary strong').textContent=(t.code||'Nuova attività')+' — '+(t.title||'Da compilare');
      el.querySelector('summary small').textContent=lookup('groups',t.assigned_group)+' · '+t.days_before_due+' giorni prima · '+(t.required?'Obbligatoria':'Facoltativa');
    }
  };});
  document.querySelectorAll('.task-editor').forEach((el,i)=>{
    el.querySelector('[data-field="code"]').onchange=()=>{
      const old=taskDraft[i].code;captureTasks();const next=taskDraft[i].code;
      if(old)taskDraft.forEach(t=>{
        normalizeTaskWorkflow(t);
        for(const outcome of Object.keys(t.transitions))t.transitions[outcome]=t.transitions[outcome].map(d=>d===old?next:d);
      });
      renderTasks();
    };
    el.querySelector('[data-add-outcome]').onclick=()=>addTaskOutcome(i);
    el.querySelectorAll('.task-outcome').forEach(row=>{
      const oldName=row.dataset.outcome;
      row.querySelector('[data-outcome-name]').onchange=event=>{
        try{
          const newName=event.target.value.trim();
          if(!newName){$('form-error').textContent='L’esito non può essere vuoto.';return;}
          if(newName!==oldName&&taskDraft[i].outcomes.includes(newName)){
            $('form-error').textContent='Esito già presente: '+newName;
            return;
          }
          renameTaskOutcome(i,oldName,newName);
          activeTask=i;
          renderTasks();
        }
        catch(error){$('form-error').textContent=error.message;renderTasks();}
      };
      row.querySelector('[data-remove-outcome]').onclick=()=>removeTaskOutcome(i,oldName);
    });
    el.querySelector('[data-up]').onclick=()=>moveTask(i,-1);
    el.querySelector('[data-down]').onclick=()=>moveTask(i,1);
    el.querySelector('[data-remove]').onclick=()=>{
      captureTasks();const code=taskDraft[i].code;
      const referenced=taskDraft.some((t,j)=>j!==i&&Object.values(normalizeTaskWorkflow(t).transitions).some(destinations=>destinations.includes(code)));
      if(referenced){$('form-error').textContent='Rimuovi prima le transizioni verso questa attività.';return;}
      taskDraft.splice(i,1);activeTask=Math.min(i,taskDraft.length-1);renderTasks();
    };
  });
}
function moveTask(i,delta){captureTasks();activeTask=i+delta;[taskDraft[i],taskDraft[i+delta]]=[taskDraft[i+delta],taskDraft[i]];renderTasks();}
async function saveItem(ev) {
  ev.preventDefault();
  if(editorEntity==='practice_types') {
    const invalid=[...ev.currentTarget.elements].find(el=>el.willValidate&&!el.validity.valid);
    if(invalid){const activity=invalid.closest('.task-detail');selectModelTab(activity?'tasks':'general');if(activity){activity.open=true;activeTask=Number(activity.dataset.index);}invalid.reportValidity();return;}
  }
  const fd=new FormData(ev.currentTarget);const item={...editingRow,...Object.fromEntries(fd.entries()),active:fd.has('active')};
  if(editorEntity==='practice_types'){captureTasks();item.tasks=taskDraft;item.requires_validation=fd.has('requires_validation');}
  await saveDialog(()=>post(`/api/admin/config/${editorEntity}`,item));
}
async function saveDialog(operation) {
  const button=$('cfg-form').querySelector('[type=submit]');button.disabled=true;$('form-error').textContent='';
  try{await operation();$('cfg-dialog').close();await load();}
  catch(e){if($('cfg-dialog').open)$('form-error').textContent=e.message;else $('cfg-error').textContent=e.message;}
  finally{button.disabled=false;}
}
function openNewPractice() {
  setupDialog('Nuova pratica');
  const opts=(entity,label)=>[{value:'',label},...configData[entity].filter(r=>r.active!==false).map(r=>({value:r.id,label:r.name||r.code||r.id}))];
  finishDialog('<div class="cfg-fields">'+selectHtml('client_id','Cliente',opts('clients','Scegli cliente'),'','required')+selectHtml('model_id','Modello',opts('practice_types','Scegli modello'),'','required')+input('period_start','Inizio periodo','','date','required')+input('period_end','Fine periodo','','date','required')+input('due_date','Scadenza pratica','','date','required')+'</div><p>Le attività e le assegnazioni verranno copiate dal modello selezionato.</p>',async ev=>{ev.preventDefault();await saveDialog(()=>post('/api/admin/practices',Object.fromEntries(new FormData(ev.currentTarget))));});
  $('cfg-form').querySelector('[type=submit]').textContent='Crea pratica';
}
async function showPractice(row) {
  try {
    const p=await api('/api/practices/'+encodeURIComponent(row.id));setupDialog('Attività · '+row.id,true);
    $('cfg-form').innerHTML=`<p>Cliente: ${escapeHtml(lookup('clients',p.client_id))} · Scadenza: ${escapeHtml(p.due_date)}</p><div class="cfg-table-wrap"><table class="cfg-table cfg-activity-table"><colgroup><col class="activity-name"><col class="activity-group"><col class="activity-date"><col class="activity-deps"><col class="activity-status"></colgroup><thead><tr><th>Attività</th><th>Gruppo</th><th>Scadenza</th><th>Percorso</th><th>Stato</th></tr></thead><tbody>${p.tasks.map(t=>`<tr><td>${escapeHtml(t.code)} — ${escapeHtml(t.title)}<p>${escapeHtml(t.instructions)}</p></td><td>${escapeHtml(lookup('groups',t.assigned_group))}</td><td>${escapeHtml(t.due_date||p.due_date)}</td><td>${escapeHtml(Object.entries(t.transitions||{}).map(([outcome,destinations])=>outcome+' → '+(destinations.join(', ')||'Fine')).join(' · ')||'Fine')}</td><td><span class="activity-status-label">${escapeHtml(t.active===false?'Non raggiunta':({DA_FARE:"Da fare",IN_LAVORAZIONE:"In lavorazione",COMPLETATO:"Completato"})[t.status]||t.status)}</span></td></tr>`).join('')}</tbody></table></div><button type="button" id="cfg-close">Chiudi</button>`;
    $('cfg-close').onclick=()=>$('cfg-dialog').close();$('cfg-dialog').showModal();
  }catch(e){$('cfg-error').textContent=e.message;}
}
async function removeItem(row) {
  if(!confirm(`Eliminare ${row.name||row.display_name||row.label||row.id}?`))return;
  try{await post(`/api/admin/config/${currentEntity}/delete`,{id:row.id});await load();}catch(e){$('cfg-error').textContent=e.message;}
}
$('cfg-new').onclick=()=>openEditor({active:true});
load().catch(e=>{$('cfg-error').textContent=e.message;});
