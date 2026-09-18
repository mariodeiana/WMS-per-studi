(()=>{
 const code=document.body.dataset.interfaceCode;
 fetch('/api/runtime')
  .then(r=>r.ok?r.json():null)
  .then(runtime=>{
   if(!runtime)return;

   const environment=runtime.environment||'DEV';
   document.title=`${document.title} · ${environment}`;

   const topbar=document.querySelector('.topbar');
   let badge=document.querySelector('.wms-env-badge');
   if(!badge && topbar){
    badge=document.createElement('span');
    badge.className='wms-env-badge';
    topbar.prepend(badge);
   }
   if(badge)badge.textContent=environment;

   if(runtime.debug && code){
    const badge=document.createElement('span');
    badge.className='interface-code';
    badge.textContent=code;
    badge.title='Codice interfaccia · modalità debug';
    topbar?.appendChild(badge);
   }
  })
  .catch(()=>{});
})();
