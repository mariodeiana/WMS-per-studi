"""Configured graphs: activation, desks, persistence and terminal semantics."""
import copy
import tempfile
import unittest
from pathlib import Path

from backend.wms_core.workflow import WorkflowError
from backend.wms_web.admin_config import AdminConfigStore
from backend.wms_web.config_models import create_configured_practice, validate_model
from backend.wms_web.organization_service import OrganizationalPracticeService

ADMIN = {'role': 'AMMINISTRATORE', 'username': 'admin'}
OP = {'role': 'OPERATORE', 'username': 'operator', 'group_id': 'contabili'}
SUP = {'role': 'MANAGER', 'username': 'supervisor'}
VAL = {'role': 'VALIDATORE', 'username': 'validator'}


def node(code, transitions=None, outcomes=None, **extra):
    return dict(code=code, title=code, assigned_group='contabili',
                transitions=transitions or {}, outcomes=outcomes or [], **extra)


class GraphWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = AdminConfigStore(Path(self.tmp.name) / 'config.json')
        self.path = Path(self.tmp.name) / 'state.pkl'
        self.service = OrganizationalPracticeService(state_path=self.path, seed_demo=False)
        self.config.save('clients', {'id': 'C', 'name': 'Cliente'})

    def create(self, nodes, validation=False):
        self.config.save('practice_types', dict(id='GRAPH', code='GRAPH', name='Grafo',
                         tasks=nodes, requires_validation=validation))
        p = create_configured_practice(self.service, self.config,
            dict(model_id='GRAPH', client_id='C', period_start='2026-01-01',
                 period_end='2026-01-31', due_date='2026-02-01'), ADMIN)
        self.pid = p['id']
        return p

    def complete(self, code, outcome='COMPLETATO'):
        return self.service.complete_task_for(self.pid, code, OP, outcome)

    def active(self):
        return [t['code'] for t in self.service.work_queue_for(OP) if t['queue_section'] == 'ACTIVE']

    def summary(self):
        return self.service.manager_practices_for(SUP)[0]

    def test_explicit_starts_block_orphans_without_creating_work(self):
        with self.assertRaisesRegex(ValueError, 'senza ingressi'):
            self.create([node('A', is_initial=True), node('B', is_initial=False)])
        self.assertEqual(len(self.service._practices), 0)
        self.create([node('A', {'*':['B']}, is_initial=True), node('B', is_initial=False), node('C', is_initial=True)])
        self.assertEqual(self.active(), ['A','C'])
        self.complete('A')
        self.assertEqual(self.active(), ['B','C'])

    def test_sequence_and_persistence_only_expose_current_node(self):
        self.create([node('C', {'*': ['@END']}), node('A', {'*': ['B']}), node('B', {'*': ['C']})])
        self.assertEqual(self.active(), ['A'])
        self.assertEqual(self.summary()['progress']['total'], 1)
        self.complete('A')
        self.assertEqual(self.active(), ['B'])
        self.service = OrganizationalPracticeService(state_path=self.path, seed_demo=False)
        self.assertEqual(self.active(), ['B'])
        self.complete('B')
        self.assertEqual(self.active(), ['C'])
        self.assertEqual(self.complete('C')['status'], 'COMPLETATA')
        self.assertEqual(self.active(), [])
        self.assertEqual(self.service.close_for(self.pid, SUP)['status'], 'CHIUSA')
        self.assertEqual(self.service.manager_practices_for(SUP), [])

    def test_outcome_branches_do_not_count_unreached_work(self):
        for outcome, selected, excluded in [('OK', 'B', 'X'), ('KO', 'X', 'B')]:
            with self.subTest(outcome=outcome):
                self.service = OrganizationalPracticeService(seed_demo=False)
                self.create([node('A', {'OK': ['B'], 'KO': ['X']}, ['OK', 'KO']),
                             node('B', {'*': ['C']}), node('C'), node('X')])
                self.complete('A', outcome)
                self.assertEqual(self.active(), [selected])
                self.assertNotIn(excluded, self.summary()['active_tasks'])
                p = self.complete(selected)
                if selected == 'B': p = self.complete('C')
                self.assertEqual(p['status'], 'COMPLETATA')
                self.assertEqual(self.summary()['progress']['percent'], 100)
                self.assertEqual(p['progress']['total'], 3 if selected == 'B' else 2)
                self.assertFalse(next(t for t in p['tasks'] if t['code'] == excluded)['active'])
                self.assertEqual(len(p['tasks']), 4)  # Complete definition remains in dossier.
                self.assertEqual([r['related_task_code'] for r in reversed(p['results'])],
                                 ['A', 'B', 'C'] if selected == 'B' else ['A', 'X'])

    def test_parallel_terminal_waits_for_every_reached_node_even_optional(self):
        self.create([node('A', {'*': ['B', 'C']}), node('B', {'*': ['@END']}), node('C', required=False)])
        self.complete('A')
        self.assertEqual(self.active(), ['B', 'C'])
        self.assertEqual(self.complete('B')['status'], 'IN_LAVORAZIONE')
        with self.assertRaises(WorkflowError): self.service.close_for(self.pid, SUP)
        self.assertEqual(self.complete('C')['status'], 'COMPLETATA')

    def test_merge_activates_once_on_first_arrival(self):
        self.create([node('A', {'*': ['B', 'C']}), node('B', {'*': ['D']}),
                     node('C', {'*': ['D']}), node('D')])
        self.complete('A'); self.complete('B'); self.complete('D')
        self.assertEqual(self.active(), ['C'])
        self.assertEqual(self.complete('C')['status'], 'COMPLETATA')
        self.assertEqual(self.active(), [])

    def test_validation_and_closure_follow_only_selected_path(self):
        self.create([node('A', {'STOP': ['@END'], 'GO': ['B']}, ['STOP', 'GO']), node('B')], validation=True)
        self.assertEqual(self.complete('A', 'STOP')['status'], 'DA_VALIDARE')
        with self.assertRaises(WorkflowError): self.service.close_for(self.pid, SUP)
        self.service.validate_for(self.pid, VAL)
        p = self.service.close_for(self.pid, SUP)
        self.assertEqual(p['status'], 'CHIUSA')
        self.assertEqual(p['progress'], {'completed': 1, 'total': 1})

    def test_inactive_actions_leave_no_claim_or_audit(self):
        p = self.create([node('A', {'*': ['B']}), node('B')])
        for action in (self.service.complete_task_for, self.service.save_task_progress_for):
            with self.assertRaises(WorkflowError): action(self.pid, 'B', OP)
            self.assertEqual(self.service.get_for(self.pid, ADMIN), p)

    def test_correction_preserves_path_and_rejects_rerouting(self):
        self.create([node('A', {'OK': ['B'], 'KO': ['C']}, ['OK', 'KO']), node('B'), node('C')])
        self.complete('A', 'OK'); self.complete('B')
        self.service.reopen_task_for(self.pid, 'A', SUP, 'Correggere nota')
        before = self.service.get_for(self.pid, ADMIN)
        with self.assertRaises(WorkflowError): self.complete('A', 'KO')
        self.assertEqual(self.service.get_for(self.pid, ADMIN), before)
        p = self.complete('A', 'OK')
        self.assertEqual(p['status'], 'COMPLETATA')
        self.assertFalse(p['tasks'][2]['active'])
        self.assertEqual(len(p['results']), 3)

    def test_reject_cycles_missing_destinations_and_legacy_prerequisites(self):
        for tasks in ([node('A', {'*': ['A']})], [node('A', {'*': ['B']}), node('B', {'*': ['A']})],
                      [node('A', {'*': ['missing']})], [node('A', depends_on=['B']), node('B')],
                      [node('@END')], [node('A', {'UNKNOWN': ['@END']})]):
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                validate_model({'tasks': copy.deepcopy(tasks)}, self.config.list('groups'))

    def test_specific_outcome_overrides_default_transition(self):
        self.create([node('A', {'*': ['B'], 'STOP': []}, ['GO', 'STOP']), node('B')])
        self.assertEqual(self.complete('A', 'STOP')['status'], 'COMPLETATA')
        self.assertEqual(self.active(), [])

    def test_layout_is_validated_persisted_and_copied_without_affecting_activation(self):
        p = self.create([node('A', {'*': ['B']}, graph_position={'x': 600, 'y': 75}), node('B')])
        self.assertEqual(p['tasks'][0]['graph_position'], {'x': 600, 'y': 75})
        self.assertEqual(self.active(), ['A'])
        self.service = OrganizationalPracticeService(state_path=self.path, seed_demo=False)
        self.assertEqual(self.service.get_for(self.pid, ADMIN)['tasks'][0]['graph_position'], {'x': 600, 'y': 75})
        model = next(m for m in self.config.list('practice_types') if m['id']=='GRAPH')
        model['tasks'][0]['graph_position'] = {'x': 5, 'y': 5}
        self.config.save('practice_types', model)
        self.assertEqual(self.service.get_for(self.pid, ADMIN)['tasks'][0]['graph_position'], {'x': 600, 'y': 75})
        for position in ({'x': True, 'y': 1}, {'x': float('nan'), 'y': 1}, {'x': 100001, 'y': 1}, {'x': '5', 'y': 2}, {'x': 1}, []):
            with self.subTest(position=position), self.assertRaises(ValueError):
                validate_model({'tasks': [node('A', graph_position=position)]}, self.config.list('groups'))
