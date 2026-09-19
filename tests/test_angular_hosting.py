import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.wms_web import app

class AngularHostingTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        (root/'index.html').write_text('<app-root></app-root><script src="/main-TEST.js"></script>')
        (root/'main-TEST.js').write_text('window.angularLoaded=true')
        self.mode=patch.object(app,'FRONTEND_MODE','angular');self.mode.start();self.addCleanup(self.mode.stop)
        self.directory=patch.object(app,'ANGULAR_FRONTEND',root);self.directory.start();self.addCleanup(self.directory.stop)
        self.server=app.create_server(port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def get(self,path):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        connection.request('GET',path);r=connection.getresponse()
        result=(r.status,dict(r.getheaders()),r.read())
        connection.close();return result

    def test_deep_links_and_assets(self):
        for path in ['/', '/login', '/manager', '/work/P-1/T-1', '/practices/P.1/tasks/T.1','/admin','/validation']:
            with self.subTest(path=path):
                status,headers,body=self.get(path)
                self.assertEqual(status,200);self.assertIn(b'<app-root>',body)
                self.assertNotIn(b'auth-context.js',body)
                self.assertEqual(headers['Cache-Control'],'no-store')
        status,headers,body=self.get('/main-TEST.js')
        self.assertEqual(status,200);self.assertIn(b'angularLoaded',body)

    def test_missing_assets_and_traversal_are_not_spa_pages(self):
        for path in ['/missing.js','/%2e%2e/Dockerfile']:
            self.assertEqual(self.get(path)[0],404)

    def test_legacy_links_redirect_to_angular(self):
        for old,new in [('/queue.html','/work'),('/configuration.html','/admin'),('/task.html?practice=P-1&task=T-2','/work/P-1/T-2'),('/manager-task.html?practice=P-1&task=T-2','/practices/P-1/tasks/T-2')]:
            status,headers,_=self.get(old)
            self.assertEqual(status,303);self.assertEqual(headers['Location'],new)

    def test_private_api_still_requires_session(self):
        self.assertEqual(self.get('/api/work-queue')[0],401)
        self.assertEqual(self.get('/api/manager/practices')[0],401)
