import unittest

from src.services import parse_systemd_show, parse_systemd_value


class ServiceParsingTests(unittest.TestCase):
    def test_parse_systemd_value_handles_empty_unset_infinity_and_numbers(self):
        self.assertIsNone(parse_systemd_value(""))
        self.assertIsNone(parse_systemd_value("[not set]"))
        self.assertIsNone(parse_systemd_value("infinity"))
        self.assertIsNone(parse_systemd_value("not-a-number"))
        self.assertEqual(parse_systemd_value("4096"), 4096)

    def test_parse_systemd_show_ignores_lines_without_properties(self):
        self.assertEqual(
            parse_systemd_show("UnitFileState=enabled\nignored\nMemoryCurrent=2048\n"),
            {
                "UnitFileState": "enabled",
                "MemoryCurrent": "2048",
            },
        )


if __name__ == "__main__":
    unittest.main()
