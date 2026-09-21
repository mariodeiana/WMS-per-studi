import tempfile
import unittest
from uuid import uuid4
from pathlib import Path
from backend.wms_web.model_drafts import ModelDraftStore

class ModelDraftTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=ModelDraftStore(Path(self.tmp.name)/'drafts')
        self.body={'id':str(uuid4()),'revision':0,'snapshot':{'draft':{'name':'Bozza'},'tasks':[{'code':'A','title':'','choices':[]}]}}

    def test_incomplete_draft_survives_restart_and_is_private(self):
        saved=self.store.save('anna',self.body)
        restarted=ModelDraftStore(self.store.directory)
        self.assertEqual(restarted.list('anna'),[saved])
        self.assertEqual(restarted.list('luca'),[])
        restarted.delete('luca',{'id':saved['id'],'revision':1})
        self.assertEqual(restarted.list('anna'),[saved])

    def test_stale_writes_and_deletes_cannot_overwrite_newer_draft(self):
        saved=self.store.save('anna',self.body)
        with self.assertRaises(ValueError):self.store.save('anna',self.body)
        with self.assertRaises(ValueError):self.store.delete('anna',{'id':saved['id'],'revision':0})
        self.assertEqual(self.store.list('anna'),[saved])
        self.store.delete('anna',{'id':saved['id'],'revision':1})
        self.assertEqual(self.store.list('anna'),[])

    def test_reauthentication_with_another_user_cannot_move_a_draft(self):
        with self.assertRaises(PermissionError): self.store.save('luca',{**self.body,'owner':'anna'})
        self.assertEqual(self.store.list('luca'),[])

    def test_rejects_path_traversal_and_invalid_content(self):
        with self.assertRaises(ValueError):self.store.save('anna',{**self.body,'id':'../../config'})
        with self.assertRaises(ValueError):self.store.save('anna',{**self.body,'snapshot':{'tasks':'invalid'}})
        with self.assertRaises(ValueError):self.store.save('anna',{**self.body,'revision':True})
