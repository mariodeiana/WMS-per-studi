import copy
import json
import os
from uuid import uuid4
from urllib.parse import quote
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.wms_web.admin_config import AdminConfigStore
from backend.wms_web.config_models import create_configured_practice, generate_repertoire_practices
from backend.wms_web.database import Database, encode
from backend.wms_web.organization_service import OrganizationalPracticeService

ADMIN = {'role': 'AMMINISTRATORE', 'username': 'mario.demo'}

class RepertoireDatabaseTest(unittest.TestCase):
    def make_database(self, path):
        url = os.environ.get('WMS_TEST_DATABASE_URL')
        if not url: return Database(path)
        import psycopg
        schema = 'wms_test_' + uuid4().hex
        with psycopg.connect(url, autocommit=True) as connection:
            connection.execute(f'CREATE SCHEMA {schema}')
        def cleanup():
            with psycopg.connect(url, autocommit=True) as connection:
                connection.execute(f'DROP SCHEMA {schema} CASCADE')
        self.addCleanup(cleanup)
        return Database(url + ('&' if '?' in url else '?') + 'options=' + quote('-csearch_path=' + schema))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.db = self.make_database(self.path / 'wms.sqlite3')
        self.addCleanup(self.db.connection.close)
        self.config = AdminConfigStore(self.path / 'config.json', database=self.db)
        self.service = OrganizationalPracticeService(database=self.db, seed_demo=False)
        self.config.save('clients', {'id':'C', 'name':'Cliente', 'gis_company_code':'00123', 'accounting_regime':'Ordinario', 'vat_settlement_type':'Trimestrale', 'notes':'Nota'})
        self.body = {'client_id':'C', 'model_id':'LIPE_TRIM', 'period_start':'2026-01-01', 'period_end':'2026-03-31', 'due_date':'2026-05-31'}

    def create(self):
        return create_configured_practice(self.service, self.config, self.body, ADMIN)

    def test_manual_outside_and_inside_and_historical_snapshot(self):
        extra = self.create()
        self.assertEqual((extra['origin'], extra['economic_regime']), ('MANUALE', 'EXTRA_CONTRATTO'))
        self.config.save('clients', {'id':'C','repertoire':['LIPE_TRIM']})
        included = self.create()
        self.config.save('clients', {'id':'C','repertoire':[]})
        reloaded = OrganizationalPracticeService(database=self.db, seed_demo=False)
        self.assertEqual(reloaded.get_for(included['id'], ADMIN)['economic_regime'], 'IN_REPERTORIO')
        self.assertEqual(reloaded.get_for(extra['id'], ADMIN)['economic_regime'], 'EXTRA_CONTRATTO')
        self.assertEqual(reloaded.get_for(included['id'], ADMIN)['tasks'][0]['transitions'], included['tasks'][0]['transitions'])
        # Request bodies cannot forge the immutable snapshot.
        forged = create_configured_practice(self.service,self.config,{**self.body,'origin':'AUTOMATICA','economic_regime':'IN_REPERTORIO'},ADMIN)
        self.assertEqual((forged['origin'], forged['economic_regime']), ('MANUALE','EXTRA_CONTRATTO'))

    def test_generation_selects_active_subscribers_and_is_idempotent(self):
        with self.assertRaises(ValueError): create_configured_practice(self.service,self.config,self.body,ADMIN,origin='AUTOMATICA')
        self.config.save('clients', {'id':'C','repertoire':['LIPE_TRIM']})
        self.config.save('clients', {'id':'INACTIVE','name':'Inattivo','active':False,'repertoire':['LIPE_TRIM']})
        self.config.save('clients', {'id':'OUT','name':'Extra'})
        generated = generate_repertoire_practices(self.service,self.config,self.body,ADMIN)
        self.assertEqual(len(generated),1)
        self.assertEqual((generated[0]['client_id'],generated[0]['origin'],generated[0]['economic_regime']),('C','AUTOMATICA','IN_REPERTORIO'))
        self.assertEqual(generate_repertoire_practices(self.service,self.config,self.body,ADMIN),[])
        with self.assertRaises(PermissionError):generate_repertoire_practices(self.service,self.config,self.body,{'role':'OPERATORE'})

    def test_repertoire_validation_and_foreign_keys(self):
        before = self.config.snapshot()
        for repertoire in [['unknown'], ['LIPE_TRIM','LIPE_TRIM'], 'LIPE_TRIM', [None]]:
            with self.assertRaises(ValueError): self.config.save('clients', {'id':'C','repertoire':repertoire})
        self.assertEqual(before,self.config.snapshot())
        self.config.save('clients', {'id':'C','repertoire':['LIPE_TRIM']})
        with self.assertRaises(ValueError):self.config.delete('practice_types','LIPE_TRIM')
        with self.assertRaises(Exception):
            with self.db.transaction() as execute: execute('INSERT INTO client_repertoire VALUES (?,?)',('missing','LIPE_TRIM'))
        reloaded = AdminConfigStore(self.path/'config.json',database=self.db)
        client = reloaded.list('clients')[0]
        self.assertEqual(client['repertoire'], ['LIPE_TRIM'])
        self.assertEqual(client['gis_company_code'],'00123')
        self.assertEqual(client['notes'],'Nota')

    def test_service_contract_dates_round_trip_and_validation(self):
        self.config.save('clients', {'id':'C', 'repertoire_signed_on':'2026-01-01', 'repertoire_valid_until':'2026-12-31', 'repertoire':['LIPE_TRIM']})
        reloaded = AdminConfigStore(self.path/'config.json', database=self.db)
        client = reloaded.list('clients')[0]
        self.assertEqual(client['repertoire_signed_on'], '2026-01-01')
        self.assertEqual(client['repertoire_valid_until'], '2026-12-31')
        before = self.config.snapshot()
        for dates in [
            {'repertoire_signed_on':'2026-02-30'},
            {'repertoire_signed_on':'20260101'},
            {'repertoire_valid_until':'2025-12-31'},
            {'repertoire_signed_on':'', 'repertoire_valid_until':'2026-12-31'},
            {'repertoire_signed_on':123}
        ]:
            with self.assertRaises(ValueError): self.config.save('clients', {'id':'C', **dates})
            self.assertEqual(self.config.snapshot(), before)
        self.config.save('clients', {'id':'C', 'repertoire_valid_until':''})
        self.assertEqual(AdminConfigStore(self.path/'config.json', database=self.db).list('clients')[0]['repertoire_valid_until'], '')
        self.assertEqual(self.config.authentication_data(), reloaded.authentication_data())

    def test_billing_frequency_round_trip_and_validation(self):
        for frequency in ('MENSILE', 'BIMESTRALE', 'TRIMESTRALE', 'QUADRIMESTRALE', 'SEMESTRALE', 'ANNUALE', ''):
            self.config.save('clients', {'id':'C', 'repertoire_billing_frequency':frequency})
            reloaded = AdminConfigStore(self.path/'config.json', database=self.db)
            self.assertEqual(reloaded.list('clients')[0]['repertoire_billing_frequency'], frequency)
        before = self.config.snapshot()
        with self.assertRaises(ValueError):
            self.config.save('clients', {'id':'C', 'repertoire_billing_frequency':'SETTIMANALE'})
        self.assertEqual(before, self.config.snapshot())

    def test_database_failure_rolls_back_memory_and_sql(self):
        before = self.config.snapshot()
        with patch.object(self.db, 'save_config', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.config.save('clients', {'id':'C','name':'Changed'})
        self.assertEqual(self.config.snapshot(),before)
        with patch.object(self.db, 'save_practices', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.create()
        self.assertEqual(self.service._practices,{})
        self.assertEqual(self.db.load_practices(),{})

    def test_generation_failure_rolls_back_entire_batch(self):
        self.config.save('clients', {'id':'C','repertoire':['LIPE_TRIM']})
        self.config.save('clients', {'id':'SECOND','name':'Secondo','repertoire':['LIPE_TRIM']})
        with patch.object(self.db, 'save_practices', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):generate_repertoire_practices(self.service,self.config,self.body,ADMIN)
        self.assertEqual(self.service._practices,{})
        self.assertEqual(self.db.load_practices(),{})

    def test_legacy_import_preserves_credentials_memberships_workflow_and_files(self):
        legacy_path = self.path/'legacy.json'
        legacy = AdminConfigStore(legacy_path)
        legacy.save('clients',{'id':'L','name':'Legacy'})
        state_path=self.path/'legacy.pkl'
        service=OrganizationalPracticeService(state_path=state_path,rich_demo=True)
        service._persist()
        old_config,old_state=legacy_path.read_bytes(),state_path.read_bytes()
        db=self.make_database(self.path/'import.sqlite3')
        self.addCleanup(db.connection.close)
        imported=AdminConfigStore(legacy_path,database=db)
        imported_service=OrganizationalPracticeService(state_path=state_path,database=db,seed_demo=False)
        self.assertEqual(imported.authentication_data(),legacy.authentication_data())
        self.assertEqual(encode(imported_service._practices),encode(service._practices))
        self.assertEqual(legacy_path.read_bytes(),old_config)
        self.assertEqual(state_path.read_bytes(),old_state)
        for p in imported_service._practices.values():
            self.assertIsNone(p.origin)
            self.assertIsNone(p.economic_regime)
        reloaded=AdminConfigStore(legacy_path,database=db)
        self.assertEqual(reloaded.authentication_data(),imported.authentication_data())
        self.assertEqual(len(OrganizationalPracticeService(state_path=state_path,database=db,seed_demo=False)._practices),len(service._practices))

    def test_empty_database_does_not_reseed_and_corruption_stops_import(self):
        self.assertEqual(OrganizationalPracticeService(database=self.db,rich_demo=True)._practices,{})
        bad=self.path/'bad.json';bad.write_text('{broken')
        fresh=self.make_database(self.path/'bad.sqlite3');self.addCleanup(fresh.connection.close)
        with self.assertRaises(RuntimeError):AdminConfigStore(bad,database=fresh)
        self.assertIsNone(fresh.load_config())
