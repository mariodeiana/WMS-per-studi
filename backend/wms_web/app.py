from __future__ import annotations
import argparse,base64,json,mimetypes
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,unquote,urlparse
from backend.wms_core.models import NonConformity,UserRole
from backend.wms_core.workflow import WorkflowError,define_corrective_action
from backend.wms_web.auth import AUTH
from backend.wms_web.organization_service import OrganizationalPracticeService
from backend.wms_web.service import DEMO_PRACTICE_ID
ROOT=Path(__file__).resolve().parents[2];FRONTEND=ROOT/"frontend";DEMO_STATE=ROOT/".wms-demo-state.pkl"
class WMSRequestHandler(BaseHTTPRequestHandler):
 service=OrganizationalPracticeService(state_path=DEMO_STATE,rich_demo=True);debug_mode=False
 def _token(self):
  cookie=SimpleCookie(self.headers.get("Cookie", ""));item=cookie.get("WMSSESSION");return item.value if item else None
 def _session(self):return AUTH.describe(self._token())
 def _principal(self):return AUTH.principal(self._token())
 def _require_session(self):
  try:return self._session()
  except PermissionError:return None
 def do_GET(self):
  parsed=urlparse(self.path);path=parsed.path;query=parse_qs(parsed.query)
  if path=="/api/health":self._json({"status":"ok"});return
  if path=="/api/runtime":self._json({"debug":bool(self.debug_mode)});return
  if path=="/api/session":
   try:self._json(self._session())
   except PermissionError as e:self._json({"error":str(e)},401)
   return
  if path.startswith("/api/") and not self._require_session():self._json({"error":"Sessione non autenticata"},401);return
  if path=="/api/manager/practices":self._api(lambda:self.service.manager_practices_for(self._principal()));return
  if path=="/api/validation-queue":self._api(lambda:self.service.validation_queue_for(self._principal()));return
  if path=="/api/validation-history":self._api(lambda:self.service.validation_history_for(self._principal()));return
  if path=="/api/work-queue":self._api(lambda:self.service.work_queue_for(self._principal()));return
  if path.startswith("/api/evidence/"):
   eid=unquote(path[len("/api/evidence/"):]);disp=query.get("disposition",["inline"])[0]
   try:
    item=self.service.evidence_content(eid);data=base64.b64decode(item.content_base64) if item.content_base64 else b"";self.send_response(200);self.send_header("Content-Type",item.content_type or "application/octet-stream");self.send_header("Content-Disposition",f'{"attachment" if disp=="attachment" else "inline"}; filename="{item.filename}"');self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
   except KeyError as e:self._json({"error":str(e.args[0])},404)
   return
  if path.startswith("/api/tasks/"):
   parts=[unquote(x) for x in path[len("/api/tasks/"):].split("/")];context=query.get("context",["0"])[0]=="1"
   if len(parts)==2:self._api(lambda:self.service.task_detail_for(parts[0],parts[1],self._principal(),context))
   else:self._json({"error":"Endpoint inesistente"},404)
   return
  if path.startswith("/api/practices/"):self._api(lambda:self.service.get_for(unquote(path[len("/api/practices/"):]),self._principal()));return
  if path not in {"/login.html","/login.js","/styles.css"} and path.endswith((".html","/")) and not self._require_session():self._redirect("/login.html");return
  self._static(path)
 def do_POST(self):
  path=urlparse(self.path).path;body=self._body()
  if path=="/api/login":
   try:
    token,session=AUTH.login(str(body.get("username") or ""),str(body.get("password") or ""));self._json(session,200,{"Set-Cookie":f"WMSSESSION={token}; Path=/; HttpOnly; SameSite=Lax"})
   except PermissionError as e:self._json({"error":str(e)},401)
   return
  if path=="/api/logout":AUTH.logout(self._token());self._json({"ok":True},200,{"Set-Cookie":"WMSSESSION=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"});return
  if path=="/api/session/role":
   try:self._json(AUTH.switch(self._token(),str(body.get("membership_id") or "")))
   except PermissionError as e:self._json({"error":str(e)},403)
   return
  if not self._require_session():self._json({"error":"Sessione non autenticata"},401);return
  parts=[unquote(x) for x in path.split("/") if x]
  if len(parts)<4 or parts[:2]!=["api","practices"]:self._json({"error":"Endpoint inesistente"},404);return
  pid,action=parts[2],parts[3];principal=self._principal();outcome=str(body.get("outcome") or "");note=str(body.get("note") or "");attachments=body.get("attachments") if isinstance(body.get("attachments"),list) else []
  if action=="tasks" and len(parts)==6 and parts[5]=="progress":self._api(lambda:self.service.save_task_progress_for(pid,parts[4],principal,note,attachments))
  elif action=="tasks" and len(parts)==6 and parts[5]=="complete":self._api(lambda:self.service.complete_task_for(pid,parts[4],principal,outcome or "COMPLETATO",note,attachments))
  elif action=="tasks" and len(parts)==6 and parts[5]=="assign":self._api(lambda:self.service.assign_group_for(pid,parts[4],str(body.get("group_id") or body.get("assignee") or ""),principal))
  elif action=="tasks" and len(parts)==6 and parts[5]=="reopen":self._api(lambda:self.service.reopen_task_for(pid,parts[4],principal,str(body.get("reason") or "")))
  elif action=="corrective-action" and len(parts)==4:self._api(lambda:self._corrective_action(pid,principal,body))
  elif action=="validate" and len(parts)==4:self._api(lambda:self.service.validate_for(pid,principal,outcome or "VALIDATA",note,attachments))
  elif action=="close" and len(parts)==4:self._api(lambda:self.service.close_for(pid,principal,outcome or "CHIUSA",note,attachments))
  else:self._json({"error":"Endpoint inesistente"},404)
 def _corrective_action(self,pid,principal,body):
  if principal["role"]!="MANAGER":raise PermissionError("Solo un manager può definire una azione correttiva")
  with self.service._lock:
   practice=self.service._find(pid);define_corrective_action(practice,principal["username"],UserRole.MANAGER,body.get("task_codes") or [],str(body.get("instruction") or ""));
   for code in body.get("task_codes") or []:
    task=self.service._find_task(practice,code);task.claimed_by=None;task.assignee=None
   self.service._persist();return self.service.get_for(pid,principal)
 def _api(self,op):
  try:self._json(op())
  except KeyError as e:self._json({"error":str(e.args[0])},404)
  except WorkflowError as e:self._json({"error":str(e)},409)
  except PermissionError as e:self._json({"error":str(e)},403)
 def _body(self):
  try:l=int(self.headers.get("Content-Length","0"));return json.loads(self.rfile.read(l)) if l else {}
  except (ValueError,json.JSONDecodeError):return {}
 def _redirect(self,path):self.send_response(303);self.send_header("Location",path);self.end_headers()
 def _static(self,path):
  relative="index.html" if path in {"/","/index.html"} else path.lstrip("/");target=(FRONTEND/relative).resolve()
  if FRONTEND not in target.parents or not target.is_file():self._json({"error":"Risorsa inesistente"},404);return
  data=target.read_bytes();content_type=mimetypes.guess_type(target.name)[0] or "application/octet-stream"
  if target.suffix==".html" and target.name!="login.html":data=data.replace(b"</body>",b'<script src="/auth-context.js"></script></body>')
  self.send_response(200);self.send_header("Content-Type",content_type);self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
 def _json(self,payload,status=200,headers=None):
  data=json.dumps(payload,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8")
  for key,value in (headers or {}).items():self.send_header(key,value)
  self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
def _migrate_nonconformities(service):
 changed=False
 with service._lock:
  for p in service._practices.values():
   if not hasattr(p,'nonconformities'):p.nonconformities=[]
   if p.status.value!='NON_VALIDATA' or p.nonconformities:continue
   validation=next((r for r in reversed(p.results) if r.action=='VALIDATION' and r.outcome=='NON_VALIDATA'),None);reason=validation.note if validation else 'Non conformità rilevata in validazione';actor=validation.actor if validation else 'sistema';nc=NonConformity(id='NC-0001',reason=reason,opened_by=actor);p.nonconformities.append(nc);p.record('NONCONFORMITY_OPENED',actor,nc_id=nc.id,reason=reason,source='VALIDATION',migrated=True);changed=True
  if changed:service._persist()
def create_server(host="127.0.0.1",port=8000,debug=False):_migrate_nonconformities(WMSRequestHandler.service);WMSRequestHandler.debug_mode=debug;return ThreadingHTTPServer((host,port),WMSRequestHandler)
def main():
 parser=argparse.ArgumentParser(description="Web app locale WMS");parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8000);parser.add_argument("--debug",action="store_true");args=parser.parse_args();server=create_server(args.host,args.port,args.debug);print(f"WMS disponibile su http://{args.host}:{server.server_port}/ (pratica {DEMO_PRACTICE_ID})");print(f"Stato demo persistente: {DEMO_STATE}");print(f"Modalità debug: {'ON' if args.debug else 'OFF'}")
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=="__main__":main()
