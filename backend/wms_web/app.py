from __future__ import annotations
import argparse,base64,json,mimetypes
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,unquote,urlparse
from backend.wms_core.models import NonConformity
from backend.wms_core.workflow import WorkflowError,define_corrective_action
from backend.wms_web.service import DEMO_PRACTICE_ID,PracticeService
ROOT=Path(__file__).resolve().parents[2];FRONTEND=ROOT/"frontend";DEMO_STATE=ROOT/".wms-demo-state.pkl"
class WMSRequestHandler(BaseHTTPRequestHandler):
 service=PracticeService(state_path=DEMO_STATE,rich_demo=True);debug_mode=False
 def do_GET(self):
  parsed=urlparse(self.path);path=parsed.path;query=parse_qs(parsed.query)
  if path=="/api/health":self._json({"status":"ok"});return
  if path=="/api/runtime":self._json({"debug":bool(self.debug_mode)});return
  if path=="/api/manager/practices":self._api(lambda:self.service.manager_practices(query.get("actor",[""])[0]));return
  if path=="/api/validation-queue":self._api(lambda:self.service.validation_queue(query.get("actor",[""])[0]));return
  if path=="/api/validation-history":self._api(lambda:self.service.validation_history(query.get("actor",[""])[0]));return
  if path=="/api/work-queue":self._api(lambda:self.service.work_queue(query.get("operator",[""])[0]));return
  if path.startswith("/api/evidence/"):
   eid=unquote(path[len("/api/evidence/"):]);disp=query.get("disposition",["inline"])[0]
   try:
    item=self.service.evidence_content(eid);data=base64.b64decode(item.content_base64) if item.content_base64 else b"";self.send_response(200);self.send_header("Content-Type",item.content_type or "application/octet-stream");self.send_header("Content-Disposition",f'{"attachment" if disp=="attachment" else "inline"}; filename="{item.filename}"');self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
   except KeyError as e:self._json({"error":str(e.args[0])},404)
   return
  if path.startswith("/api/tasks/"):
   parts=[unquote(x) for x in path[len("/api/tasks/"):].split("/")];operator=query.get("operator",[""])[0];context=query.get("context",["0"])[0]=="1"
   if len(parts)==2:self._api(lambda:self.service.task_detail(parts[0],parts[1],operator,context))
   else:self._json({"error":"Endpoint inesistente"},404)
   return
  if path.startswith("/api/practices/"):self._api(lambda:self.service.get(unquote(path[len("/api/practices/"):])));return
  self._static(path)
 def do_POST(self):
  parts=[unquote(x) for x in urlparse(self.path).path.split("/") if x]
  if len(parts)<4 or parts[:2]!=["api","practices"]:self._json({"error":"Endpoint inesistente"},404);return
  pid,action=parts[2],parts[3];body=self._body();actor=str(body.get("actor") or "operatore web");outcome=str(body.get("outcome") or "");note=str(body.get("note") or "");attachments=body.get("attachments") if isinstance(body.get("attachments"),list) else []
  if action=="tasks" and len(parts)==6 and parts[5]=="progress":self._api(lambda:self.service.save_task_progress(pid,parts[4],actor,note,attachments))
  elif action=="tasks" and len(parts)==6 and parts[5]=="complete":self._api(lambda:self.service.complete_task(pid,parts[4],actor,outcome or "COMPLETATO",note,attachments))
  elif action=="tasks" and len(parts)==6 and parts[5]=="assign":self._api(lambda:self.service.assign_task(pid,parts[4],str(body.get("assignee") or ""),actor))
  elif action=="tasks" and len(parts)==6 and parts[5]=="reopen":self._api(lambda:self.service.reopen_task(pid,parts[4],actor,str(body.get("reason") or "")))
  elif action=="corrective-action" and len(parts)==4:self._api(lambda:self._corrective_action(pid,actor,body))
  elif action=="validate" and len(parts)==4:self._api(lambda:self.service.validate(pid,actor,outcome or "VALIDATA",note,attachments))
  elif action=="close" and len(parts)==4:self._api(lambda:self.service.close(pid,actor,outcome or "CHIUSA",note,attachments))
  else:self._json({"error":"Endpoint inesistente"},404)
 def _corrective_action(self,pid,actor,body):
  with self.service._lock:
   practice=self.service._find(pid);define_corrective_action(practice,actor,self.service._role(actor),body.get("task_codes") or [],str(body.get("instruction") or ""));self.service._persist();return self.service.get(pid)
 def _api(self,op):
  try:self._json(op())
  except KeyError as e:self._json({"error":str(e.args[0])},404)
  except WorkflowError as e:self._json({"error":str(e)},409)
  except PermissionError as e:self._json({"error":str(e)},403)
 def _body(self):
  try:l=int(self.headers.get("Content-Length","0"));return json.loads(self.rfile.read(l)) if l else {}
  except (ValueError,json.JSONDecodeError):return {}
 def _static(self,path):
  relative="index.html" if path in {"/","/index.html"} else path.lstrip("/");target=(FRONTEND/relative).resolve()
  if FRONTEND not in target.parents or not target.is_file():self._json({"error":"Risorsa inesistente"},404);return
  data=target.read_bytes();self.send_response(200);self.send_header("Content-Type",mimetypes.guess_type(target.name)[0] or "application/octet-stream");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
 def _json(self,payload,status=200):
  data=json.dumps(payload,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
def _migrate_nonconformities(service):
 changed=False
 with service._lock:
  for p in service._practices.values():
   if not hasattr(p,'nonconformities'):p.nonconformities=[]
   if p.status.value!='NON_VALIDATA' or p.nonconformities:continue
   validation=next((r for r in reversed(p.results) if r.action=='VALIDATION' and r.outcome=='NON_VALIDATA'),None)
   reason=validation.note if validation else 'Non conformità rilevata in validazione'
   actor=validation.actor if validation else 'valeria.validatore';nc=NonConformity(id='NC-0001',reason=reason,opened_by=actor);p.nonconformities.append(nc);p.record('NONCONFORMITY_OPENED',actor,nc_id=nc.id,reason=reason,source='VALIDATION',migrated=True);changed=True
  if changed:service._persist()
def create_server(host="127.0.0.1",port=8000,debug=False):_migrate_nonconformities(WMSRequestHandler.service);WMSRequestHandler.debug_mode=debug;return ThreadingHTTPServer((host,port),WMSRequestHandler)
def main():
 parser=argparse.ArgumentParser(description="Web app locale WMS");parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8000);parser.add_argument("--debug",action="store_true");args=parser.parse_args();server=create_server(args.host,args.port,args.debug);print(f"WMS disponibile su http://{args.host}:{server.server_port}/ (pratica {DEMO_PRACTICE_ID})");print(f"Stato demo persistente: {DEMO_STATE}");print(f"Modalità debug: {'ON' if args.debug else 'OFF'}")
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=="__main__":main()
