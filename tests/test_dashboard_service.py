import os
import tempfile
import unittest

from database import KhataDB
from services.dashboard_service import build_dashboard_summary


class TestDashboardService(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        os.remove(self.path)
        self.db = KhataDB(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_summary_contains_overview_and_risk(self):
        self.db.add_transaction("Raju", 900)
        self.db.add_transaction("Mohan", 400)
        self.db.add_transaction("Raju", -100)
        summary = build_dashboard_summary(self.db, trend_days=30)
        self.assertIn("overview", summary)
        self.assertGreaterEqual(summary["overview"]["pending_total"], 1200)
        self.assertIn("top_risk_customers", summary)
        self.assertGreaterEqual(len(summary["top_risk_customers"]), 1)


if __name__ == "__main__":
    unittest.main()
