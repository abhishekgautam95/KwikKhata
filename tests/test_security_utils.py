import unittest

from services.security_utils import hash_identifier, mask_phone, redact_sensitive


class TestSecurityUtils(unittest.TestCase):
    def test_mask_phone(self):
        self.assertEqual(mask_phone("+919999111222"), "********1222")

    def test_hash_identifier_stable(self):
        a = hash_identifier("919999111222")
        b = hash_identifier("919999111222")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_redact_sensitive(self):
        payload = {
            "token": "abc",
            "nested": {"Authorization": "Bearer very-secret"},
            "safe": "ok",
        }
        redacted = redact_sensitive(payload)
        self.assertEqual(redacted["token"], "***redacted***")
        self.assertEqual(redacted["nested"]["Authorization"], "***redacted***")
        self.assertEqual(redacted["safe"], "ok")


if __name__ == "__main__":
    unittest.main()
