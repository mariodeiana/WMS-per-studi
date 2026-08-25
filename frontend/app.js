const id = "P-2026-LIPE-001";
const $ = (selector) => document.querySelector(selector);
const labels = {DA_FARE:"Da fare",IN_LAVORAZIONE:"In lavorazione",COMPLETATA:"Completata",DA_VALIDARE:"Da validare",VALIDATA:"Validata",CHIUSA:"Chiusa"};
const italianDate = (value) => new Intl.DateTimeFormat("it-IT", {day:"2-digit",month:"short",year:"numeric"}).format(new Date(`${value}T00:00:00`));
async function request(path, options) { const response=await fetch(path,options); const data=await response.json(); if(!response.ok) throw new Error(data.error||"Operazione non riuscita"); return data; }
function render(practice) {
  $("#practice-id").textContent=practice.id; $("#client").textContent=practice.client_id; $("#due").textContent=italianDate(practice.due_date);
  $("#manager").textContent=practice.roles.manager; $("#validator").textContent=practice.roles.validator;
  $("#period").textContent=`${italianDate(practice.period_start)} – ${italianDate(practice.period_end)}`; $("#status").textContent=labels[practice.status];
  $("#progress").textContent=`${practice.progress.completed} / ${practice.progress.total}`; $("#bar").style.width=`${100*practice.progress.completed/practice.progress.total}%`;
  const canReopen=!["VALIDATA","CHIUSA"].includes(practice.status);
  $("#tasks").innerHTML=practice.tasks.map(task=>`<div class="task ${task.status==='COMPLETATO'?'done':''}"><span class="check">${task.status==='COMPLETATO'?'✓':''}</span><div><div class="task-code">${task.code} · ${labels[task.status]}</div><div class="task-title">${task.title}</div><small>Assegnato a <strong>${task.assignee}</strong>${task.completed_by?` · completato da <strong>${task.completed_by}</strong>`:''}${task.depends_on.length?` · dipende da ${task.depends_on.join(', ')}`:' · nessuna dipendenza'}</small></div><div>${task.status!=='COMPLETATO'?`<select data-assignee="${task.code}"><option ${task.assignee==='anna.operatore'?'selected':''}>anna.operatore</option><option ${task.assignee==='luca.operatore'?'selected':''}>luca.operatore</option></select>`:''}${task.status==='COMPLETATO'&&canReopen?`<button class="reopen" data-reopen="${task.code}">Riapri</button>`:''}</div></div>`).join("");
  document.querySelectorAll("[data-assignee]").forEach(select=>select.onchange=()=>assign(select.dataset.assignee,select.value));
  document.querySelectorAll("[data-reopen]").forEach(button=>button.onclick=()=>act(`/tasks/${button.dataset.reopen}/reopen`,"marta.manager"));
  $("#close").disabled=practice.status!=="VALIDATA";
  $("#results").innerHTML=practice.results.length?practice.results.map(result=>`<div class="result"><strong>${result.related_task_code||result.action} · ${result.outcome}</strong><p>${result.note||"Nessuna nota"}</p><small>${result.actor} (${result.actor_role}) · ${new Date(result.timestamp).toLocaleString('it-IT')}</small></div>`).join(""):"<p>Nessun risultato registrato.</p>";
  $("#evidence").innerHTML=practice.evidence.map(item=>`<span class="evidence">${item.filename} · ${item.source}</span>`).join("");
  $("#audit").innerHTML=practice.audit.slice(0,14).map(event=>`<div class="event"><strong>${event.event_type.replaceAll('_',' ')}</strong><span>${event.actor} · ${new Date(event.at).toLocaleString('it-IT')}</span></div>`).join("");
}
async function act(path, actor) { try { $("#message").hidden=true; render(await request(`/api/practices/${id}${path}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor})})); } catch(error) { $("#message").textContent=error.message; $("#message").hidden=false; } }
async function assign(task, assignee) { try { render(await request(`/api/practices/${id}/tasks/${task}/assign`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor:"marta.manager",assignee})})); } catch(error) { $("#message").textContent=error.message; $("#message").hidden=false; } }
$("#close").onclick=async()=>{const attachments=[...$("#close-files").files].map(file=>({filename:file.name,content_type:file.type||"application/octet-stream"}));try{$("#message").hidden=true;render(await request(`/api/practices/${id}/close`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor:"marta.manager",outcome:$("#close-outcome").value,note:$("#close-note").value,attachments})}))}catch(error){$("#message").textContent=error.message;$("#message").hidden=false}};
request(`/api/practices/${id}`).then(render).catch(error=>{ $("#message").textContent=error.message; $("#message").hidden=false; });
