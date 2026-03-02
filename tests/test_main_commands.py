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

    def test_remind_all_command(self):
        self.assertEqual(
            parse_manual_command('/remind-all'),
            {"customer_name": "", "action": "send_reminders", "amount": 0},
        )

    def test_natural_language_bulk_reminder_intent(self):
        self.assertEqual(
            parse_manual_command('ok ab jis jis pr mere paise h unko message bhej do'),
            {"customer_name": "", "action": "send_reminders", "amount": 0},
        )

    def test_cleanup_names_command(self):
        self.assertEqual(
            parse_manual_command('/cleanup-names'),
            {"customer_name": "", "action": "cleanup_names", "amount": 0},
        )

    def test_merge_command(self):
        self.assertEqual(
            parse_manual_command('/merge additya -> aditya'),
            {
                "customer_name": "",
                "action": "merge_customer",
                "amount": 0,
                "source": "Additya",
                "target": "Aditya",
            },
        )

    def test_ack_text(self):
        self.assertEqual(
            parse_manual_command('ok good'),
            {"customer_name": "", "action": "ack", "amount": 0},
        )

    def test_smalltalk_how_are_you(self):
        self.assertEqual(
            parse_manual_command('aur kese ho aap'),
            {"customer_name": "", "action": "smalltalk_help", "amount": 0},
        )

    def test_smalltalk_capabilities(self):
        self.assertEqual(
            parse_manual_command('aap kya kya kr sakte ho'),
            {"customer_name": "", "action": "smalltalk_help", "amount": 0},
        )

    def test_smalltalk_capabilities_short_kr(self):
        self.assertEqual(
            parse_manual_command('hey aap mere liye kya kr sakte ho'),
            {"customer_name": "", "action": "smalltalk_help", "amount": 0},
        )


if __name__ == '__main__':
    unittest.main()
