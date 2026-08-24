const id = "P-2026-LIPE-001";
const $ = (selector) => document.querySelector(selector);
const labels = {DA_FARE:"Da fare",IN_LAVORAZIONE:"In lavorazione",COMPLETATA:"Completata",DA_VALIDARE:"Da validare",VALIDATA:"Validata",CHIUSA:"Chiusa"};

function italianDate(value) { return new Intl.DateTimeFormat("it-IT", {day:"2-digit",month:"short",year:"numeric"}).format(new Date(`${value}T00:00:00`)); }
async function request(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Operazione non riuscita");
  return data;
}
function render(practice) {
  $("#practice-id").textContent=practice.id; $("#client").textContent=practice.client_id; $("#due").textContent=italianDate(practice.due_date);
  $("#period").textContent=`${italianDate(practice.period_start)} – ${italianDate(practice.period_end)}`; $("#status").textContent=labels[practice.status];
  $("#progress").textContent=`${practice.progress.completed} / ${practice.progress.total}`; $("#bar").style.width=`${100*practice.progress.completed/practice.progress.total}%`;
  $("#tasks").innerHTML=practice.tasks.map(task=>`<div class="task ${task.status==='COMPLETATO'?'done':''}"><span class="check">${task.status==='COMPLETATO'?'✓':''}</span><div><div class="task-code">${task.code}</div><div class="task-title">${task.title}</div></div>${task.status!=='COMPLETATO'?`<button data-task="${task.code}">Completa</button>`:''}</div>`).join("");
  document.querySelectorAll("[data-task]").forEach(button=>button.onclick=()=>act(`/tasks/${button.dataset.task}/complete`,"operatore"));
  $("#validate").disabled=practice.status!=="DA_VALIDARE"; $("#close").disabled=practice.status!=="VALIDATA";
  $("#audit").innerHTML=practice.audit.slice(0,8).map(event=>`<div class="event"><strong>${event.event_type.replaceAll('_',' ')}</strong><span>${event.actor} · ${new Date(event.at).toLocaleString('it-IT')}</span></div>`).join("");
}
async function act(path, actor, actorRole="OPERATORE") { try { $("#message").hidden=true; render(await request(`/api/practices/${id}${path}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor,actor_role:actorRole})})); } catch(error) { $("#message").textContent=error.message; $("#message").hidden=false; } }
$("#validate").onclick=()=>act("/validate","responsabile","RESPONSABILE"); $("#close").onclick=()=>act("/close","responsabile","RESPONSABILE");
request(`/api/practices/${id}`).then(render).catch(error=>{ $("#message").textContent=error.message; $("#message").hidden=false; });
