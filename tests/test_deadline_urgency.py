import unittest
from datetime import date, timedelta
from backend.wms_web.service import deadline_urgency

class DeadlineUrgencyTest(unittest.TestCase):
    def test_manager_priority_boundaries(self):
        for days, level in [(-1,'OVERDUE'),(0,'HIGH'),(7,'HIGH'),(8,'MEDIUM'),(30,'MEDIUM'),(31,'LOW')]:
            with self.subTest(days=days):
                urgency, order = deadline_urgency((date.today()+timedelta(days=days)).isoformat())
                self.assertEqual(urgency['level'],level)
                self.assertEqual(order,days)
