import tempfile
import unittest
from unittest.mock import patch

from database import KhataDB
from services.reminder_engine import _build_personalized_reminder, _sanitize_phone_number, build_candidates, send_customer_reminder


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

    def test_sanitize_phone(self):
        self.assertEqual(_sanitize_phone_number("+91 99999-88888"), "+919999988888")
        self.assertEqual(_sanitize_phone_number("123"), "")

    def test_personalized_reminder_message(self):
        text = _build_personalized_reminder("Raju", balance=5200, pending_days=50)
        self.assertIn("Raju", text)
        self.assertIn("5200", text)

    @patch("services.reminder_engine.send_text_message")
    def test_send_customer_reminder_uses_profile(self, mock_send):
        mock_send.return_value = {"ok": True}
        import os

        os.environ["CUSTOMER_PHONEBOOK"] = '{"Raju":"+919999999999"}'
        self.db.add_transaction("Raju", 2000)
        ok = send_customer_reminder("Raju", db=self.db)
        self.assertTrue(ok)
        sent_body = mock_send.call_args[0][1]
        self.assertIn("Raju", sent_body)


if __name__ == "__main__":
    unittest.main()
