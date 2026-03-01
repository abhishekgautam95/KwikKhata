import os
import unittest

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


if __name__ == "__main__":
    unittest.main()
