"""Local Angular acceptance preview with disposable data; never uses WMS environments."""
import argparse
import os
import mimetypes
import tempfile
from pathlib import Path
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    import sys
    sys.path.insert(0, str(root))
    with tempfile.TemporaryDirectory(prefix='wms-angular-preview-') as data_dir:
        os.environ['WMS_DATA_DIR'] = data_dir
        os.environ['WMS_ENV'] = 'DEV'
        from backend.wms_web import app
        from http.server import ThreadingHTTPServer
        app.FRONTEND = root / 'frontend-angular/dist/frontend-angular/browser'
        if not (app.FRONTEND / 'index.html').is_file():
            raise SystemExit('Eseguire prima npm run build in frontend-angular')

        class PreviewHandler(app.WMSRequestHandler):
            def _static(self, path):
                target = (app.FRONTEND / path.lstrip('/')).resolve()
                if app.FRONTEND not in target.parents or not target.is_file():
                    self._json({"error": "Risorsa inesistente"}, 404)
                    return
                data = target.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                path = urlparse(self.path).path
                if path.startswith('/api/'):
                    return super().do_GET()
                return self._static(path if Path(path).suffix else '/index.html')

        app._migrate_nonconformities(PreviewHandler.service)
        app.CONFIG.sync_clients((p.client_id for p in PreviewHandler.service._practices.values()), app.DEMO_CLIENT_NAMES)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), PreviewHandler)
        print(f'Anteprima isolata: http://127.0.0.1:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
