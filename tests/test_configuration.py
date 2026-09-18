import copy
import json
import tempfile
import unittest
from pathlib import Path
from backend.wms_web.admin_config import AdminConfigStore, DEFAULT_DATA
from backend.wms_web.config_models import create_configured_practice
from backend.wms_web.organization_service import OrganizationalPracticeService
from backend.wms_core.workflow import WorkflowError

ADMIN = {"role":"AMMINISTRATORE", "username":"mario.demo"}
OPERATOR = {"role":"OPERATORE", "username":"mario.demo", "group_id":"contabili"}

class ConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'config.json'
        self.config=AdminConfigStore(self.path)
        self.service=OrganizationalPracticeService(state_path=Path(self.tmp.name)/'state.pkl')
        self.config.save('clients', {'id':'C-TEST','name':'Cliente prova','active':True})
        self.model={'id':'TEST','code':'TEST','name':'Modello prova','active':True,'requires_validation':False,'tasks':[
            {'code':'A','title':'Raccolta','assigned_group':'contabili','instructions':'Raccogli documenti','days_before_due':5,'required':True,'depends_on':[]},
            {'code':'B','title':'Controllo','assigned_group':'contabili','days_before_due':0,'required':True,'depends_on':['A']}]}
        self.config.save('practice_types', self.model)
        self.body={'client_id':'C-TEST','model_id':'TEST','period_start':'2026-09-01','period_end':'2026-09-30','due_date':'2026-10-16'}

    def test_migration_is_additive_and_idempotent(self):
        legacy=copy.deepcopy(DEFAULT_DATA)
        legacy['groups'].append({'id':'custom','name':'Custom','role':'OPERATORE'})
        self.path.write_text(json.dumps(legacy))
        store=AdminConfigStore(self.path)
        self.assertEqual(len(store.list('practice_types')),6)
        self.assertIn('custom',[g['id'] for g in store.list('groups')])
        store.sync_clients(['CLIENT-001','CLIENT-001'])
        self.assertEqual(len(store.list('clients')),1)
        self.assertEqual(AdminConfigStore(self.path).snapshot(),store.snapshot())

    def test_reject_invalid_dependencies_groups_and_deadlines(self):
        for mutation in ['cycle','missing','duplicate','group','days']:
            model=copy.deepcopy(self.model)
            if mutation=='cycle':model['tasks'][0]['depends_on']=['B']
            if mutation=='missing':model['tasks'][0]['depends_on']=['missing']
            if mutation=='duplicate':model['tasks'][1]['code']='A'
            if mutation=='group':model['tasks'][0]['assigned_group']='manager'
            if mutation=='days':model['tasks'][0]['days_before_due']=-1
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.config.save('practice_types',model)
        self.assertEqual(self.config.list('practice_types')[-1],self.model)

    def test_create_persist_and_snapshot_model(self):
        p=create_configured_practice(self.service,self.config,self.body,ADMIN)
        self.assertEqual([t['code'] for t in p['tasks']],['A','B'])
        self.assertEqual(p['tasks'][0]['due_date'],'2026-10-11')
        self.assertFalse(p['requires_validation'])
        self.model['tasks'][0]['title']='Nuovo titolo'
        self.config.save('practice_types',self.model)
        self.assertEqual(self.service.get_for(p['id'],ADMIN)['tasks'][0]['title'],'Raccolta')
        reloaded=OrganizationalPracticeService(state_path=Path(self.tmp.name)/'state.pkl')
        self.assertEqual(reloaded.get_for(p['id'],ADMIN)['tasks'][0]['due_date'],'2026-10-11')
        queue=reloaded.work_queue_for(OPERATOR)
        self.assertEqual(next(t for t in queue if t['practice_id']==p['id'] and t['code']=='A')['due_date'],'2026-10-11')
        with self.assertRaises(WorkflowError):reloaded.complete_task_for(p['id'],'B',OPERATOR)
        reloaded.complete_task_for(p['id'],'A',OPERATOR)
        done=reloaded.complete_task_for(p['id'],'B',OPERATOR)
        self.assertEqual(done['status'],'COMPLETATA')

    def test_invalid_creation_has_no_side_effect(self):
        size=len(self.service._practices)
        for patch in [{'client_id':'missing'},{'model_id':'missing'},{'period_end':'2025-01-01'},{'due_date':'invalid'}]:
            with self.assertRaises(ValueError):create_configured_practice(self.service,self.config,{**self.body,**patch},ADMIN)
        with self.assertRaises(PermissionError):create_configured_practice(self.service,self.config,self.body,OPERATOR)
        self.config.save('clients',{'id':'C-TEST','active':False})
        with self.assertRaises(ValueError):create_configured_practice(self.service,self.config,self.body,ADMIN)
        self.assertEqual(len(self.service._practices),size)

    def test_metadata_edits_preserve_tasks_and_duplicate_codes_are_rejected(self):
        self.config.save('practice_types',{'id':'TEST','name':'Updated'})
        saved=next(m for m in self.config.list('practice_types') if m['id']=='TEST')
        self.assertEqual(saved['tasks'],self.model['tasks'])
        with self.assertRaises(ValueError):self.config.save('practice_types',{**self.model,'id':'OTHER'})
        with self.assertRaises(ValueError):self.config.delete('groups','contabili')

class ConfigurationHTTPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import threading
        from backend.wms_web import app
        cls.app=app
        cls.tmp=tempfile.TemporaryDirectory()
        cls.original_config, cls.original_service=app.CONFIG, app.WMSRequestHandler.service
        app.CONFIG=AdminConfigStore(Path(cls.tmp.name)/'config.json')
        app.WMSRequestHandler.service=OrganizationalPracticeService(state_path=Path(cls.tmp.name)/'state.pkl')
        cls.server=app.create_server(port=0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
        cls.app.CONFIG,cls.app.WMSRequestHandler.service=cls.original_config,cls.original_service
        cls.tmp.cleanup()

    def request(self,path,body=None,admin=True):
        from backend.wms_web.auth import AUTH
        from urllib.request import Request,urlopen
        from urllib.error import HTTPError
        token,_=AUTH.login('mario.demo','demo')
        if admin: AUTH.switch(token,'mario-amministratore')
        try:
            req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','Cookie':f'WMSSESSION={token}'})
            try:
                with urlopen(req) as response:return response.status,json.load(response)
            except HTTPError as error:
                with error:return error.code,json.load(error)
        finally: AUTH.logout(token)

    def test_admin_routes_and_protection_of_used_catalog(self):
        self.assertEqual(self.request('/api/admin/practices',admin=False)[0],403)
        self.assertEqual(self.request('/api/admin/practices',{},admin=False)[0],403)
        self.assertEqual(self.request('/api/admin/config/clients',{'id':'HTTP','name':'Cliente HTTP'})[0],200)
        body={'client_id':'HTTP','model_id':'LIPE_TRIM','period_start':'2026-09-01','period_end':'2026-09-30','due_date':'2026-10-16'}
        status,p=self.request('/api/admin/practices',body)
        self.assertEqual(status,200)
        self.assertEqual(len(p['tasks']),7)
        self.assertIn(p['id'],[r['id'] for r in self.request('/api/admin/practices')[1]])
        self.assertEqual(self.request('/api/admin/config/clients/delete',{'id':'HTTP'})[0],409)
        self.assertEqual(self.request('/api/admin/config/practice_types/delete',{'id':'LIPE_TRIM'})[0],409)
        self.assertEqual(self.request('/api/admin/config/practice_types',{'id':'LIPE_TRIM','code':'CHANGED'})[0],409)
        self.assertEqual(self.request('/api/admin/config/clients',{'id':'HTTP','name':'Cliente aggiornato'})[0],200)
