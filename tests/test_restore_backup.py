import os
import tempfile
import unittest

from scripts.restore_backup import find_latest_backup, restore_backup


class TestRestoreBackup(unittest.TestCase):
    def test_find_latest_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup_dir = os.path.join(tmp, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            db_path = os.path.join(tmp, "kwik_khata_db.xlsx")

            b1 = os.path.join(backup_dir, "kwik_khata_db_20260101_100000.xlsx")
            b2 = os.path.join(backup_dir, "kwik_khata_db_20260101_110000.xlsx")
            with open(b1, "w", encoding="utf-8") as f:
                f.write("old")
            with open(b2, "w", encoding="utf-8") as f:
                f.write("new")

            latest = find_latest_backup(backup_dir, db_path)
            self.assertIsNotNone(latest)

            restored = restore_backup(str(latest), db_path, create_pre_restore_backup=False)
            self.assertTrue(os.path.exists(restored))
            with open(db_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "new")


if __name__ == "__main__":
    unittest.main()
