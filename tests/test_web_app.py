import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from backend.wms_web.app import AUTH
from backend.wms_web.organization_service import OrganizationalPracticeService

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
        WMSRequestHandler.service = OrganizationalPracticeService()
        self.login("marta.manager")

    def login(self, actor):
        user, membership = {"marta.manager": ("mario.demo", "mario-manager"), "anna.operatore": ("mario.demo", "mario-contabili"), "luca.operatore": ("luca.demo", "luca-contabili"), "valeria.validatore": ("valeria.demo", "valeria-validatori")}[actor]
        self.token, _ = AUTH.login(user, "demo")
        AUTH.switch(self.token, membership)

    def request(self, path, method="GET", body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = Request(self.url + path, data=data, method=method, headers={"Content-Type": "application/json", "Cookie": f"WMSSESSION={self.token}"})
        with urlopen(request) as response:
            return response.status, response.read(), response.headers.get_content_type()

    def error(self, path, method="GET", body=None):
        with self.assertRaises(HTTPError) as context:
            self.request(path, method, body)
        code = context.exception.code
        context.exception.close()
        return code

    def complete(self, code, actor):
        self.login(actor)
        return self.request(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/{code}/complete", "POST", {"actor": actor})

    def test_serves_manager_queue_task_and_validation_views(self):
        for path, marker in [
            ("/", b"Pratiche in esecuzione"),
            (f"/practice.html?practice={DEMO_PRACTICE_ID}", b"Scheda Pratica Manager"),
            ("/queue.html", b"I miei compiti"),
            ("/task.html", b"Attivit\xc3\xa0 Operatore"),
            ("/validation.html", b"Validazione Pratica"),
        ]:
            status, page, content_type = self.request(path)
            self.assertEqual((status, content_type), (200, "text/html"))
            self.assertIn(marker, page)

    def test_manager_practice_list_is_scoped_and_summarized(self):
        _, body, _ = self.request("/api/manager/practices?actor=marta.manager")
        rows = json.loads(body)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], DEMO_PRACTICE_ID)
        self.assertIn("urgency", rows[0])
        self.assertIn("situation", rows[0])
        self.login("anna.operatore")
        self.assertEqual(self.error("/api/manager/practices?actor=marta.manager"), 403)

    def test_manager_assignment_catalog_and_invalid_group(self):
        _, body, _ = self.request("/api/manager/assignment-groups")
        groups = json.loads(body)
        self.assertIn({"id": "contabili", "name": "Contabili"}, groups)
        self.assertNotIn("manager", [g["id"] for g in groups])
        before = WMSRequestHandler.service.get_for(DEMO_PRACTICE_ID, AUTH.principal(self.token))
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/assign", "POST", {"group_id": "missing"}), 409)
        after = WMSRequestHandler.service.get_for(DEMO_PRACTICE_ID, AUTH.principal(self.token))
        self.assertEqual(before, after)
        self.login("anna.operatore")
        self.assertEqual(self.error("/api/manager/assignment-groups"), 403)

    def test_nonconformity_payload_tracks_corrective_cycle(self):
        for i in range(1, 8):
            self.complete(f"LIPE-{i:02}", "anna.operatore")
        self.login("valeria.validatore")
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}/validate", "POST", {"outcome": "NON_VALIDATA", "note": "Correggere importi"})
        nc = json.loads(body)["nonconformities"][0]
        self.assertEqual(nc["status"], "APERTA")
        self.assertEqual(nc["reason"], "Correggere importi")
        self.login("marta.manager")
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}/corrective-action", "POST", {"task_codes": ["LIPE-01"], "instruction": "Controllare importi"})
        nc = json.loads(body)["nonconformities"][0]
        self.assertEqual(nc["status"], "IN_SANATORIA")
        self.assertEqual(nc["corrective_actions"][0]["task_codes"], ["LIPE-01"])
        self.complete("LIPE-01", "anna.operatore")
        self.login("valeria.validatore")
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}/validate", "POST", {"outcome": "VALIDATA"})
        nc = json.loads(body)["nonconformities"][0]
        self.assertEqual(nc["status"], "CHIUSA")
        self.assertTrue(nc["closed_at"])

    def test_operator_context_includes_own_result_history(self):
        self.complete("LIPE-01", "anna.operatore")
        _, body, _ = self.request(f"/api/tasks/{DEMO_PRACTICE_ID}/LIPE-01?context=1")
        data = json.loads(body)
        self.assertEqual(len(data["task_results"]), 1)
        self.assertEqual(data["task_results"][0]["id"], data["task"]["result_id"])
        self.assertNotIn("LIPE-01", [r["related_task_code"] for r in data["previous_results"]])

    def test_service_without_demo_seed_starts_empty(self):
        service = PracticeService(seed_demo=False)
        self.assertEqual(service._practices, {})

    def test_rich_demo_has_25_practices_and_multiple_workflow_states(self):
        service = PracticeService(rich_demo=True)
        rows = service.manager_practices("marta.manager")
        self.assertEqual(len(rows), 25)
        self.assertEqual(len({row["client_id"] for row in rows}), 5)
        self.assertEqual(len({row["practice_type_code"] for row in rows}), 5)
        states = {row["status"] for row in rows}
        self.assertTrue({"DA_FARE", "IN_LAVORAZIONE", "DA_VALIDARE", "NON_VALIDATA", "VALIDATA"}.issubset(states))
        self.assertGreater(len(service.validation_queue("valeria.validatore")), 0)

    def test_demo_tasks_are_assigned_to_the_accounting_group(self):
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}")
        practice = json.loads(body)
        self.assertEqual({task["assigned_group"] for task in practice["tasks"]}, {"contabili"})
        self.assertTrue(all("completed_by" in task and "depends_on" in task for task in practice["tasks"]))
        self.assertEqual(sum(event["event_type"] == "TASK_ASSIGNED" for event in practice["audit"]), 7)

    def test_manager_can_reassign_task_and_assignment_is_audited(self):
        _, body, _ = self.request(
            f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/assign",
            "POST",
            {"actor": "marta.manager", "group_id": "segreteria"},
        )
        practice = json.loads(body)
        self.assertEqual(practice["tasks"][0]["assigned_group"], "segreteria")
        self.assertEqual(practice["audit"][0]["event_type"], "TASK_GROUP_ASSIGNED")
        self.login("anna.operatore")
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/assign", "POST", {"actor": "anna.operatore", "group_id": "segreteria"}), 403)

    def test_operator_queue_and_minimal_task_detail_are_scoped(self):
        self.login("anna.operatore")
        _, body, _ = self.request("/api/work-queue?operator=anna.operatore")
        queue = json.loads(body)
        self.assertEqual([item["code"] for item in queue], [f"LIPE-{i:02}" for i in range(1,8)])
        _, body, _ = self.request(f"/api/tasks/{DEMO_PRACTICE_ID}/LIPE-01?operator=anna.operatore")
        detail = json.loads(body)
        self.assertEqual(set(detail), {"practice", "task", "task_progress_evidence", "task_journal"})
        self.assertEqual(detail["task_progress_evidence"], [])
        self.assertEqual(detail["task_journal"], [])
        self.request(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/progress", "POST", {})
        self.login("luca.operatore")
        self.assertEqual(self.error(f"/api/tasks/{DEMO_PRACTICE_ID}/LIPE-01?operator=anna.operatore"), 403)

    def test_tasks_complete_out_of_definition_order(self):
        plan = [("LIPE-07", "anna.operatore"), ("LIPE-02", "luca.operatore"), ("LIPE-05", "anna.operatore"), ("LIPE-04", "luca.operatore"), ("LIPE-01", "anna.operatore"), ("LIPE-06", "luca.operatore"), ("LIPE-03", "anna.operatore")]
        for code, actor in plan:
            _, body, _ = self.complete(code, actor)
        practice = json.loads(body)
        self.assertEqual(practice["status"], "DA_VALIDARE")
        self.assertEqual(practice["tasks"][6]["completed_by"], "mario.demo")

    def test_wrong_operator_and_wrong_roles_are_rejected(self):
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/complete", "POST", {"actor": "anna.operatore"}), 403)
        self.login("anna.operatore")
        self.request(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/progress", "POST", {})
        self.login("luca.operatore")
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/complete", "POST", {"actor": "mario.demo"}), 403)
        self.login("valeria.validatore")
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {"actor": "marta.manager"}), 403)

    def test_executor_cannot_self_validate_and_manager_closes(self):
        for index in range(1,8):
            self.complete(f"LIPE-{index:02}", "anna.operatore")
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/validate", "POST", {"actor": "valeria.validatore"}), 403)
        self.login("valeria.validatore")
        self.request(f"/api/practices/{DEMO_PRACTICE_ID}/validate", "POST", {})
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {}), 403)
        self.login("marta.manager")
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {})
        self.assertEqual(json.loads(body)["status"], "CHIUSA")

    def test_early_close_returns_409(self):
        self.assertEqual(self.error(f"/api/practices/{DEMO_PRACTICE_ID}/close", "POST", {"actor": "marta.manager"}), 409)

    def test_task_result_and_evidence_are_exposed_to_manager_and_context(self):
        self.login("anna.operatore")
        _, body, _ = self.request(
            f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/complete", "POST",
            {"actor": "anna.operatore", "outcome": "POSITIVO", "note": "Dati completi",
             "attachments": [{"filename": "verifica.pdf", "content_type": "application/pdf"}]},
        )
        practice = json.loads(body)
        task = next(item for item in practice["tasks"] if item["code"] == "LIPE-01")
        result = next(item for item in practice["results"] if item["id"] == task["result_id"])
        evidence = next(item for item in practice["evidence"] if item["filename"] == "verifica.pdf")
        self.assertEqual(result["related_task_code"], "LIPE-01")
        self.assertEqual(evidence["related_task_code"], "LIPE-01")
        self.assertIn(evidence["id"], result["evidence_ids"])
        _, body, _ = self.request(f"/api/tasks/{DEMO_PRACTICE_ID}/LIPE-03?operator=anna.operatore&context=1")
        context = json.loads(body)
        self.assertEqual(context["previous_results"][0]["related_task_code"], "LIPE-01")
        self.assertEqual(context["evidence"][0]["source"], "TASK")

    def test_evidence_urls_select_the_owning_practice(self):
        from backend.wms_web.service import _evidence
        WMSRequestHandler.service = OrganizationalPracticeService(rich_demo=True)
        practices = list(WMSRequestHandler.service._practices.values())
        first = next(p for p in practices if p.evidence)
        second = next(p for p in practices if p.id != first.id and p.evidence and p.evidence[0].id == first.evidence[0].id)
        import base64
        for practice in (first, second):
            item = practice.evidence[0]
            payload = _evidence(item)
            for key, disposition in (("preview_url", "inline"), ("download_url", "attachment")):
                with urlopen(Request(self.url + payload[key], headers={"Cookie": f"WMSSESSION={self.token}"})) as response:
                    self.assertEqual(response.read(), base64.b64decode(item.content_base64))
                    self.assertEqual(response.headers.get_content_type(), item.content_type)
                    self.assertEqual(response.headers["Content-Disposition"], f'{disposition}; filename="{item.filename}"')
        self.assertEqual(self.error(f"/api/evidence/{first.evidence[0].id}"), 404)
        self.assertEqual(self.error(f"/api/evidence/{first.evidence[0].id}?practice=missing"), 404)

    def test_legacy_unique_evidence_link_still_works(self):
        self.complete("LIPE-01", "anna.operatore")
        WMSRequestHandler.service.save_task_progress_for(DEMO_PRACTICE_ID, "LIPE-03", AUTH.principal(self.token), attachments=[{"filename":"legacy.txt", "content_type":"text/plain", "content_base64":"b2s="}])
        self.assertEqual(self.request("/api/evidence/E-0001")[1], b"ok")

    def test_recompleted_task_points_to_latest_result(self):
        self.login("anna.operatore")
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/complete", "POST", {"actor":"anna.operatore","outcome":"CON_RILIEVI"})
        first = json.loads(body)
        first_result_id = next(t for t in first["tasks"] if t["code"]=="LIPE-01")["result_id"]
        self.login("marta.manager")
        self.request(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/reopen", "POST", {"actor":"marta.manager","reason":"Correggere"})
        self.login("anna.operatore")
        _, body, _ = self.request(f"/api/practices/{DEMO_PRACTICE_ID}/tasks/LIPE-01/complete", "POST", {"actor":"anna.operatore","outcome":"POSITIVO"})
        current = json.loads(body)
        task = next(t for t in current["tasks"] if t["code"]=="LIPE-01")
        self.assertNotEqual(task["result_id"], first_result_id)
        latest = next(r for r in current["results"] if r["id"]==task["result_id"])
        self.assertEqual(latest["outcome"], "POSITIVO")


if __name__ == "__main__":
    unittest.main()
