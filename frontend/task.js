const p=new URLSearchParams(location.search),operator=p.get("operator"),practice=p.get("practice"),task=p.get("task");
document.querySelector("#identity").textContent=`OPERATORE · ${operator}`;
document.querySelector("#back").href=`/queue.html?operator=${encodeURIComponent(operator)}`;
const box=document.querySelector("#message");
function fail(error){box.textContent=error.message;box.hidden=false}
function escapeHtml(value){const node=document.createElement("span");node.textContent=value??"";return node.innerHTML}
function evidenceHtml(item){
  const meta=[item.document_type,item.description,item.actor,item.created_at?new Date(item.created_at).toLocaleString("it-IT"):""].filter(Boolean).join(" · ");
  const preview=item.content_type&&item.content_type.startsWith("image/")?`<img src="${item.preview_url}" alt="Anteprima ${escapeHtml(item.filename)}">`:`<span>${escapeHtml(meta||item.content_type||"Documento")}</span>`;
  return `<span class="doc-preview"><a class="doc-icon" href="${item.preview_url}" target="_blank" title="${escapeHtml(meta)}">📄 ${escapeHtml(item.filename)}</a><span class="doc-popover">${preview}<small>${escapeHtml(meta)}</small><a href="${item.download_url}">Scarica</a></span></span>`;
}
function resultHtml(result){
  const docs=(result.evidence||[]).map(evidenceHtml).join("");
  return `<li><strong>${escapeHtml(result.related_task_code||result.action)} · ${escapeHtml(result.outcome)}</strong>${result.note?`<br>${escapeHtml(result.note)}`:""}<br><small>${escapeHtml(result.actor)} · ${result.timestamp?new Date(result.timestamp).toLocaleString("it-IT"):""}</small>${docs?`<div class="evidence-list">${docs}</div>`:""}</li>`;
}
async function load(){
  const response=await fetch(`/api/tasks/${practice}/${task}?operator=${encodeURIComponent(operator)}&context=1`),data=await response.json();
  if(!response.ok)throw new Error(data.error);
  const history=(data.previous_results||[]).map(resultHtml).join("");
  document.querySelector("#detail").innerHTML=`<p class="eyebrow">${data.practice.type} · ${data.practice.id}</p><h1>${escapeHtml(data.task.title)}</h1><p>Cliente <strong>${escapeHtml(data.practice.client_id)}</strong> · periodo ${data.practice.period_start} / ${data.practice.period_end} · scadenza ${data.practice.due_date}</p><p>Dipendenze esplicite: <strong>${data.task.depends_on.join(', ')||'nessuna'}</strong></p><section class="instructions"><p class="eyebrow">Istruzioni operative</p><h2>Cosa devi fare</h2><p>${escapeHtml(data.task.instructions||"Nessuna istruzione definita.")}</p></section>${history?`<section class="context"><h2>Materiale e risultati precedenti</h2><ul>${history}</ul></section>`:""}<form id="result-form"><label>Esito<select id="outcome"><option value="POSITIVO">Positivo</option><option value="CON_RILIEVI">Con rilievi</option></select></label><label>Nota<textarea id="note" rows="4" placeholder="Descrivi il risultato del lavoro"></textarea></label><label>Evidenze<input id="attachments" type="file" multiple></label><div id="attachment-meta"></div><small>Puoi allegare più documenti; massimo 5 MB per documento. Per ogni file puoi indicare descrizione e tipo.</small><button id="complete" ${data.task.status==='COMPLETATO'?'disabled':''}>${data.task.status==='COMPLETATO'?'Completata':'Registra risultato e completa'}</button></form>`;
  document.querySelector("#attachments").addEventListener("change",renderAttachmentMeta);
  document.querySelector("#result-form").onsubmit=event=>{event.preventDefault();complete().catch(fail)};
}
function renderAttachmentMeta(){
  const files=[...document.querySelector("#attachments").files];
  document.querySelector("#attachment-meta").innerHTML=files.map((file,i)=>`<div class="attachment-meta"><strong>${escapeHtml(file.name)}</strong><label>Descrizione<input data-description="${i}" type="text" placeholder="Descrizione o nota del documento"></label><label>Tipo documento<input data-document-type="${i}" type="text" value="DOCUMENTO"></label></div>`).join("");
}
function readFile(file){return new Promise((resolve,reject)=>{if(file.size>5*1024*1024){reject(new Error(`${file.name}: dimensione superiore a 5 MB`));return}const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",",2)[1]||"");reader.onerror=()=>reject(new Error(`Impossibile leggere ${file.name}`));reader.readAsDataURL(file)})}
async function complete(){
  const files=[...document.querySelector("#attachments").files];
  const attachments=[];
  for(let i=0;i<files.length;i++)attachments.push({filename:files[i].name,content_type:files[i].type||"application/octet-stream",description:document.querySelector(`[data-description="${i}"]`)?.value||"",document_type:document.querySelector(`[data-document-type="${i}"]`)?.value||"DOCUMENTO",content_base64:await readFile(files[i])});
  const response=await fetch(`/api/practices/${practice}/tasks/${task}/complete`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor:operator,outcome:document.querySelector("#outcome").value,note:document.querySelector("#note").value,attachments})}),data=await response.json();
  if(!response.ok)throw new Error(data.error);
  location.href=document.querySelector("#back").href;
}
load().catch(fail);
