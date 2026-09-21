import json
import threading
import unittest
from uuid import uuid4
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from backend.wms_web.app import AUTH, CONFIG, DRAFTS, create_server

class ModelDraftApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=create_server(port=0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def call(self,path,body=None):
        request=Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','Cookie':'WMSSESSION='+self.token})
        try:
            with urlopen(request) as response:return response.status,json.load(response)
        except HTTPError as error:
            with error:return error.code,json.load(error)
    def test_role_session_recovery_and_stale_revision(self):
        self.token,_=AUTH.login('mario.demo','demo')
        self.assertEqual(self.call('/api/admin/model-drafts')[0],403)
        AUTH.switch(self.token,'mario-amministratore')
        published=CONFIG.list('practice_types')
        body={'id':str(uuid4()),'revision':0,'snapshot':{'draft':{'name':'Draft'},'tasks':[]}}
        code,saved=self.call('/api/admin/model-drafts',body);self.assertEqual(code,200)
        self.addCleanup(lambda:DRAFTS.delete('mario.demo',{'id':saved['id'],'revision':saved['revision']}))
        self.assertEqual(self.call('/api/admin/model-drafts',body)[0],409)
        AUTH.logout(self.token)
        self.assertEqual(self.call('/api/admin/model-drafts')[0],401)
        self.token,_=AUTH.login('mario.demo','demo');AUTH.switch(self.token,'mario-amministratore')
        self.assertIn(saved,self.call('/api/admin/model-drafts')[1])
        self.assertEqual(CONFIG.list('practice_types'),published)
    def test_stale_model_cannot_be_published(self):
        self.token,_=AUTH.login('mario.demo','demo');AUTH.switch(self.token,'mario-amministratore')
        published=CONFIG.list('practice_types')
        body={**published[0],'_expected_model':{}}
        self.assertEqual(self.call('/api/admin/config/practice_types',body)[0],409)
        self.assertEqual(CONFIG.list('practice_types'),published)
