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


if __name__ == '__main__':
    unittest.main()
