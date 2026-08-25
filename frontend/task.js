const p=new URLSearchParams(location.search),operator=p.get("operator"),practice=p.get("practice"),task=p.get("task");
document.querySelector("#identity").textContent=`OPERATORE · ${operator}`;
document.querySelector("#back").href=`/queue.html?operator=${encodeURIComponent(operator)}`;
const box=document.querySelector("#message");
const selectedAttachments=[];
function fail(error){box.textContent=error.message;box.hidden=false;box.scrollIntoView({block:"nearest"})}
function escapeHtml(value){const node=document.createElement("span");node.textContent=value??"";return node.innerHTML}
function evidenceHtml(item){
  const meta=[item.document_type,item.description,item.actor,item.created_at?new Date(item.created_at).toLocaleString("it-IT"):""].filter(Boolean).join(" · ");
  const preview=item.content_type&&item.content_type.startsWith("image/")?`<img src="${item.preview_url}" alt="Anteprima ${escapeHtml(item.filename)}">`:`<span>${escapeHtml(meta||item.content_type||"Documento")}</span>`;
  return `<span class="doc-preview"><a class="doc-icon" href="${item.preview_url}" target="_blank" title="${escapeHtml(meta)}">📄 ${escapeHtml(item.filename)}</a><span class="doc-popover">${preview}<small>${escapeHtml(meta)}</small><a href="${item.download_url}">Scarica</a></span></span>`;
}
function resultHtml(result){
  const docs=(result.evidence||[]).map(evidenceHtml).join("");
  const taskLabel=[result.related_task_code||result.action,result.related_task_title].filter(Boolean).join(" · ");
  return `<li><strong>${escapeHtml(taskLabel)} · ${escapeHtml(result.outcome)}</strong>${result.note?`<br>${escapeHtml(result.note)}`:""}<br><small>${escapeHtml(result.actor)} · ${result.timestamp?new Date(result.timestamp).toLocaleString("it-IT"):""}</small>${docs?`<div class="evidence-list">${docs}</div>`:""}</li>`;
}
async function load(){
  const response=await fetch(`/api/tasks/${practice}/${task}?operator=${encodeURIComponent(operator)}&context=1`),data=await response.json();
  if(!response.ok)throw new Error(data.error);
  const history=(data.previous_results||[]).map(resultHtml).join("");
  document.querySelector("#detail").innerHTML=`<p class="eyebrow">${data.practice.type} · ${data.practice.id}</p><h1>${escapeHtml(data.task.title)}</h1><p>Cliente <strong>${escapeHtml(data.practice.client_id)}</strong> · periodo ${data.practice.period_start} / ${data.practice.period_end} · scadenza ${data.practice.due_date}</p><p>Dipendenze esplicite: <strong>${data.task.depends_on.join(', ')||'nessuna'}</strong></p><section class="instructions"><p class="eyebrow">Istruzioni operative</p><h2>Cosa devi fare</h2><p>${escapeHtml(data.task.instructions||"Nessuna istruzione definita.")}</p></section>${history?`<section class="context"><h2>Materiale e risultati precedenti</h2><ul>${history}</ul></section>`:""}<form id="result-form"><label>Esito<select id="outcome" required><option value="" selected>Seleziona esito…</option><option value="POSITIVO">Positivo</option><option value="CON_RILIEVI">Con rilievi</option></select></label><label>Nota<textarea id="note" rows="4" placeholder="Descrivi il risultato del lavoro"></textarea></label><fieldset class="attachments-fieldset"><legend>Evidenze</legend><input id="attachment-picker" class="file-picker-hidden" type="file" multiple><div id="attachment-meta"></div><small>Puoi aggiungere più documenti. Massimo 5 MB per documento. Descrizione consigliata; tipo documento opzionale.</small></fieldset><button id="complete" type="button" ${data.task.status==='COMPLETATO'?'disabled':''}>${data.task.status==='COMPLETATO'?'Completata':'Registra risultato e completa'}</button></form>`;
  const picker=document.querySelector("#attachment-picker");
  picker.addEventListener("change",()=>{addSelectedFiles([...picker.files]);picker.value=""});
  document.querySelector("#result-form").addEventListener("submit",event=>event.preventDefault());
  document.querySelector("#result-form").addEventListener("keydown",event=>{if(event.key==="Enter"&&event.target.tagName!=="TEXTAREA")event.preventDefault()});
  document.querySelector("#complete").addEventListener("click",()=>complete().catch(fail));
  renderAttachmentMeta();
}
function addSelectedFiles(files){
  for(const file of files){
    if(file.size>5*1024*1024){fail(new Error(`${file.name}: dimensione superiore a 5 MB`));continue}
    selectedAttachments.push({file,description:"",documentType:""});
  }
  renderAttachmentMeta();
}
function renderAttachmentMeta(){
  const container=document.querySelector("#attachment-meta");
  const rows=selectedAttachments.map((item,i)=>`<div class="attachment-row"><div class="attachment-file">📄 ${escapeHtml(item.file.name)}</div><input aria-label="Descrizione ${escapeHtml(item.file.name)}" data-description="${i}" type="text" value="${escapeHtml(item.description)}" placeholder="Descrizione"><input aria-label="Tipo documento ${escapeHtml(item.file.name)}" data-document-type="${i}" type="text" value="${escapeHtml(item.documentType)}" placeholder="Tipo documento"><button type="button" class="icon-button" data-remove="${i}" title="Elimina l'allegato" aria-label="Elimina l'allegato ${escapeHtml(item.file.name)}">−</button></div>`).join("");
  const addRow=`<div class="attachment-row attachment-add-row"><button type="button" class="icon-button" id="add-attachment-row" title="Aggiungi allegato" aria-label="Aggiungi allegato">+</button><span></span><span></span><span></span></div>`;
  container.innerHTML=`<div class="attachment-table"><div class="attachment-head"><span>Documento</span><span>Descrizione</span><span>Tipo documento</span><span></span></div>${rows}${addRow}</div>`;
  container.querySelectorAll("[data-description]").forEach(input=>input.addEventListener("input",()=>{selectedAttachments[Number(input.dataset.description)].description=input.value}));
  container.querySelectorAll("[data-document-type]").forEach(input=>input.addEventListener("input",()=>{selectedAttachments[Number(input.dataset.documentType)].documentType=input.value}));
  container.querySelectorAll("[data-remove]").forEach(button=>button.addEventListener("click",()=>{selectedAttachments.splice(Number(button.dataset.remove),1);renderAttachmentMeta()}));
  document.querySelector("#add-attachment-row").addEventListener("click",()=>document.querySelector("#attachment-picker").click());
}
function readFile(file){return new Promise((resolve,reject)=>{if(file.size>5*1024*1024){reject(new Error(`${file.name}: dimensione superiore a 5 MB`));return}const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",",2)[1]||"");reader.onerror=()=>reject(new Error(`Impossibile leggere ${file.name}`));reader.readAsDataURL(file)})}
async function complete(){
  box.hidden=true;
  const outcome=document.querySelector("#outcome").value;
  if(!outcome){fail(new Error("Seleziona l'esito prima di completare il task."));document.querySelector("#outcome").focus();return}
  const attachments=[];
  for(const item of selectedAttachments)attachments.push({filename:item.file.name,content_type:item.file.type||"application/octet-stream",description:item.description,document_type:item.documentType||"DOCUMENTO",content_base64:await readFile(item.file)});
  const response=await fetch(`/api/practices/${practice}/tasks/${task}/complete`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actor:operator,outcome,note:document.querySelector("#note").value,attachments})}),data=await response.json();
  if(!response.ok)throw new Error(data.error);
  location.href=document.querySelector("#back").href;
}
load().catch(fail);
