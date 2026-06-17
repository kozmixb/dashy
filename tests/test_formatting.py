import unittest

from src.formatting import (
    format_bytes,
    format_bytes_per_second,
    format_bytes_short,
    format_percent,
)


class FormattingTests(unittest.TestCase):
    def test_format_bytes_handles_none_and_scales_binary_units(self):
        self.assertEqual(format_bytes(None), "n/a")
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(1024), "1.00 KiB")
        self.assertEqual(format_bytes(1536), "1.50 KiB")
        self.assertEqual(format_bytes(10 * 1024), "10.0 KiB")
        self.assertEqual(format_bytes(100 * 1024), "100 KiB")

    def test_format_bytes_short_uses_short_unit_labels(self):
        self.assertEqual(format_bytes_short(None), "n/a")
        self.assertEqual(format_bytes_short(1024 * 1024), "1.00 MB")

    def test_rate_and_percent_formatting(self):
        self.assertEqual(format_bytes_per_second(0), "0.0 B/s")
        self.assertEqual(format_bytes_per_second(1536), "1.5 KB/s")
        self.assertEqual(format_percent(12.345), "12.3%")


if __name__ == "__main__":
    unittest.main()
