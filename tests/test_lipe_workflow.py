import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from wms_core.models import Practice, PracticeStatus
from wms_core.templates import build_lipe_trim_tasks
from wms_core.workflow import WorkflowError, close_practice, complete_task, reopen_task, validate_practice


class LipeWorkflowTest(unittest.TestCase):
    def build_practice(self) -> Practice:
        return Practice(
            id="P-2026-0001",
            practice_type_code="LIPE_TRIM",
            client_id="CLIENT-001",
            period_start="2026-04-01",
            period_end="2026-06-30",
            due_date="2026-09-30",
            tasks=build_lipe_trim_tasks(),
        )

    def test_end_to_end_lipe(self):
        practice = self.build_practice()

        for task in practice.tasks:
            complete_task(practice, task.code, actor="operatore")

        self.assertEqual(practice.status, PracticeStatus.DA_VALIDARE)

        validate_practice(practice, actor="responsabile", actor_can_validate=True)
        self.assertEqual(practice.status, PracticeStatus.VALIDATA)

        close_practice(practice, actor="responsabile")
        self.assertEqual(practice.status, PracticeStatus.CHIUSA)
        self.assertGreaterEqual(len(practice.audit), 12)

    def test_unauthorized_validation_is_rejected(self):
        practice = self.build_practice()
        for task in practice.tasks:
            complete_task(practice, task.code, actor="operatore")

        with self.assertRaises(WorkflowError):
            validate_practice(practice, actor="operatore", actor_can_validate=False)

    def test_early_close_is_rejected(self):
        practice = self.build_practice()
        with self.assertRaises(WorkflowError):
            close_practice(practice, actor="responsabile")

    def test_completed_task_can_be_reopened_before_validation(self):
        practice = self.build_practice()
        for task in practice.tasks:
            complete_task(practice, task.code, actor="operatore")

        reopen_task(practice, "LIPE-03", actor="operatore")

        self.assertEqual(practice.status, PracticeStatus.IN_LAVORAZIONE)
        self.assertEqual(practice.tasks[2].status.value, "IN_LAVORAZIONE")
        self.assertEqual(practice.audit[-2].event_type, "TASK_REOPENED")

    def test_task_cannot_be_reopened_after_validation(self):
        practice = self.build_practice()
        for task in practice.tasks:
            complete_task(practice, task.code, actor="operatore")
        validate_practice(practice, actor="responsabile", actor_can_validate=True)

        with self.assertRaises(WorkflowError):
            reopen_task(practice, "LIPE-03", actor="operatore")


if __name__ == "__main__":
    unittest.main()
