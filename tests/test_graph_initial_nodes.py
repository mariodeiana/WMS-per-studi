import unittest
from backend.wms_web.config_models import model_graph_issues

class InitialNodesTest(unittest.TestCase):
    def test_legacy_roots_are_migrated_once(self):
        tasks=[{"code":"A","transitions":{"*": ["B"]}},{"code":"B","transitions":{}}]
        self.assertEqual(model_graph_issues(tasks), [])
        self.assertEqual([t["is_initial"] for t in tasks], [True,False])
        tasks[0]["transitions"]={}
        self.assertIn("B: senza ingressi e non iniziale",model_graph_issues(tasks))

    def test_disconnected_branch_and_multiple_starts(self):
        tasks=[{"code":"A","is_initial":True,"transitions":{}},{"code":"B","is_initial":False,"transitions":{"OK":["C"]}},{"code":"C","is_initial":False,"transitions":{}}]
        self.assertEqual(len(model_graph_issues(tasks)),2)
        self.assertIn("non raggiungibile", model_graph_issues(tasks)[1])
        tasks[1]["is_initial"]=True
        self.assertEqual(model_graph_issues(tasks),[])

    def test_no_start_and_invalid_flag(self):
        tasks=[{"code":"A","is_initial":False,"transitions":{}}]
        self.assertIn("Nessun nodo iniziale", model_graph_issues(tasks))
        tasks[0]["is_initial"]="false"
        with self.assertRaises(ValueError): model_graph_issues(tasks)
