from __future__ import annotations

import argparse
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

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._json({"status": "ok"})
            return
        if path == "/api/work-queue":
            operator = parse_qs(parsed.query).get("operator", [""])[0]
            self._api(lambda: self.service.work_queue(operator))
            return
        task_prefix = "/api/tasks/"
        if path.startswith(task_prefix):
            parts = [unquote(part) for part in path[len(task_prefix) :].split("/")]
            operator = parse_qs(parsed.query).get("operator", [""])[0]
            if len(parts) == 2:
                self._api(lambda: self.service.task_detail(parts[0], parts[1], operator))
            else:
                self._json({"error": "Endpoint inesistente"}, HTTPStatus.NOT_FOUND)
            return
        prefix = "/api/practices/"
        if path.startswith(prefix):
            self._api(lambda: self.service.get(unquote(path[len(prefix) :])))
            return
        self._static(path)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parts = [unquote(part) for part in urlparse(self.path).path.split("/") if part]
        if len(parts) < 4 or parts[:2] != ["api", "practices"]:
            self._json({"error": "Endpoint inesistente"}, HTTPStatus.NOT_FOUND)
            return
        practice_id, action = parts[2], parts[3]
        body = self._body()
        actor = str(body.get("actor") or "operatore web")
        if action == "tasks" and len(parts) == 6 and parts[5] == "complete":
            self._api(lambda: self.service.complete_task(practice_id, parts[4], actor))
        elif action == "tasks" and len(parts) == 6 and parts[5] == "assign":
            assignee = str(body.get("assignee") or "")
            self._api(lambda: self.service.assign_task(practice_id, parts[4], assignee, actor))
        elif action == "tasks" and len(parts) == 6 and parts[5] == "reopen":
            self._api(lambda: self.service.reopen_task(practice_id, parts[4], actor))
        elif action == "validate" and len(parts) == 4:
            self._api(lambda: self.service.validate(practice_id, actor))
        elif action == "close" and len(parts) == 4:
            self._api(lambda: self.service.close(practice_id, actor))
        else:
            self._json({"error": "Endpoint inesistente"}, HTTPStatus.NOT_FOUND)

    def _api(self, operation) -> None:
        try:
            self._json(operation())
        except KeyError as error:
            self._json({"error": str(error.args[0])}, HTTPStatus.NOT_FOUND)
        except WorkflowError as error:
            self._json({"error": str(error)}, HTTPStatus.CONFLICT)
        except PermissionError as error:
            self._json({"error": str(error)}, HTTPStatus.FORBIDDEN)

    def _body(self) -> dict[str, object]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length)) if length else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def _static(self, path: str) -> None:
        relative = "index.html" if path in {"/", "/index.html"} else path.lstrip("/")
        target = (FRONTEND / relative).resolve()
        if FRONTEND not in target.parents or not target.is_file():
            self._json({"error": "Risorsa inesistente"}, HTTPStatus.NOT_FOUND)
            return
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), WMSRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Web app locale WMS")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"WMS disponibile su http://{args.host}:{server.server_port}/ (pratica {DEMO_PRACTICE_ID})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
