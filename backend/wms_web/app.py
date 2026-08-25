from __future__ import annotations

import argparse
import base64
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from backend.wms_core.workflow import WorkflowError
from backend.wms_web.service import DEMO_PRACTICE_ID, PracticeService

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

class WMSRequestHandler(BaseHTTPRequestHandler):
    service = PracticeService()

    def do_GET(self) -> None:
        parsed = urlparse(self.path); path = parsed.path
        if path == "/api/health": self._json({"status":"ok"}); return
        if path == "/api/work-queue":
            operator=parse_qs(parsed.query).get("operator",[""])[0]; self._api(lambda:self.service.work_queue(operator)); return
        if path.startswith("/api/evidence/"):
            evidence_id=unquote(path[len("/api/evidence/"):]); disposition=parse_qs(parsed.query).get("disposition",["inline"])[0]
            try:
                item=self.service.evidence_content(evidence_id)
                data=base64.b64decode(item.content_base64) if item.content_base64 else b""
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", item.content_type or "application/octet-stream")
                self.send_header("Content-Disposition", f'{"attachment" if disposition=="attachment" else "inline"}; filename="{item.filename}"')
                self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            except KeyError as error: self._json({"error":str(error.args[0])},HTTPStatus.NOT_FOUND)
            return
        if path.startswith("/api/tasks/"):
            parts=[unquote(x) for x in path[len("/api/tasks/"):].split("/")]; query=parse_qs(parsed.query)
            operator=query.get("operator",[""])[0]; include_context=query.get("context",["0"])[0]=="1"
            if len(parts)==2: self._api(lambda:self.service.task_detail(parts[0],parts[1],operator,include_context))
            else: self._json({"error":"Endpoint inesistente"},HTTPStatus.NOT_FOUND)
            return
        if path.startswith("/api/practices/"):
            self._api(lambda:self.service.get(unquote(path[len("/api/practices/"):]))); return
        self._static(path)

    def do_POST(self) -> None:
        parts=[unquote(x) for x in urlparse(self.path).path.split("/") if x]
        if len(parts)<4 or parts[:2]!=["api","practices"]: self._json({"error":"Endpoint inesistente"},HTTPStatus.NOT_FOUND); return
        practice_id,action=parts[2],parts[3]; body=self._body(); actor=str(body.get("actor") or "operatore web")
        outcome=str(body.get("outcome") or ""); note=str(body.get("note") or ""); attachments=body.get("attachments")
        if not isinstance(attachments,list): attachments=[]
        if action=="tasks" and len(parts)==6 and parts[5]=="progress": self._api(lambda:self.service.save_task_progress(practice_id,parts[4],actor,note,attachments))
        elif action=="tasks" and len(parts)==6 and parts[5]=="complete": self._api(lambda:self.service.complete_task(practice_id,parts[4],actor,outcome or "COMPLETATO",note,attachments))
        elif action=="tasks" and len(parts)==6 and parts[5]=="assign": self._api(lambda:self.service.assign_task(practice_id,parts[4],str(body.get("assignee") or ""),actor))
        elif action=="tasks" and len(parts)==6 and parts[5]=="reopen": self._api(lambda:self.service.reopen_task(practice_id,parts[4],actor,str(body.get("reason") or "")))
        elif action=="validate" and len(parts)==4: self._api(lambda:self.service.validate(practice_id,actor,outcome or "VALIDATA",note,attachments))
        elif action=="close" and len(parts)==4: self._api(lambda:self.service.close(practice_id,actor,outcome or "CHIUSA",note,attachments))
        else: self._json({"error":"Endpoint inesistente"},HTTPStatus.NOT_FOUND)

    def _api(self, operation) -> None:
        try: self._json(operation())
        except KeyError as error: self._json({"error":str(error.args[0])},HTTPStatus.NOT_FOUND)
        except WorkflowError as error: self._json({"error":str(error)},HTTPStatus.CONFLICT)
        except PermissionError as error: self._json({"error":str(error)},HTTPStatus.FORBIDDEN)
    def _body(self):
        try:
            length=int(self.headers.get("Content-Length","0")); return json.loads(self.rfile.read(length)) if length else {}
        except (ValueError,json.JSONDecodeError): return {}
    def _static(self,path):
        relative="index.html" if path in {"/","/index.html"} else path.lstrip("/"); target=(FRONTEND/relative).resolve()
        if FRONTEND not in target.parents or not target.is_file(): self._json({"error":"Risorsa inesistente"},HTTPStatus.NOT_FOUND); return
        data=target.read_bytes(); self.send_response(HTTPStatus.OK); self.send_header("Content-Type",mimetypes.guess_type(target.name)[0] or "application/octet-stream"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def _json(self,payload,status=HTTPStatus.OK):
        data=json.dumps(payload,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)

def create_server(host="127.0.0.1",port=8000): return ThreadingHTTPServer((host,port),WMSRequestHandler)
def main():
    parser=argparse.ArgumentParser(description="Web app locale WMS"); parser.add_argument("--host",default="127.0.0.1"); parser.add_argument("--port",type=int,default=8000); args=parser.parse_args(); server=create_server(args.host,args.port)
    print(f"WMS disponibile su http://{args.host}:{server.server_port}/ (pratica {DEMO_PRACTICE_ID})")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=="__main__": main()
