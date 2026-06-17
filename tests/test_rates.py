import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src import rates


class RateTests(unittest.TestCase):
    def setUp(self):
        rates.LAST_NET_SAMPLE = None
        rates.LAST_DISK_SAMPLE = None

    def test_network_throughput_returns_zero_for_initial_sample(self):
        net_io = SimpleNamespace(bytes_recv=1000, bytes_sent=2000)

        with patch("src.rates.time.monotonic", return_value=10):
            result = rates.get_network_throughput(net_io)

        self.assertEqual(result["rx_rate"], 0)
        self.assertEqual(result["tx_rate"], 0)
        self.assertEqual(result["total_rate_label"], "0.0 B/s")

    def test_network_throughput_calculates_rate_from_previous_sample(self):
        first = SimpleNamespace(bytes_recv=1000, bytes_sent=2000)
        second = SimpleNamespace(bytes_recv=2024, bytes_sent=4048)

        with patch("src.rates.time.monotonic", side_effect=[10, 12]):
            rates.get_network_throughput(first)
            result = rates.get_network_throughput(second)

        self.assertEqual(result["rx_rate"], 512)
        self.assertEqual(result["tx_rate"], 1024)
        self.assertEqual(result["total_rate"], 1536)
        self.assertEqual(result["total_rate_label"], "1.5 KB/s")

    def test_disk_throughput_never_reports_negative_rates(self):
        first = SimpleNamespace(read_bytes=2000, write_bytes=3000)
        second = SimpleNamespace(read_bytes=1000, write_bytes=1000)

        with patch("src.rates.time.monotonic", side_effect=[10, 12]):
            rates.get_disk_throughput(first)
            result = rates.get_disk_throughput(second)

        self.assertEqual(result["read_rate"], 0)
        self.assertEqual(result["write_rate"], 0)
        self.assertEqual(result["total_rate"], 0)


if __name__ == "__main__":
    unittest.main()
