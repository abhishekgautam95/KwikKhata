import os
import tempfile
import unittest

from services.compliance_service import ComplianceStore


class TestComplianceService(unittest.TestCase):
    def test_append_export_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "compliance.jsonl")
            store = ComplianceStore(filepath=path)
            store.append_event("consent", "user-1", {"consent": "granted"})
            store.append_event("consent", "user-2", {"consent": "granted"})
            exported = store.export_subject_events("user-1")
            self.assertEqual(len(exported), 1)
            removed = store.delete_subject_events("user-1")
            self.assertEqual(removed, 1)
            self.assertEqual(len(store.export_subject_events("user-1")), 0)


if __name__ == "__main__":
    unittest.main()
