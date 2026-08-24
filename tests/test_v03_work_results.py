import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from wms_core import (  # noqa: E402
    EvidenceInput, EvidenceOrigin, Practice, PracticeStatus, Role, Task,
    WorkflowError, close_practice, complete_task, manager_practice_view,
    operator_work_queue, task_detail, validate_practice, validator_view,
)
from wms_core.templates import build_lipe_trim_tasks  # noqa: E402


class V03WorkflowTest(unittest.TestCase):
    def build_practice(self, tasks=None):
        return Practice(
            id="P-03", practice_type_code="LIPE_TRIM", client_id="C-1",
            client_name="Cliente Demo", period_start="2026-04-01", period_end="2026-06-30",
            due_date="2026-09-30", context={"regime": "trimestrale"},
            tasks=tasks or build_lipe_trim_tasks(),
        )

    def complete_all(self, practice):
        for task in practice.tasks:
            task.assigned_to = "op-1"
            complete_task(practice, task.code, "op-1", note=f"Nota {task.code}")

    def test_task_result_evidence_dossier_and_audit_are_separate(self):
        practice = self.build_practice([Task("T-1", "Lavoro", instructions="Istruzione", assigned_to="op-1")])
        result = complete_task(
            practice, "T-1", "op-1", outcome="OK", note="Controllo eseguito",
            attachments=[EvidenceInput("prospetto.pdf", "memory://prospetto", {"mime": "application/pdf"})],
        )
        self.assertEqual((result.outcome, result.note, result.actor_role), ("OK", "Controllo eseguito", Role.OPERATORE))
        self.assertEqual(result.attachments[0].origin, EvidenceOrigin.TASK)
        self.assertEqual(practice.dossier[0].id, result.attachments[0].id)
        self.assertNotIn(practice.dossier[0], practice.audit)
        self.assertIn("WORK_RESULT_RECORDED", [event.event_type for event in practice.audit])
        self.assertIn("EVIDENCE_ADDED", [event.event_type for event in practice.audit])

    def test_validation_and_closure_results_are_visible_to_manager(self):
        practice = self.build_practice([Task("T-1", "Lavoro", assigned_to="op-1")])
        complete_task(practice, "T-1", "op-1", outcome="OK", note="Operatore",
                      attachments=[{"name": "task.txt", "content_ref": "memory://task"}])
        validation = validate_practice(
            practice, "val-1", outcome="APPROVATA", note="Verifica positiva",
            attachments=[{"name": "check.txt", "content_ref": "memory://check"}],
        )
        closure = close_practice(
            practice, "manager-1", outcome="ARCHIVIATA", note="Chiusura definitiva",
            attachments=[{"name": "riepilogo.txt", "content_ref": "memory://riepilogo"}],
        )
        self.assertEqual(validation.attachments[0].origin, EvidenceOrigin.VALIDATION)
        self.assertEqual(closure.attachments[0].origin, EvidenceOrigin.CLOSURE)
        view = manager_practice_view(practice)
        self.assertEqual(view["tasks"][0]["note"], "Operatore")
        self.assertEqual(view["validation_result"]["note"], "Verifica positiva")
        self.assertEqual(view["closure_result"]["note"], "Chiusura definitiva")
        self.assertEqual(len(view["dossier"]), 3)
        self.assertTrue(view["audit"])

    def test_validator_sees_operator_results_and_task_context(self):
        practice = self.build_practice([Task("T-1", "Lavoro", instructions="Dal template", assigned_to="op-1")])
        complete_task(practice, "T-1", "op-1", note="Nota visibile",
                      attachments=[{"name": "evidenza"}])
        validator = validator_view(practice)
        self.assertEqual(validator["completed_tasks"][0]["completed_by"], "op-1")
        self.assertEqual(validator["completed_tasks"][0]["note"], "Nota visibile")
        detail = task_detail(practice, "T-1")
        self.assertEqual(detail["instructions"], "Dal template")
        self.assertEqual(detail["context"]["regime"], "trimestrale")
        self.assertEqual(detail["action"], "Completa attività")

    def test_v02_out_of_order_assignments_dependencies_roles_and_separation(self):
        tasks = [
            Task("A", "Prima", assigned_to="op-1"),
            Task("B", "Indipendente", assigned_to="op-1"),
            Task("C", "Dipendente", assigned_to="op-1", depends_on=["A"]),
        ]
        practice = self.build_practice(tasks)
        self.assertEqual([task.code for _, task in operator_work_queue([practice], "op-1")], ["A", "B", "C"])
        complete_task(practice, "B", "op-1")  # fuori ordine, ma senza dipendenze
        with self.assertRaises(WorkflowError):
            complete_task(practice, "C", "op-1")
        with self.assertRaises(WorkflowError):
            complete_task(practice, "A", "op-2")
        with self.assertRaises(WorkflowError):
            complete_task(practice, "A", "val-1", actor_role=Role.VALIDATORE)
        complete_task(practice, "A", "op-1")
        complete_task(practice, "C", "op-1")
        self.assertEqual(practice.status, PracticeStatus.DA_VALIDARE)
        with self.assertRaises(WorkflowError):
            validate_practice(practice, "op-1")
        with self.assertRaises(WorkflowError):
            validate_practice(practice, "manager-1", actor_role=Role.MANAGER)


if __name__ == "__main__":
    unittest.main()
