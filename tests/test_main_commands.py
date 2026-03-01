import unittest

from main import parse_manual_command


class TestMainCommands(unittest.TestCase):
    def test_bal_command(self):
        self.assertEqual(
            parse_manual_command('/bal raju'),
            {"customer_name": "Raju", "action": "get_balance", "amount": 0},
        )

    def test_add_command(self):
        self.assertEqual(
            parse_manual_command('/add raju 500'),
            {"customer_name": "Raju", "action": "add_transaction", "amount": 500},
        )

    def test_pay_command(self):
        self.assertEqual(
            parse_manual_command('/pay raju 300'),
            {"customer_name": "Raju", "action": "add_transaction", "amount": -300},
        )

    def test_undo_command(self):
        self.assertEqual(
            parse_manual_command('/undo'),
            {"customer_name": "", "action": "undo", "amount": 0},
        )

    def test_recent_command_default_limit(self):
        self.assertEqual(
            parse_manual_command('/recent'),
            {"customer_name": "", "action": "recent", "amount": 0, "limit": 10},
        )

    def test_recent_command_custom_limit(self):
        self.assertEqual(
            parse_manual_command('/recent 5'),
            {"customer_name": "", "action": "recent", "amount": 0, "limit": 5},
        )

    def test_history_command(self):
        self.assertEqual(
            parse_manual_command('/history raju 3'),
            {"customer_name": "Raju", "action": "history", "amount": 0, "limit": 3},
        )


if __name__ == '__main__':
    unittest.main()
