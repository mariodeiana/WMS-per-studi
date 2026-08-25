import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from wms_core.models import Practice, PracticeStatus, Task, UserRole
from wms_core.templates import build_lipe_trim_tasks
from wms_core.workflow import WorkflowError, assign_task, close_practice, complete_task, reopen_task, validate_practice


class LipeWorkflowTest(unittest.TestCase):
    def build_practice(self) -> Practice:
        practice = Practice(
            id="P-2026-0001", practice_type_code="LIPE_TRIM", client_id="CLIENT-001",
            period_start="2026-04-01", period_end="2026-06-30", due_date="2026-09-30",
            tasks=build_lipe_trim_tasks(),
        )
        for index, task in enumerate(practice.tasks):
            assign_task(practice, task.code, "anna" if index % 2 == 0 else "luca", "manager", UserRole.MANAGER)
        return practice

    def complete_all_out_of_order(self, practice: Practice) -> None:
        for index in (6, 0, 4, 1, 5, 2, 3):
            task = practice.tasks[index]
            complete_task(practice, task.code, task.assignee, UserRole.OPERATORE)

    def test_out_of_order_end_to_end_with_roles_and_audit(self):
        practice = self.build_practice()
        self.complete_all_out_of_order(practice)
        self.assertEqual(practice.status, PracticeStatus.DA_VALIDARE)
        validate_practice(practice, "valeria", UserRole.VALIDATORE)
        close_practice(practice, "manager", UserRole.MANAGER)
        self.assertEqual(practice.status, PracticeStatus.CHIUSA)
        events = [event.event_type for event in practice.audit]
        self.assertIn("TASK_ASSIGNED", events)
        self.assertIn("PRACTICE_VALIDATED", events)
        self.assertIn("PRACTICE_CLOSED", events)

    def test_only_assignee_operator_can_complete(self):
        practice = self.build_practice()
        with self.assertRaises(WorkflowError):
            complete_task(practice, "LIPE-01", "luca", UserRole.OPERATORE)
        with self.assertRaises(WorkflowError):
            complete_task(practice, "LIPE-01", "anna", UserRole.MANAGER)

    def test_explicit_dependency_is_enforced_but_graphic_order_is_not(self):
        practice = Practice("P", "GENERIC", "C", "2026-01-01", "2026-01-31", "2026-02-01", tasks=[
            Task("FIRST", "First", assignee="anna"),
            Task("SECOND", "Second", assignee="anna", depends_on=("FIRST",)),
            Task("INDEPENDENT", "Independent", assignee="anna"),
        ])
        complete_task(practice, "INDEPENDENT", "anna", UserRole.OPERATORE)
        with self.assertRaises(WorkflowError):
            complete_task(practice, "SECOND", "anna", UserRole.OPERATORE)

    def test_executor_cannot_validate_same_practice(self):
        practice = self.build_practice()
        self.complete_all_out_of_order(practice)
        with self.assertRaises(WorkflowError):
            validate_practice(practice, "anna", UserRole.VALIDATORE)

    def test_closure_is_manager_only(self):
        practice = self.build_practice()
        self.complete_all_out_of_order(practice)
        validate_practice(practice, "valeria", UserRole.VALIDATORE)
        with self.assertRaises(WorkflowError):
            close_practice(practice, "valeria", UserRole.VALIDATORE)

    def test_manager_reopens_and_clears_completion_author(self):
        practice = self.build_practice()
        self.complete_all_out_of_order(practice)
        reopen_task(practice, "LIPE-03", "manager", UserRole.MANAGER)
        self.assertEqual(practice.status, PracticeStatus.IN_LAVORAZIONE)
        self.assertIsNone(practice.tasks[2].completed_by)
        self.assertEqual(practice.audit[-2].event_type, "TASK_REOPENED")

    def test_reopening_does_not_erase_separation_of_duties_history(self):
        practice = self.build_practice()
        self.complete_all_out_of_order(practice)
        reopen_task(practice, "LIPE-03", "manager", UserRole.MANAGER)
        assign_task(practice, "LIPE-03", "luca", "manager", UserRole.MANAGER)
        complete_task(practice, "LIPE-03", "luca", UserRole.OPERATORE)
        with self.assertRaises(WorkflowError):
            validate_practice(practice, "anna", UserRole.VALIDATORE)


if __name__ == "__main__":
    unittest.main()
