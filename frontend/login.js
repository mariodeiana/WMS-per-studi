const form=document.getElementById('login-form');const message=document.getElementById('login-message');
function homeFor(role){if(role==='MANAGER')return '/';if(role==='VALIDATORE')return '/validation-list.html';return '/queue.html';}
(async()=>{const r=await fetch('/api/session');if(r.ok){const s=await r.json();location.replace(homeFor(s.active.role));}})();
form.addEventListener('submit',async event=>{event.preventDefault();message.hidden=true;const data=Object.fromEntries(new FormData(form));const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const payload=await r.json();if(!r.ok){message.textContent=payload.error||'Accesso non riuscito';message.hidden=false;return;}location.replace(homeFor(payload.active.role));});
