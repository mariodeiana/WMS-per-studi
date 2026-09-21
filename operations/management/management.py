import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 8004

CONTAINERS = {
    "DEV": ("asc-wms-dev", 8000),
    "TEST": ("asc-wms-test", 8001),
    "PROD": ("asc-wms-prod", 8002),
}

DEV_DATA = Path("/opt/asc/wms/data/dev")
TEST_DATA = Path("/opt/asc/wms/data/test")
BACKUP_ROOT = Path("/opt/asc/wms/backups/test")
PREVIOUS = BACKUP_ROOT / "previous"
LAST_FILE = BACKUP_ROOT / "last.txt"


def docker(*args):
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=60
    )


def status():
    result = {}
    for env, (container, port) in CONTAINERS.items():
        p = docker("inspect", "-f", "{{.State.Status}}", container)
        result[env] = {
            "container": container,
            "port": port,
            "status": p.stdout.strip() if p.returncode == 0 else "not-found"
        }
    return result


def last_backup():
    if not LAST_FILE.exists():
        return None
    return LAST_FILE.read_text().strip()


def clear_directory(path):
    path.mkdir(parents=True, exist_ok=True)
    for item in path.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()


def copy_directory(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def save_test_previous():
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    clear_directory(PREVIOUS)
    copy_directory(TEST_DATA, PREVIOUS)
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    LAST_FILE.write_text(stamp + "\n")
    return stamp


def clone_dev_to_test():
    stopped = False
    try:
        p = docker("stop", "asc-wms-test")
        if p.returncode:
            raise RuntimeError(p.stderr.strip())
        stopped = True

        stamp = save_test_previous()
        clear_directory(TEST_DATA)
        copy_directory(DEV_DATA, TEST_DATA)

        p = docker("start", "asc-wms-test")
        if p.returncode:
            raise RuntimeError(p.stderr.strip())
        stopped = False

        return stamp
    finally:
        if stopped:
            docker("start", "asc-wms-test")


def restore_test_previous():
    if not PREVIOUS.exists() or not any(PREVIOUS.iterdir()):
        raise RuntimeError("Nessun TEST precedente disponibile")

    stopped = False
    swap = BACKUP_ROOT / "restore-swap"

    try:
        p = docker("stop", "asc-wms-test")
        if p.returncode:
            raise RuntimeError(p.stderr.strip())
        stopped = True

        clear_directory(swap)
        copy_directory(TEST_DATA, swap)

        clear_directory(TEST_DATA)
        copy_directory(PREVIOUS, TEST_DATA)

        clear_directory(PREVIOUS)
        copy_directory(swap, PREVIOUS)
        shutil.rmtree(swap)

        stamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        LAST_FILE.write_text(stamp + "\n")

        p = docker("start", "asc-wms-test")
        if p.returncode:
            raise RuntimeError(p.stderr.strip())
        stopped = False

        return stamp
    finally:
        if stopped:
            docker("start", "asc-wms-test")


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, code=200):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/status":
            self.send_json({
                "instances": status(),
                "last_test_backup": last_backup()
            })
            return

        if self.path != "/":
            self.send_error(404)
            return

        states = status()
        backup = last_backup() or "Nessun salvataggio disponibile"

        rows = []
        for env, info in states.items():
            extra = ""
            if env == "TEST":
                extra = f"""
                <hr>
                <button onclick="cloneTest()">Clona DEV → TEST</button>
                <p class="backup">Ultimo TEST salvato:<br><strong>{backup}</strong></p>
                <button class="restore" onclick="restoreTest()">Ripristina TEST precedente</button>
                """

            rows.append(f"""
            <section class="card">
              <h2>{env}</h2>
              <div class="status">{info['status'].upper()}</div>
              <p>Porta {info['port']}</p>
              <button onclick="restart('{env}')">Riavvia {env}</button>
              {extra}
            </section>
            """)

        html = f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WMS Management</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f3f5f2;color:#1c2b2a}}
header{{background:#123b36;color:white;padding:20px 32px}}
main{{max-width:1000px;margin:32px auto;padding:0 24px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;align-items:start}}
.card{{background:white;border:1px solid #dde4e0;border-radius:12px;padding:24px}}
.status{{font-weight:900;margin:12px 0}}
button{{border:0;border-radius:7px;padding:11px 14px;background:#246b5c;color:white;font-weight:750;cursor:pointer;margin:3px 0}}
.restore{{background:#56635f}}
.all{{margin-top:24px}}
.backup{{font-size:13px;line-height:1.5}}
hr{{border:0;border-top:1px solid #dde4e0;margin:20px 0}}
#message{{font-weight:700;margin-top:20px}}
@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><strong>WMS Management · ASC-OLB-WFO-01</strong></header>
<main>
<h1>Ambienti WMS</h1>
<div class="grid">{''.join(rows)}</div>
<button class="all" onclick="restart('ALL')">Riavvia tutte</button>
<p id="message"></p>
</main>
<script>
async function action(url, question) {{
 if(!confirm(question)) return;
 const message=document.getElementById('message');
 message.textContent='Operazione in corso...';
 const r=await fetch(url,{{method:'POST'}});
 const j=await r.json();
 message.textContent=j.message || j.error;
 if(r.ok)setTimeout(()=>location.reload(),1200);
}}

function restart(env) {{
 action('/api/restart/'+env,'Confermi riavvio '+env+'?');
}}

function cloneTest() {{
 action(
   '/api/clone/dev-to-test',
   'Clonare DEV in TEST? Il TEST corrente verrà prima salvato come TEST precedente.'
 );
}}

function restoreTest() {{
 action(
   '/api/restore/test',
   'Ripristinare il TEST precedente? Il TEST corrente verrà conservato per consentire di tornare indietro.'
 );
}}
</script>
</body>
</html>"""

        data = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path == "/api/clone/dev-to-test":
            try:
                stamp = clone_dev_to_test()
                self.send_json({
                    "message": "DEV clonato in TEST. TEST precedente salvato: " + stamp
                })
            except Exception as exc:
                self.send_json({"error": str(exc)}, 500)
            return

        if self.path == "/api/restore/test":
            try:
                stamp = restore_test_previous()
                self.send_json({
                    "message": "TEST precedente ripristinato. Punto di ritorno aggiornato: " + stamp
                })
            except Exception as exc:
                self.send_json({"error": str(exc)}, 500)
            return

        prefix = "/api/restart/"
        if not self.path.startswith(prefix):
            self.send_json({"error": "Azione inesistente"}, 404)
            return

        env = self.path[len(prefix):].upper()

        if env == "ALL":
            targets = [v[0] for v in CONTAINERS.values()]
        elif env in CONTAINERS:
            targets = [CONTAINERS[env][0]]
        else:
            self.send_json({"error": "Ambiente non valido"}, 400)
            return

        p = docker("restart", *targets)
        if p.returncode:
            self.send_json({"error": p.stderr.strip()}, 500)
            return

        self.send_json({"message": f"Riavvio {env} completato"})


ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
