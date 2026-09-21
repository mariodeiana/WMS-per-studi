import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from wms_core.models import NonConformityStatus, Practice, PracticeStatus, Task, TaskStatus, UserRole
from wms_core.templates import build_lipe_trim_tasks
from wms_core.workflow import WorkflowError, assign_task, close_practice, complete_task, define_corrective_action, reopen_task, save_task_progress, validate_practice


class LipeWorkflowTest(unittest.TestCase):
    def build_practice(self) -> Practice:
        practice = Practice(
            id="P-2026-0001", practice_type_code="LIPE_TRIM", client_id="000001",
            period_start="2026-04-01", period_end="2026-06-30", due_date="2026-09-30",
            tasks=build_lipe_trim_tasks(),
        )
        for index, task in enumerate(practice.tasks):
            assign_task(practice, task.code, "anna" if index % 2 == 0 else "luca", "manager", UserRole.MANAGER)
        return practice

    def complete_all_in_sequence(self, practice: Practice) -> None:
        for index in range(7):
            task = practice.tasks[index]
            complete_task(practice, task.code, task.assignee, UserRole.OPERATORE)

    def test_sequence_end_to_end_with_roles_and_audit(self):
        practice = self.build_practice()
        self.complete_all_in_sequence(practice)
        self.assertEqual(practice.status, PracticeStatus.DA_VALIDARE)
        validate_practice(practice, "valeria", UserRole.VALIDATORE)
        close_practice(practice, "manager", UserRole.MANAGER)
        self.assertEqual(practice.status, PracticeStatus.CHIUSA)
        events = [event.event_type for event in practice.audit]
        self.assertIn("TASK_ASSIGNED", events)
        self.assertIn("PRACTICE_VALIDATED", events)
        self.assertIn("PRACTICE_CLOSED", events)

    def test_non_conformity_corrective_cycle(self):
        practice = self.build_practice()
        self.complete_all_in_sequence(practice)
        validate_practice(practice, "valeria", UserRole.VALIDATORE, "NON_VALIDATA", "Totali IVA non coerenti")
        self.assertEqual(practice.status, PracticeStatus.NON_VALIDATA)
        self.assertEqual(len(practice.nonconformities), 1)
        nc = practice.nonconformities[0]
        self.assertEqual((nc.id, nc.status), ("NC-0001", NonConformityStatus.APERTA))
        define_corrective_action(practice, "manager", UserRole.MANAGER, ["LIPE-03", "LIPE-04"], "Rieseguire elaborazione e controllo")
        self.assertEqual(practice.status, PracticeStatus.IN_LAVORAZIONE)
        self.assertEqual(nc.status, NonConformityStatus.IN_SANATORIA)
        self.assertIn("NC-0001", practice.tasks[2].reopen_reason)
        complete_task(practice, "LIPE-03", "anna", UserRole.OPERATORE, "POSITIVO", "Rielaborato")
        complete_task(practice, "LIPE-04", "luca", UserRole.OPERATORE, "POSITIVO", "Controllo corretto")
        self.assertEqual(practice.status, PracticeStatus.DA_VALIDARE)
        self.assertEqual(nc.status, NonConformityStatus.DA_VERIFICARE)
        validate_practice(practice, "valeria", UserRole.VALIDATORE, "VALIDATA", "Sanatoria verificata")
        self.assertEqual(practice.status, PracticeStatus.VALIDATA)
        self.assertEqual(nc.status, NonConformityStatus.CHIUSA)
        self.assertEqual(nc.closed_by, "valeria")

    def test_failed_nc_verification_reuses_same_non_conformity(self):
        practice = self.build_practice(); self.complete_all_in_sequence(practice)
        validate_practice(practice, "valeria", UserRole.VALIDATORE, "NON_VALIDATA", "Prima non conformità")
        define_corrective_action(practice, "manager", UserRole.MANAGER, ["LIPE-03"], "Correggere elaborazione")
        complete_task(practice, "LIPE-03", "anna", UserRole.OPERATORE)
        validate_practice(practice, "valeria", UserRole.VALIDATORE, "NON_VALIDATA", "Correzione ancora insufficiente")
        self.assertEqual(len(practice.nonconformities), 1)
        self.assertEqual(practice.nonconformities[0].status, NonConformityStatus.APERTA)
        self.assertEqual(practice.nonconformities[0].reason, "Correzione ancora insufficiente")

    def test_only_assignee_operator_can_complete(self):
        practice = self.build_practice()
        with self.assertRaises(WorkflowError): complete_task(practice, "LIPE-01", "luca", UserRole.OPERATORE)
        with self.assertRaises(WorkflowError): complete_task(practice, "LIPE-01", "anna", UserRole.MANAGER)

    def test_explicit_dependency_is_enforced_but_graphic_order_is_not(self):
        practice = Practice("P", "GENERIC", "C", "2026-01-01", "2026-01-31", "2026-02-01", tasks=[Task("FIRST", "First", assignee="anna"),Task("SECOND", "Second", assignee="anna", depends_on=("FIRST",)),Task("INDEPENDENT", "Independent", assignee="anna")])
        complete_task(practice, "INDEPENDENT", "anna", UserRole.OPERATORE)
        with self.assertRaises(WorkflowError): complete_task(practice, "SECOND", "anna", UserRole.OPERATORE)

    def build_fork_practice(self) -> Practice:
        return Practice(
            id="P-WF-001",
            practice_type_code="TEST_WORKFLOW",
            client_id="000001",
            period_start="2026-09-01",
            period_end="2026-09-30",
            due_date="2026-09-30",
            requires_validation=False,
            tasks=[
                Task(
                    "A", "Verifica cliente",
                    assignee="anna",
                    outcomes=("SI", "NO"),
                    transitions={"SI": ("B",), "NO": ("C",)},
                    active=True,
                ),
                Task("B", "Percorso SI", assignee="anna", active=False),
                Task("C", "Percorso NO", assignee="anna", active=False),
            ],
        )

    def test_workflow_outcome_si_activates_only_si_branch(self):
        practice = self.build_fork_practice()
        complete_task(practice, "A", "anna", UserRole.OPERATORE, "SI")
        self.assertTrue(practice.tasks[1].active)
        self.assertFalse(practice.tasks[2].active)
        complete_task(practice, "B", "anna", UserRole.OPERATORE)
        self.assertEqual(practice.status, PracticeStatus.COMPLETATA)

    def test_workflow_outcome_no_activates_only_no_branch(self):
        practice = self.build_fork_practice()
        complete_task(practice, "A", "anna", UserRole.OPERATORE, "NO")
        self.assertFalse(practice.tasks[1].active)
        self.assertTrue(practice.tasks[2].active)
        complete_task(practice, "C", "anna", UserRole.OPERATORE)
        self.assertEqual(practice.status, PracticeStatus.COMPLETATA)

    def test_workflow_rejects_unconfigured_outcome(self):
        practice = self.build_fork_practice()
        with self.assertRaises(WorkflowError):
            complete_task(practice, "A", "anna", UserRole.OPERATORE, "FORSE")

    def test_workflow_rejects_inactive_task(self):
        practice = self.build_fork_practice()
        with self.assertRaises(WorkflowError):
            complete_task(practice, "B", "anna", UserRole.OPERATORE)

    def test_workflow_rejects_progress_on_inactive_task(self):
        practice = self.build_fork_practice()
        with self.assertRaises(WorkflowError):
            save_task_progress(
                practice,
                "B",
                "anna",
                UserRole.OPERATORE,
                "Tentativo anticipato",
            )

    def test_executor_cannot_validate_same_practice(self):
        practice = self.build_practice(); self.complete_all_in_sequence(practice)
        with self.assertRaises(WorkflowError): validate_practice(practice, "anna", UserRole.VALIDATORE)

    def test_closure_is_manager_only(self):
        practice = self.build_practice(); self.complete_all_in_sequence(practice); validate_practice(practice, "valeria", UserRole.VALIDATORE)
        with self.assertRaises(WorkflowError): close_practice(practice, "valeria", UserRole.VALIDATORE)

    def test_task_can_be_saved_in_progress_and_resumed(self):
        practice = self.build_practice(); save_task_progress(practice, "LIPE-01", "anna", UserRole.OPERATORE, "Controllati i primi registri")
        self.assertEqual(practice.tasks[0].status, TaskStatus.IN_LAVORAZIONE); self.assertEqual(practice.tasks[0].work_note, "Controllati i primi registri")
        save_task_progress(practice, "LIPE-01", "anna", UserRole.OPERATORE, "Controllo quasi concluso"); self.assertEqual(practice.tasks[0].work_note, "Controllo quasi concluso")
        complete_task(practice, "LIPE-01", "anna", UserRole.OPERATORE, "POSITIVO", "Concluso"); self.assertEqual(practice.tasks[0].status, TaskStatus.COMPLETATO); self.assertEqual(practice.tasks[0].work_note, "")

    def test_manager_reopens_and_clears_completion_author(self):
        practice = self.build_practice(); self.complete_all_in_sequence(practice); reopen_task(practice, "LIPE-03", "manager", UserRole.MANAGER, "Rivedere il prospetto")
        self.assertEqual(practice.status, PracticeStatus.IN_LAVORAZIONE); self.assertIsNone(practice.tasks[2].completed_by); self.assertEqual(practice.tasks[2].reopen_reason, "Rivedere il prospetto"); self.assertEqual(practice.audit[-2].event_type, "TASK_REOPENED")

    def test_reopen_requires_reason(self):
        practice = self.build_practice(); complete_task(practice, "LIPE-01", "anna", UserRole.OPERATORE)
        with self.assertRaises(WorkflowError): reopen_task(practice, "LIPE-01", "manager", UserRole.MANAGER, "")

    def test_reopening_does_not_erase_separation_of_duties_history(self):
        practice = self.build_practice(); self.complete_all_in_sequence(practice); reopen_task(practice, "LIPE-03", "manager", UserRole.MANAGER, "Secondo controllo"); assign_task(practice, "LIPE-03", "luca", "manager", UserRole.MANAGER); complete_task(practice, "LIPE-03", "luca", UserRole.OPERATORE)
        with self.assertRaises(WorkflowError): validate_practice(practice, "anna", UserRole.VALIDATORE)

    def test_structured_results_and_evidence_are_separate_from_audit(self):
        practice = self.build_practice(); complete_task(practice, "LIPE-01", "anna", UserRole.OPERATORE,"POSITIVO", "Registri verificati",[{"filename": "controllo.pdf", "content_type": "application/pdf"}])
        result = practice.results[0]; self.assertEqual((result.actor, result.actor_role, result.outcome),("anna", UserRole.OPERATORE, "POSITIVO")); self.assertEqual(result.evidence_ids, (practice.evidence[0].id,)); self.assertEqual(practice.tasks[0].result_id, result.id); self.assertEqual(next(e for e in reversed(practice.audit) if e.event_type == "TASK_COMPLETED").details["result_id"], result.id)

    def test_reopening_preserves_result_and_dossier_history(self):
        practice = self.build_practice(); complete_task(practice, "LIPE-01", "anna", UserRole.OPERATORE,"POSITIVO", "Prima lavorazione", [{"filename": "prima.txt"}]); reopen_task(practice, "LIPE-01", "manager", UserRole.MANAGER, "Rifare il controllo")
        self.assertIsNone(practice.tasks[0].result_id); self.assertEqual(len(practice.results), 1); self.assertEqual(len(practice.evidence), 1)

if __name__ == "__main__": unittest.main()
