import json
import shutil
import subprocess
import time
from html import escape
from urllib.request import urlopen
from threading import Lock
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


def application_revision(container, port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/runtime', timeout=2) as response:
            runtime = json.load(response)
            version, revision = runtime.get('version'), runtime.get('revision')
            if version and isinstance(revision, int):
                return f'Versione {version} · Revisione {revision}'
    except (OSError, ValueError):
        pass
    return 'Versione non rilevata'


def status():
    result = {}
    for env, (container, port) in CONTAINERS.items():
        p = docker("inspect", "-f", "{{.State.Status}}", container)
        result[env] = {
            "container": container,
            "port": port,
            "revision": application_revision(container, port),
            "status": p.stdout.strip() if p.returncode == 0 else "not-found"
        }
    return result


# WMS TEST only: never target the independent n8n PostgreSQL container.
POSTGRES_CONTAINER = "asc-wms-test-postgres"
POSTGRES_DATABASE = "wms_test"
POSTGRES_APPLICATION = "asc-wms-test"
POSTGRES_RESTART_LOCK = Lock()
DATABASE_METRICS_SQL = """
SELECT json_build_object(
 'database', current_database(),
 'version', current_setting('server_version'),
 'size', pg_size_pretty(pg_database_size(current_database())),
 'uptime', date_trunc('second', clock_timestamp()-pg_postmaster_start_time())::text,
 'connections', (SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()),
 'active_connections', (SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND state='active' AND pid<>pg_backend_pid()),
 'max_connections', current_setting('max_connections')::int,
 'transactions', xact_commit + xact_rollback,
 'rollbacks', xact_rollback,
 'deadlocks', deadlocks,
 'statistics_since', stats_reset,
 'clients', (SELECT count(*) FROM clients),
 'practices', (SELECT count(*) FROM practices),
 'repertoire_entries', (SELECT count(*) FROM client_repertoire),
 'tables', (SELECT json_agg(t) FROM (
   SELECT relname AS name, pg_size_pretty(pg_total_relation_size(relid)) AS size,
          n_live_tup AS estimated_rows
   FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 8
 ) t)
) FROM pg_stat_database WHERE datname=current_database()
"""


def database_status():
    info = {"environment": "TEST", "container": POSTGRES_CONTAINER,
            "status": "unknown", "ready": False, "metrics": None}
    try:
        state = docker("inspect", "-f", "{{.State.Status}}", POSTGRES_CONTAINER)
        info["status"] = state.stdout.strip() if state.returncode == 0 else "not-found"
        if info["status"] != "running":
            return info
        ready = docker("exec", POSTGRES_CONTAINER, "pg_isready", "-U", POSTGRES_DATABASE, "-d", POSTGRES_DATABASE)
        info["ready"] = ready.returncode == 0
        if not info["ready"]:
            return info
        query = docker("exec", "-e", "PGOPTIONS=-c statement_timeout=5000", POSTGRES_CONTAINER,
                       "psql", "-X", "-U", POSTGRES_DATABASE, "-d", POSTGRES_DATABASE,
                       "-At", "-v", "ON_ERROR_STOP=1", "-c", DATABASE_METRICS_SQL)
        if query.returncode != 0:
            info["error"] = "Database raggiungibile; misure non disponibili."
        else:
            info["metrics"] = json.loads(query.stdout)
    except (subprocess.TimeoutExpired, OSError, ValueError):
        info["error"] = "Controllo PostgreSQL non disponibile; riprovare."
    return info


def restart_postgres():
    if not POSTGRES_RESTART_LOCK.acquire(blocking=False):
        raise RuntimeError("Un riavvio PostgreSQL è già in corso.")
    app_running = False
    try:
        state = docker("inspect", "-f", "{{.State.Running}}", POSTGRES_APPLICATION)
        if state.returncode:
            raise RuntimeError("Impossibile verificare lo stato del WMS TEST.")
        app_running = state.stdout.strip() == "true"
        if app_running:
            stopped = docker("stop", POSTGRES_APPLICATION)
            if stopped.returncode:
                raise RuntimeError("Impossibile arrestare WMS TEST; PostgreSQL non è stato riavviato.")
        restarted = docker("restart", POSTGRES_CONTAINER)
        if restarted.returncode:
            raise RuntimeError("Riavvio PostgreSQL non riuscito.")
        for _ in range(30):
            ready = docker("exec", POSTGRES_CONTAINER, "pg_isready", "-U", POSTGRES_DATABASE, "-d", POSTGRES_DATABASE)
            if ready.returncode == 0:
                return "PostgreSQL WMS TEST riavviato e disponibile."
            time.sleep(1)
        raise RuntimeError("PostgreSQL riavviato, ma non ancora pronto. Controllare lo stato.")
    finally:
        try:
            # Reopen the application's persistent connection after the DB restart.
            if app_running:
                started = docker("start", POSTGRES_APPLICATION)
                if started.returncode:
                    raise RuntimeError("Controllare WMS TEST: riavvio applicativo non riuscito.")
        finally:
            POSTGRES_RESTART_LOCK.release()


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
        if self.path == "/api/postgres":
            self.send_json(database_status())
            return
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
              <p><a href="http://192.168.11.10:{info['port']}" target="_blank" rel="noopener">Apri {env} · {escape(info['revision'])}</a></p>
              <button onclick="restart('{env}')">Riavvia {env} · {escape(info['revision'])}</button>
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
.database-card{{margin-top:24px}} #pg-metrics{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} #pg-metrics dt{{font-weight:600}} #pg-metrics dd{{margin:0}} button:disabled{{opacity:.5}}
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
<p id="message" role="status"></p>
<section class="card database-card">
<h2>PostgreSQL · WMS TEST</h2>
<p id="pg-state" role="status">Controllo in corso…</p>
<p>Database dedicato a TEST. DEV e PROD usano ancora la persistenza precedente.</p>
<button id="pg-restart" onclick="restartPostgres()">Riavvia PostgreSQL TEST</button>
<button onclick="refreshPostgres()">Aggiorna misure</button>
<p class="backup">Il riavvio sospende brevemente WMS TEST e lo riavvia per ristabilire la connessione.</p>
<dl id="pg-metrics"></dl>
<h3>Tabelle principali</h3><div id="pg-tables"></div>
<small>Righe delle tabelle stimate; conteggi di clienti, pratiche e voci Repertorio esatti.
Transazioni, rollback e deadlock sono cumulativi dall’azzeramento delle statistiche.
Le connessioni totali includono questa verifica; il limite è dell’intero server PostgreSQL.</small>
<p id="pg-updated" class="backup"></p>
</section>
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

let postgresRefreshing=false;
async function refreshPostgres() {{
 if(postgresRefreshing) return;
 postgresRefreshing=true;
 const state=document.getElementById('pg-state'), metrics=document.getElementById('pg-metrics'), tables=document.getElementById('pg-tables');
 try {{
  const response=await fetch('/api/postgres',{{cache:'no-store'}});
  if(!response.ok) throw new Error();
  const data=await response.json();
  const labels={{running:'In esecuzione',exited:'Fermo',restarting:'In riavvio','not-found':'Non trovato',unknown:'Non disponibile'}};
  state.textContent=(labels[data.status] || data.status)+(data.ready?' · Accetta connessioni':' · Non disponibile')+(data.error?' · '+data.error:'');
  metrics.replaceChildren(); tables.replaceChildren();
  const m=data.metrics;
  if(m) {{
   const values=[['Versione',m.version],['Database',m.database],['Dimensione',m.size],['Tempo dall’avvio',m.uptime],['Connessioni totali',m.connections],['Query attive',m.active_connections],['Limite connessioni',m.max_connections],['Clienti',m.clients],['Pratiche',m.practices],['Voci Repertorio',m.repertoire_entries],['Transazioni',m.transactions],['Rollback',m.rollbacks],['Deadlock',m.deadlocks],['Statistiche dal',m.statistics_since || 'Non disponibile']];
   for(const [label,value] of values) {{
    const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(value);metrics.append(dt,dd);
   }}
   for(const table of m.tables || []) {{
    const row=document.createElement('p');row.textContent=table.name+' · '+table.size+' · circa '+table.estimated_rows+' righe';tables.append(row);
   }}
  }}
  document.getElementById('pg-updated').textContent='Ultimo controllo: '+new Date().toLocaleTimeString('it-IT');
 }} catch(error) {{
  state.textContent='Impossibile aggiornare lo stato PostgreSQL.';
  metrics.replaceChildren(); tables.replaceChildren();
 }} finally {{postgresRefreshing=false;}}
}}
async function restartPostgres() {{
 if(!confirm('Riavviare PostgreSQL WMS TEST? WMS TEST sarà temporaneamente sospeso e riconnesso.')) return;
 const button=document.getElementById('pg-restart'),message=document.getElementById('message');
 button.disabled=true;message.textContent='Riavvio PostgreSQL TEST in corso…';
 try {{
  const response=await fetch('/api/postgres/restart',{{method:'POST'}});
  const data=await response.json();message.textContent=data.message || data.error;
 }} catch(error) {{message.textContent='Esito non disponibile: controllare lo stato prima di riprovare.';}}
 finally {{button.disabled=false;await refreshPostgres();}}
}}
refreshPostgres();
setInterval(refreshPostgres,15000);

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
        if self.path == "/api/postgres/restart":
            try:
                self.send_json({"message": restart_postgres()})
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                self.send_json({"error": str(exc) if isinstance(exc, RuntimeError) else "Riavvio non completato: controllare lo stato."}, 503)
            return
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


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
