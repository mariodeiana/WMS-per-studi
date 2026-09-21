import json
import subprocess
import unittest
from unittest.mock import patch
from operations.management import management as panel

def result(stdout='', code=0):
    return subprocess.CompletedProcess([], code, stdout, '')

class PostgresPanelTest(unittest.TestCase):
    def test_stopped_database_has_no_stale_metrics(self):
        with patch.object(panel, 'docker', return_value=result('exited')) as docker:
            value=panel.database_status()
        self.assertFalse(value['ready'])
        self.assertIsNone(value['metrics'])
        self.assertEqual(docker.call_count, 1)

    def test_collects_metrics_without_touching_n8n(self):
        metrics={'database':'wms_test','size':'10 MB','connections':2}
        with patch.object(panel, 'docker', side_effect=[result('running'),result(),result(json.dumps(metrics))]) as docker:
            self.assertEqual(panel.database_status()['metrics'],metrics)
        for call in docker.call_args_list:
            self.assertIn(panel.POSTGRES_CONTAINER, call.args)
            self.assertNotIn('asc-wfo-postgres',call.args)

    def test_timeout_is_reported_without_exposing_command(self):
        with patch.object(panel,'docker',side_effect=subprocess.TimeoutExpired(['secret'],60)):
            self.assertNotIn('secret',json.dumps(panel.database_status()))
            self.assertIn('error',panel.database_status())

    def test_restart_reconnects_running_application(self):
        with patch.object(panel,'docker',side_effect=[result('true'),result(),result(),result(),result()]) as docker:
            self.assertIn('disponibile',panel.restart_postgres())
        self.assertEqual([c.args[:2] for c in docker.call_args_list],
                         [('inspect','-f'),('stop','asc-wms-test'),('restart','asc-wms-test-postgres'),('exec','asc-wms-test-postgres'),('start','asc-wms-test')])

    def test_failed_restart_still_restores_application_and_releases_lock(self):
        with patch.object(panel,'docker',side_effect=[result('true'),result(),result(code=1),result()]) as docker:
            with self.assertRaises(RuntimeError):panel.restart_postgres()
        self.assertEqual(docker.call_args_list[-1].args,('start','asc-wms-test'))
        self.assertFalse(panel.POSTGRES_RESTART_LOCK.locked())

    def test_restart_preserves_stopped_application(self):
        with patch.object(panel,'docker',side_effect=[result('false'),result(),result()]) as docker:
            panel.restart_postgres()
        self.assertNotIn(('start','asc-wms-test'),[c.args for c in docker.call_args_list])

    def test_concurrent_restart_is_rejected(self):
        panel.POSTGRES_RESTART_LOCK.acquire()
        try:
            with patch.object(panel,'docker') as docker:
                with self.assertRaises(RuntimeError):panel.restart_postgres()
                docker.assert_not_called()
        finally:panel.POSTGRES_RESTART_LOCK.release()
