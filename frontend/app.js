const id = "P-2026-LIPE-001";
const $ = (selector) => document.querySelector(selector);
const labels = {DA_FARE:"Da fare",IN_LAVORAZIONE:"In corso",COMPLETATO:"Completato",COMPLETATA:"Completata",DA_VALIDARE:"Da validare",VALIDATA:"Validata",CHIUSA:"Chiusa"};
const italianDate = (value) => new Intl.DateTimeFormat("it-IT", {day:"2-digit",month:"short",year:"numeric"}).format(new Date(`${value}T00:00:00`));
async function request(path, options) { const response=await fetch(path,options); const data=await response.json(); if(!response.ok) throw new Error(data.error||"Operazione non riuscita"); return data; }
function esc(value){const n=document.createElement("span");n.textContent=value??"";return n.innerHTML}
function evidenceHtml(item){const meta=[item.document_type,item.description,item.actor,item.created_at?new Date(item.created_at).toLocaleString('it-IT'):""].filter(Boolean).join(" · ");return `<span class="doc-preview"><a class="doc-icon" href="${item.preview_url}" target="_blank" title="${esc(meta)}">📄 ${esc(item.filename)}</a><span class="doc-popover"><span>${esc(meta||item.content_type||"Documento")}</span><a href="${item.preview_url}" target="_blank">Apri anteprima</a></span></span>`}
function completionClass(result){if(!result)return "";return result.outcome==="CON_RILIEVI"||String(result.outcome).includes("RILIEVI")?"completed-warning":"completed-ok"}
function render(practice) {
  $("#practice-id").textContent=practice.id; $("#client").textContent=practice.client_id; $("#due").textContent=italianDate(practice.due_date);
  $("#manager").textContent=practice.roles.manager; $("#validator").textContent=practice.roles.validator;
  $("#period").textContent=`${italianDate(practice.period_start)} – ${italianDate(practice.period_end)}`; $("#status").textContent=labels[practice.status]||practice.status;
  $("#progress").textContent=`${practice.progress.completed} / ${practice.progress.total}`; $("#bar").style.width=`${100*practice.progress.completed/practice.progress.total}%`;
  const canReopen=!["VALIDATA","CHIUSA"].includes(practice.status);
  const resultByTask=Object.fromEntries(practice.results.filter(r=>r.related_task_code).map(r=>[r.related_task_code,r]));
  $("#tasks").innerHTML=practice.tasks.map(task=>{
    const result=resultByTask[task.code];
    const done=task.status==='COMPLETATO';
    const title=done?`<a class="task-open-link" href="/manager-task.html?practice=${encodeURIComponent(practice.id)}&task=${encodeURIComponent(task.code)}">${esc(task.title)}</a>`:esc(task.title);
    const work=task.status==='IN_LAVORAZIONE'&&task.work_note?` · nota di lavoro: ${esc(task.work_note)}`:"";
    const reopen=task.reopen_reason?` · riaperto: ${esc(task.reopen_reason)}`:"";
    return `<div class="task ${done?'done':''} ${done?completionClass(result):task.status==='IN_LAVORAZIONE'?'in-progress':''}"><span class="check">${done?'✓':task.status==='IN_LAVORAZIONE'?'…':''}</span><div><div class="task-code">${task.code} · ${labels[task.status]||task.status}</div><div class="task-title">${title}</div><small>Assegnato a <strong>${task.assignee}</strong>${task.completed_by?` · completato da <strong>${task.completed_by}</strong>`:''}${task.depends_on.length?` · dipende da ${task.depends_on.join(', ')}`:' · nessuna dipendenza'}${work}${reopen}</small></div><div>${!done?`<select data-assignee="${task.code}"><option ${task.assignee==='anna.operatore'?'selected':''}>anna.operatore</option><option ${task.assignee==='luca.operatore'?'selected':''}>luca.operatore</option></select>`:''}${done&&canReopen?`<button class="reopen" data-reopen="${task.code}">Riapri</button>`:''}</div></div>`;
  }).join("");
  document.querySelectorAll("[data-assignee]").forEach(select=>select.onchange=()=>assign(select.dataset.assignee,select.value));
  document.querySelectorAll("[data-reopen]").forEach(button=>button.onclick=()=>reopenTask(button.dataset.reopen));
  $("#close").disabled=practice.status!=="VALIDATA";
  const evidenceById=Object.fromEntries(practice.evidence.map(item=>[item.id,item]));
  $("#results").innerHTML=practice.results.length?practice.results.map(result=>`<div class="result"><strong>${result.related_task_code||result.action} · ${esc(result.outcome)}</strong><p>${esc(result.note||"Nessuna nota")}</p><small>${esc(result.actor)} (${result.actor_role}) · ${new Date(result.timestamp).toLocaleString('it-IT')}</small><div class="evidence-list">${result.evidence_ids.map(eid=>evidenceById[eid]?evidenceHtml(evidenceById[eid]):"").join("")}</div></div>`).join(""):"<p>Nessun risultato registrato.</p>";
  $("#evidence").innerHTML=practice.evidence.length?practice.evidence.map(evidenceHtml).join(""):"<p>Nessuna evidenza.</p>";
  $("#audit").innerHTML=practice.audit.slice(0,14).map(event=>`<div class="event"><strong>${event.event_type.replaceAll('_',' ')}</strong><span>${event.actor} · ${new Date(event.at).toLocaleString('it-IT')}</span></div>`).join("");
}
async function reopenTask(task){const reason=prompt("Motivazione della riapertura del task:");if(reason===null)return;if(!reason.trim()){alert("La motivazione è obbligatoria.");return}try{$("#message").hidden=true;render(await request(`/api/practices/${id}/tasks/${task}/reopen`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor:"marta.manager",reason:reason.trim()})}))}catch(error){$("#message").textContent=error.message;$("#message").hidden=false}}
async function act(path, actor) { try { $("#message").hidden=true; render(await request(`/api/practices/${id}${path}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor})})); } catch(error) { $("#message").textContent=error.message; $("#message").hidden=false; } }
async function assign(task, assignee) { try { render(await request(`/api/practices/${id}/tasks/${task}/assign`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor:"marta.manager",assignee})})); } catch(error) { $("#message").textContent=error.message; $("#message").hidden=false; } }
$("#close").onclick=async()=>{const attachments=[];try{$("#message").hidden=true;render(await request(`/api/practices/${id}/close`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor:"marta.manager",outcome:$("#close-outcome").value,note:$("#close-note").value,attachments})}))}catch(error){$("#message").textContent=error.message;$("#message").hidden=false}};
request(`/api/practices/${id}`).then(render).catch(error=>{ $("#message").textContent=error.message; $("#message").hidden=false; });
