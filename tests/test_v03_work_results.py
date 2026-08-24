import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from wms_core import EvidenceInput, EvidenceOrigin, Practice, PracticeStatus, Role, Task, WorkflowError, close_practice, complete_task, manager_practice_view, task_detail, validate_practice, validator_view


class V03WorkflowTest(unittest.TestCase):
    def practice(self, tasks):
        return Practice("P-03", "LIPE_TRIM", "C-1", "2026-04-01", "2026-06-30", "2026-09-30", client_name="Cliente Demo", context={"regime": "trimestrale"}, tasks=tasks)

    def test_task_result_evidence_and_context(self):
        p = self.practice([Task("T-1", "Lavoro", assignee="op-1", instructions="Istruzione")])
        result = complete_task(p, "T-1", "op-1", outcome="OK", note="Controllo eseguito", attachments=[EvidenceInput("prospetto.pdf", "memory://prospetto")])
        self.assertEqual(result.attachments[0].origin, EvidenceOrigin.TASK)
        self.assertEqual(p.dossier[0].id, result.attachments[0].id)
        detail = task_detail(p, "T-1")
        self.assertEqual(detail["instructions"], "Istruzione")
        self.assertEqual(detail["note"], "Controllo eseguito")

    def test_validation_and_closure_results(self):
        p = self.practice([Task("T-1", "Lavoro", assignee="op-1")])
        complete_task(p, "T-1", "op-1", note="Operatore", attachments=[{"name": "task.txt"}])
        validate_practice(p, "val-1", note="Verifica positiva", attachments=[{"name": "check.txt"}])
        close_practice(p, "manager-1", note="Chiusura definitiva", attachments=[{"name": "riepilogo.txt"}])
        view = manager_practice_view(p)
        self.assertEqual(view["validation_result"]["note"], "Verifica positiva")
        self.assertEqual(view["closure_result"]["note"], "Chiusura definitiva")
        self.assertEqual(len(view["dossier"]), 3)

    def test_out_of_order_and_roles_remain_enforced(self):
        p = self.practice([Task("A", "Prima", assignee="op-1"), Task("B", "Indipendente", assignee="op-1"), Task("C", "Dipendente", assignee="op-1", depends_on=("A",))])
        complete_task(p, "B", "op-1")
        with self.assertRaises(WorkflowError):
            complete_task(p, "C", "op-1")
        with self.assertRaises(WorkflowError):
            complete_task(p, "A", "val-1", actor_role=Role.VALIDATORE)
        complete_task(p, "A", "op-1")
        complete_task(p, "C", "op-1")
        self.assertEqual(p.status, PracticeStatus.DA_VALIDARE)
        with self.assertRaises(WorkflowError):
            validate_practice(p, "op-1")

    def test_validator_sees_operator_results(self):
        p = self.practice([Task("T-1", "Lavoro", assignee="op-1")])
        complete_task(p, "T-1", "op-1", note="Nota visibile")
        self.assertEqual(validator_view(p)["completed_tasks"][0]["note"], "Nota visibile")


if __name__ == "__main__":
    unittest.main()
