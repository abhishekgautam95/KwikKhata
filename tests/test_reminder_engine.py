import tempfile
import unittest

from database import KhataDB
from services.reminder_engine import build_candidates


class TestReminderEngine(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".xlsx")
        import os

        os.close(fd)
        os.remove(self.path)
        self.db = KhataDB(self.path)

    def tearDown(self):
        import os

        if os.path.exists(self.path):
            os.remove(self.path)

    def test_build_candidates(self):
        self.db.add_transaction("Raju", 500)
        candidates = build_candidates(self.db, min_days=0, min_amount=1)
        self.assertTrue(any(c.name == "Raju" for c in candidates))


if __name__ == "__main__":
    unittest.main()
