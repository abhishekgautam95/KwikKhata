import os
import tempfile
import unittest

from database import KhataDB, create_db


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

    def test_pending_ledgers_with_age(self):
        self.db.add_transaction("Raju", 100)
        self.db.add_transaction("Mohan", -20)
        rows = self.db.get_pending_ledgers_with_age()
        names = {row["name"] for row in rows}
        self.assertIn("Raju", names)
        for row in rows:
            self.assertGreaterEqual(row["pending_days"], 0)

    def test_merge_customers(self):
        self.db.add_transaction("Additya", 40)
        self.db.add_transaction("Aditya", 60)

        result = self.db.merge_customers("Additya", "Aditya")
        self.assertTrue(result["ok"])
        self.assertEqual(self.db.get_balance("Additya"), None)
        self.assertEqual(self.db.get_balance("Aditya"), 100)

    def test_cleanup_noisy_customer_names(self):
        self.db.add_transaction("Rupees Chini Additya", 10)
        self.db.add_transaction("Aditya Rupees Namkeen", 60)

        result = self.db.cleanup_noisy_customer_names()
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["updated"], 1)
        self.assertEqual(self.db.get_balance("Aditya"), 60)
        self.assertEqual(self.db.get_balance("Additya"), 10)

    def test_create_db_defaults_to_excel_backend(self):
        prev_backend = os.environ.get("DATA_BACKEND")
        try:
            os.environ.pop("DATA_BACKEND", None)
            db = create_db(self.path)
            self.assertIsInstance(db, KhataDB)
        finally:
            if prev_backend is None:
                os.environ.pop("DATA_BACKEND", None)
            else:
                os.environ["DATA_BACKEND"] = prev_backend

    def test_create_db_postgres_without_config_fails_fast(self):
        prev_backend = os.environ.get("DATA_BACKEND")
        prev_url = os.environ.get("KWIKKHATA_DATABASE_URL")
        prev_url2 = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATA_BACKEND"] = "postgres"
            os.environ.pop("KWIKKHATA_DATABASE_URL", None)
            os.environ.pop("DATABASE_URL", None)
            with self.assertRaises(RuntimeError):
                create_db()
        finally:
            if prev_backend is None:
                os.environ.pop("DATA_BACKEND", None)
            else:
                os.environ["DATA_BACKEND"] = prev_backend
            if prev_url is None:
                os.environ.pop("KWIKKHATA_DATABASE_URL", None)
            else:
                os.environ["KWIKKHATA_DATABASE_URL"] = prev_url
            if prev_url2 is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = prev_url2


if __name__ == "__main__":
    unittest.main()
