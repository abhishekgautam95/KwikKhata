from datetime import datetime
import unittest

from services.localization import format_currency, format_datetime, localize_ack


class TestLocalization(unittest.TestCase):
    def test_format_currency_inr(self):
        self.assertEqual(format_currency(1200, locale="en-IN", currency="INR"), "₹1200")

    def test_format_currency_usd(self):
        self.assertEqual(format_currency(1200.5, locale="en-US", currency="USD"), "$1,200.50")

    def test_format_datetime_locales(self):
        dt = datetime(2026, 3, 2, 15, 30)
        self.assertIn("03/02/2026", format_datetime(dt, locale="en-US"))
        self.assertIn("02/03/2026", format_datetime(dt, locale="en-IN"))

    def test_localize_ack(self):
        self.assertEqual(localize_ack("hi-IN"), "Thik hai, update ho gaya.")


if __name__ == "__main__":
    unittest.main()
