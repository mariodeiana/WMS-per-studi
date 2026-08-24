import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.wms_core.models import PracticeStatus  # noqa: E402
from backend.wms_web.app import WMSHandler  # noqa: E402
from backend.wms_web.store import demo_store  # noqa: E402


class WebEndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), WMSHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        WMSHandler.store = demo_store()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return response.status, response.read().decode(), response.headers["Content-Type"]

    def post(self, path, fields):
        request = Request(self.base + path, data=urlencode(fields, doseq=True).encode(), method="POST")
        with urlopen(request) as response:
            return response.status, response.geturl(), response.read().decode()

    def complete_all(self):
        practice = WMSHandler.store.get("P-2026-0001")
        for task in practice.tasks:
            self.post(
                f"/practices/{practice.id}/tasks/{task.code}/complete",
                {"actor": task.assigned_to, "outcome": "OK", "note": f"Nota {task.code}",
                 "evidence_name": f"{task.code}.pdf", "evidence_ref": f"memory://{task.code}"},
            )
        return practice

    def test_work_queue_task_card_and_structured_completion(self):
        status, queue, _ = self.get("/?actor=mario")
        self.assertEqual(status, 200)
        self.assertIn("Work Queue personale", queue)
        self.assertIn("LIPE-01", queue)
        _, card, _ = self.get("/practices/P-2026-0001/tasks/LIPE-01")
        self.assertIn("Istruzioni operative", card)
        self.assertIn("Verifica che tutti i dati IVA", card)
        self.assertIn("Outcome / esito", card)
        self.assertIn("Allegati / evidenze", card)
        self.post("/practices/P-2026-0001/tasks/LIPE-01/complete", {
            "actor": "mario", "outcome": "POSITIVO", "note": "Dati presenti",
            "evidence_name": ["registro.pdf", "check.csv"],
            "evidence_ref": ["memory://registro", "memory://check"],
        })
        task = WMSHandler.store.get("P-2026-0001").tasks[0]
        self.assertEqual(task.result.note, "Dati presenti")
        self.assertEqual(len(task.result.attachments), 2)
        _, api, content_type = self.get("/api/practices/P-2026-0001/tasks/LIPE-01")
        self.assertEqual(content_type, "application/json")
        self.assertEqual(json.loads(api)["evidence"][0]["name"], "registro.pdf")

    def test_validator_manager_dossier_audit_and_closure(self):
        practice = self.complete_all()
        _, validator_page, _ = self.get("/validate/P-2026-0001")
        self.assertIn("Nota LIPE-01", validator_page)
        self.assertIn("LIPE-01.pdf", validator_page)
        self.assertIn("Valida pratica", validator_page)
        self.post("/validate/P-2026-0001/submit", {
            "actor": "valeria", "outcome": "APPROVATA", "note": "Controlli positivi",
            "evidence_name": "validazione.pdf", "evidence_ref": "memory://validazione",
        })
        self.assertEqual(practice.status, PracticeStatus.VALIDATA)
        _, manager_page, _ = self.get("/practices/P-2026-0001")
        self.assertIn("Controlli positivi", manager_page)
        self.assertIn("Fascicolo", manager_page)
        self.assertIn("Audit (separato dal fascicolo)", manager_page)
        self.assertIn("Chiudi pratica", manager_page)
        self.post("/practices/P-2026-0001/close", {
            "actor": "manager", "outcome": "ARCHIVIATA", "note": "Chiusura verificata",
            "evidence_name": "chiusura.pdf", "evidence_ref": "memory://chiusura",
        })
        self.assertEqual(practice.status, PracticeStatus.CHIUSA)
        _, api, _ = self.get("/api/practices/P-2026-0001")
        data = json.loads(api)
        self.assertEqual(data["closure_result"]["note"], "Chiusura verificata")
        self.assertEqual(len(data["dossier"]), 9)
        self.assertTrue(data["audit"])

    def test_separation_of_duties_and_manager_reopen(self):
        practice = self.complete_all()
        with self.assertRaises(HTTPError) as context:
            self.post("/validate/P-2026-0001/submit", {"actor": "mario", "outcome": "OK"})
        self.assertEqual(context.exception.code, 409)
        context.exception.close()
        self.post("/practices/P-2026-0001/tasks/LIPE-01/reopen", {"actor": "manager"})
        self.assertEqual(practice.status, PracticeStatus.IN_LAVORAZIONE)
        self.assertIsNone(practice.tasks[0].result)
        self.assertEqual(practice.audit[-1].event_type, "TASK_REOPENED")


if __name__ == "__main__":
    unittest.main()
