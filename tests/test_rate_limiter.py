import unittest

from services.rate_limiter import InMemorySlidingWindowRateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_blocks_after_limit(self):
        limiter = InMemorySlidingWindowRateLimiter(limit=2, window_seconds=60)
        first = limiter.check("ip-1")
        second = limiter.check("ip-1")
        third = limiter.check("ip-1")
        self.assertTrue(first.allowed)
        self.assertTrue(second.allowed)
        self.assertFalse(third.allowed)
        self.assertGreaterEqual(third.retry_after_seconds, 1)

    def test_separate_keys_have_separate_buckets(self):
        limiter = InMemorySlidingWindowRateLimiter(limit=1, window_seconds=60)
        self.assertTrue(limiter.check("ip-a").allowed)
        self.assertTrue(limiter.check("ip-b").allowed)
        self.assertFalse(limiter.check("ip-a").allowed)


if __name__ == "__main__":
    unittest.main()
