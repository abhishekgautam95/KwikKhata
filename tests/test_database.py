import os
import tempfile
import unittest

from database import KhataDB


class TestKhataDB(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        os.remove(self.path)
        self.db = KhataDB(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_add_and_get_balance(self):
        self.assertEqual(self.db.add_transaction("Raju", 500), 500)
        self.assertEqual(self.db.add_transaction("raju", -200), 300)
        self.assertEqual(self.db.get_balance("RAJU"), 300)

    def test_get_all_ledgers_only_positive(self):
        self.db.add_transaction("A", 100)
        self.db.add_transaction("B", -10)
        names = {row["name"] for row in self.db.get_all_ledgers()}
        self.assertIn("A", names)
        self.assertNotIn("B", names)

    def test_recent_transactions(self):
        self.db.add_transaction("Raju", 100)
        self.db.add_transaction("Raju", -10)
        tx = self.db.get_recent_transactions(limit=2)
        self.assertEqual(len(tx), 2)
        self.assertEqual(tx[0]["name"], "Raju")

    def test_undo_last_transaction(self):
        self.db.add_transaction("Raju", 100)
        self.db.add_transaction("Raju", -40)

        undone = self.db.undo_last_transaction()
        self.assertIsNotNone(undone)
        self.assertEqual(undone["customer_name"], "Raju")
        self.assertEqual(undone["amount"], -40.0)
        self.assertEqual(self.db.get_balance("Raju"), 100)

    def test_undo_when_empty(self):
        self.assertIsNone(self.db.undo_last_transaction())

    def test_customer_transactions(self):
        self.db.add_transaction("Raju", 100)
        self.db.add_transaction("Mohan", 70)
        self.db.add_transaction("Raju", -20)

        tx = self.db.get_customer_transactions("raju", limit=5)
        self.assertEqual(len(tx), 2)
        self.assertEqual(tx[0]["name"], "Raju")
        self.assertEqual(tx[0]["amount"], -20)


if __name__ == "__main__":
    unittest.main()
