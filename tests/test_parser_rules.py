import os
import unittest
from unittest.mock import patch

from ai_parser import parse_shopkeeper_intent


class TestRuleParser(unittest.TestCase):
    def setUp(self):
        os.environ["PARSER_MODE"] = "hybrid"
        os.environ["AI_PROVIDER"] = "ollama"
        os.environ["ENABLE_FALLBACK"] = "false"
        os.environ["OLLAMA_URL"] = "http://127.0.0.1:65535/api/generate"

    def test_credit_parse(self):
        got = parse_shopkeeper_intent("Raju ka 500 udhaar likho")
        self.assertEqual(got["action"], "add_transaction")
        self.assertEqual(got["customer_name"], "Raju")
        self.assertEqual(got["amount"], 500)

    def test_payment_parse(self):
        got = parse_shopkeeper_intent("Raju ka 200 jama kar lo")
        self.assertEqual(got["action"], "add_transaction")
        self.assertEqual(got["amount"], -200)

    def test_balance_parse(self):
        got = parse_shopkeeper_intent("Raju ka balance batao")
        self.assertEqual(got, {"customer_name": "Raju", "action": "get_balance", "amount": 0})

    def test_get_all_parse(self):
        got = parse_shopkeeper_intent("Sabka hisaab dikhao")
        self.assertEqual(got, {"customer_name": "", "action": "get_all", "amount": 0})

    def test_get_all_parse_kis_kis_phrase(self):
        got = parse_shopkeeper_intent("ok abb mughe check krna h ki mere kis kis pr kitne rupees h to show me")
        self.assertEqual(got, {"customer_name": "", "action": "get_all", "amount": 0})

    def test_balance_short_followup(self):
        got = parse_shopkeeper_intent("sbi ka")
        self.assertEqual(got, {"customer_name": "Sbi", "action": "get_balance", "amount": 0})

    def test_get_all_parse_all_data_phrase(self):
        got = parse_shopkeeper_intent("ok mughe all data dikhao")
        self.assertEqual(got, {"customer_name": "", "action": "get_all", "amount": 0})

    def test_name_cleanup_with_amount_phrase(self):
        got = parse_shopkeeper_intent("aditya 30 rupees namkeen")
        self.assertEqual(got, {"customer_name": "Aditya", "action": "add_transaction", "amount": 30})

    def test_name_cleanup_amount_first_phrase(self):
        got = parse_shopkeeper_intent("30 rupees chini aditya")
        self.assertEqual(got, {"customer_name": "Aditya", "action": "add_transaction", "amount": 30})

    @patch("ai_parser._parse_with_provider")
    @patch("ai_parser.PARSER_MODE", "llm")
    def test_llm_result_repaired_to_get_all(self, mock_provider):
        mock_provider.return_value = {"customer_name": "", "action": "get_balance", "amount": 0}
        got = parse_shopkeeper_intent("mere kis kis pe kitna baki hai show me")
        self.assertEqual(got, {"customer_name": "", "action": "get_all", "amount": 0})


if __name__ == "__main__":
    unittest.main()
