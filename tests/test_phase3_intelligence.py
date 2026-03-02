import os
import tempfile
import unittest

from ai_parser import parse_shopkeeper_intent
from database import KhataDB
from services.ledger_agent import PendingIntentStore, process_user_text


class TestPhase3Intelligence(unittest.TestCase):
    def setUp(self):
        os.environ["PARSER_MODE"] = "hybrid"
        fd, self.path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        os.remove(self.path)
        self.db = KhataDB(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_parser_returns_explain_meta(self):
        got = parse_shopkeeper_intent("Raju ka 500 udhaar likho", include_meta=True)
        self.assertIsNotNone(got)
        self.assertEqual(got["action"], "add_transaction")
        self.assertIn("_explain", got)
        self.assertEqual(got["_explain"]["confidence"], "high")

    def test_parser_marks_risky_when_words_weak(self):
        got = parse_shopkeeper_intent("Raju 500", include_meta=True)
        self.assertIsNotNone(got)
        self.assertEqual(got["action"], "add_transaction")
        self.assertEqual(got["_explain"]["risk"], "high")
        self.assertEqual(got["_explain"]["confidence"], "medium")

    def test_parser_corrects_payment_direction(self):
        got = parse_shopkeeper_intent("Raju ko 500 payment mila", include_meta=True)
        self.assertIsNotNone(got)
        self.assertEqual(got["amount"], -500)

    def test_sensitive_command_requires_confirmation(self):
        store = PendingIntentStore()
        response = process_user_text(self.db, store, "u1", "/remind-all")
        self.assertTrue(response.needs_confirmation)
        self.assertIn("confirm", response.text.lower())


if __name__ == "__main__":
    unittest.main()
