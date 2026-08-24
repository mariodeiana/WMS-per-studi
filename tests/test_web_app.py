import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.wms_web.app import WMSRequestHandler, create_server
from backend.wms_web.service import DEMO_PRACTICE_ID, PracticeService


class WebAppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WMSRequestHandler.service = PracticeService()
        cls.server = create_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, method="GET", body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = Request(self.url + path, data=data, method=method, headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            return response.status, response.read(), response.headers.get_content_type()

    def setUp(self):
        WMSRequestHandler.service = PracticeService()

    def test_serves_practice_page_and_health(self):
        status, page, content_type = self.request("/")
        self.assertEqual((status, content_type), (200, "text/html"))
        self.assertIn(b"Scheda pratica LIPE_TRIM", page)
        status, body, _ = self.request("/api/health")
        self.assertEqual(json.loads(body), {"status": "ok"})

    def test_api_drives_complete_workflow(self):
        for index in range(1, 8):
            path = f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-{index:02}/complete"
            _, body, _ = self.request(path, "POST", {"actor": "operatore"})
        self.assertEqual(json.loads(body)["status"], "DA_VALIDARE")
        _, body, _ = self.request(
            f"/api/practices/{DEMO_PRACTICE_ID}/validate",
            "POST",
            {"actor": "responsabile", "actor_role": "RESPONSABILE"},
        )
        self.assertEqual(json.loads(body)["status"], "VALIDATA")
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {"actor": "responsabile"})
        self.assertEqual(json.loads(body)["status"], "CHIUSA")

    def test_validation_requires_responsabile_role(self):
        for index in range(1, 8):
            path = f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-{index:02}/complete"
            self.request(path, "POST", {"actor": "operatore"})

        with self.assertRaises(HTTPError) as context:
            self.request(
                f"/api/practices/{DEMO_PRACTICE_ID}/validate",
                "POST",
                {"actor": "operatore", "actor_role": "OPERATORE"},
            )

        self.assertEqual(context.exception.code, 409)
        context.exception.close()
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}")
        self.assertEqual(json.loads(body)["status"], "DA_VALIDARE")

    def test_completed_task_can_be_reopened_through_api(self):
        for index in range(1, 8):
            path = f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-{index:02}/complete"
            self.request(path, "POST", {"actor": "operatore"})

        _, body, _ = self.request(
            f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-03/reopen",
            "POST",
            {"actor": "operatore"},
        )
        practice = json.loads(body)

        self.assertEqual(practice["status"], "IN_LAVORAZIONE")
        self.assertEqual(practice["progress"], {"completed": 6, "total": 7})
        self.assertEqual(practice["tasks"][2]["status"], "IN_LAVORAZIONE")
        self.assertTrue(any(event["event_type"] == "TASK_REOPENED" for event in practice["audit"]))

    def test_early_close_returns_409_and_preserves_state(self):
        with self.assertRaises(HTTPError) as context:
            self.request(
                f"/api/practices/{DEMO_PRACTICE_ID}/close",
                "POST",
                {"actor": "responsabile"},
            )

        self.assertEqual(context.exception.code, 409)
        context.exception.close()
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}")
        self.assertEqual(json.loads(body)["status"], "DA_FARE")

    def test_demo_assignments_are_exposed_by_application_layer(self):
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}")
        self.assertEqual(
            json.loads(body)["assignments"],
            {"responsible": "Dott.ssa Giulia Bianchi", "operator": "Marco Rossi"},
        )

    def test_unknown_practice_returns_404(self):
        with self.assertRaises(HTTPError) as context:
            self.request("/api/practices/UNKNOWN")
        self.assertEqual(context.exception.code, 404)
        context.exception.close()


if __name__ == "__main__":
    unittest.main()
