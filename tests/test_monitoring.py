import unittest

from services.monitoring import InMemoryMetrics


class TestMonitoring(unittest.TestCase):
    def test_snapshot_and_slo(self):
        m = InMemoryMetrics(window_size=100)
        m.record("/health", "GET", 200, 50)
        m.record("/api/v1/ledgers", "GET", 500, 1200)
        snap = m.snapshot()
        self.assertEqual(snap["total_requests"], 2)
        self.assertEqual(snap["total_errors"], 1)
        slo = m.slo(max_error_rate=0.6, max_p95_ms=1500)
        self.assertTrue(slo["ok"])


if __name__ == "__main__":
    unittest.main()
