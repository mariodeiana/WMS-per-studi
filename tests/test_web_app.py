import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from backend.wms_web.app import WMSRequestHandler, create_server
from backend.wms_web.service import DEMO_PRACTICE_ID, PracticeService


class WebAppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def setUp(self):
        WMSRequestHandler.service = PracticeService()

    def request(self, path, method="GET", body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = Request(self.url + path, data=data, method=method, headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            return response.status, response.read(), response.headers.get_content_type()

    def error(self, path, method="GET", body=None):
        with self.assertRaises(HTTPError) as context:
            self.request(path, method, body)
        code = context.exception.code
        context.exception.close()
        return code

    def complete(self, code, actor):
        return self.request(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/{code}/complete", "POST", {"actor": actor})

    def test_serves_manager_queue_task_and_validation_views(self):
        for path, marker in [("/", b"Scheda Pratica Manager"), ("/queue.html", b"I miei compiti"),
                             ("/task.html", b"Attivit\xc3\xa0 Operatore"), ("/validation.html", b"Validazione Pratica")]:
            status, page, content_type = self.request(path)
            self.assertEqual((status, content_type), (200, "text/html"))
            self.assertIn(marker, page)

    def test_demo_assignments_are_split_between_two_operators(self):
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}")
        practice = json.loads(body)
        self.assertEqual({task["assignee"] for task in practice["tasks"]}, {"anna.operatore", "luca.operatore"})
        self.assertTrue(all("completed_by" in task and "depends_on" in task for task in practice["tasks"]))
        self.assertEqual(sum(event["event_type"] == "TASK_ASSIGNED" for event in practice["audit"]), 7)

    def test_manager_can_reassign_task_and_assignment_is_audited(self):
        _, body, _ = self.request(
            f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/assign",
            "POST",
            {"actor": "marta.manager", "assignee": "luca.operatore"},
        )
        practice = json.loads(body)
        self.assertEqual(practice["tasks"][0]["assignee"], "luca.operatore")
        self.assertEqual(practice["audit"][0]["event_type"], "TASK_ASSIGNED")
        self.assertEqual(
            self.error(
                f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/assign",
                "POST",
                {"actor": "anna.operatore", "assignee": "luca.operatore"},
            ),
            409,
        )

    def test_operator_queue_and_minimal_task_detail_are_scoped(self):
        _, body, _ = self.request("/api/work-queue?operator=anna.operatore")
        queue = json.loads(body)
        self.assertEqual([item["code"] for item in queue], ["LIPE-01", "LIPE-03", "LIPE-05", "LIPE-07"])
        _, body, _ = self.request(f"/api/tasks/{DEMO_PRACTICE_ID}/LIPE-01?operator=anna.operatore")
        detail = json.loads(body)
        self.assertEqual(set(detail), {"practice", "task", "task_progress_evidence", "task_journal"})
        self.assertEqual(detail["task_progress_evidence"], [])
        self.assertEqual(detail["task_journal"], [])
        self.assertEqual(self.error(f"/api/tasks/{DEMO_PRACTICE_ID}/LIPE-01?operator=luca.operatore"), 403)

    def test_tasks_complete_out_of_definition_order(self):
        plan = [("LIPE-07", "anna.operatore"), ("LIPE-02", "luca.operatore"),
                ("LIPE-05", "anna.operatore"), ("LIPE-04", "luca.operatore"),
                ("LIPE-01", "anna.operatore"), ("LIPE-06", "luca.operatore"),
                ("LIPE-03", "anna.operatore")]
        for code, actor in plan:
            _, body, _ = self.complete(code, actor)
        practice = json.loads(body)
        self.assertEqual(practice["status"], "DA_VALIDARE")
        self.assertEqual(practice["tasks"][6]["completed_by"], "anna.operatore")

    def test_wrong_operator_and_wrong_roles_are_rejected(self):
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/complete", "POST", {"actor": "luca.operatore"}), 409)
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/complete", "POST", {"actor": "marta.manager"}), 409)
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {"actor": "valeria.validatore"}), 409)

    def test_executor_cannot_self_validate_and_manager_closes(self):
        for index in range(1, 8):
            actor = "anna.operatore" if index % 2 else "luca.operatore"
            self.complete(f"LIPE-{index:02}", actor)
        from backend.wms_web import service
        original = service.DEMO_USERS["anna.operatore"]
        service.DEMO_USERS["anna.operatore"] = service.UserRole.VALIDATORE
        try:
            self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/validate", "POST", {"actor": "anna.operatore"}), 409)
        finally:
            service.DEMO_USERS["anna.operatore"] = original
        self.request(f"/api/practices/{DEMO_PRACTICE_ID}/validate", "POST", {"actor": "valeria.validatore"})
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {"actor": "valeria.validatore"}), 409)
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {"actor": "marta.manager"})
        self.assertEqual(json.loads(body)["status"], "CHIUSA")
        self.assertEqual(json.loads(body)["audit"][0]["event_type"], "PRACTICE_CLOSED")

    def test_early_close_returns_409(self):
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {"actor": "marta.manager"}), 409)

    def test_task_result_and_evidence_are_exposed_to_manager_and_context(self):
        _, body, _ = self.request(
            f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/complete", "POST",
            {"actor": "anna.operatore", "outcome": "POSITIVO", "note": "Dati completi",
             "attachments": [{"filename": "verifica.pdf", "content_type": "application/pdf"}]},
        )
        practice = json.loads(body)
        self.assertEqual(practice["results"][0]["note"], "Dati completi")
        self.assertEqual(practice["evidence"][0]["filename"], "verifica.pdf")
        _, body, _ = self.request(
            f"/api/tasks/{DEMO_PRACTICE_ID}/LIPE-03?operator=anna.operatore&context=1"
        )
        context = json.loads(body)
        self.assertEqual(context["previous_results"][0]["related_task_code"], "LIPE-01")
        self.assertEqual(context["evidence"][0]["source"], "TASK")


if __name__ == "__main__":
    unittest.main()
