import unittest
from unittest.mock import patch

from src import history


class HistoryTests(unittest.TestCase):
    def test_sample_timestamp_rounds_down_to_sample_interval(self):
        self.assertEqual(history.sample_timestamp(123), 120)
        self.assertEqual(history.sample_timestamp(129.9), 120)
        self.assertEqual(history.sample_timestamp(130), 130)

    def test_fill_short_gaps_only_fills_bounded_internal_gaps(self):
        values = [
            (1, True),
            (0, False),
            (0, False),
            (4, True),
            (0, False),
            (0, False),
            (0, False),
            (8, True),
            (0, False),
        ]

        self.assertEqual(
            history.fill_short_gaps(values, max_gap=2),
            [
                (1, True),
                (1, True),
                (1, True),
                (4, True),
                (0, False),
                (0, False),
                (0, False),
                (8, True),
                (0, False),
            ],
        )

    def test_graph_points_scale_values_and_mark_missing_data(self):
        points = history.graph_points(
            [(0, False), (5, True), (10, True)],
            max_value=10,
            label_formatter=lambda value: f"{value}%",
        )

        self.assertEqual(points[0], {"value": 0, "height": 0, "has_data": False, "label": "No data"})
        self.assertEqual(points[1], {"value": 5, "height": 50, "has_data": True, "label": "5%"})
        self.assertEqual(points[2], {"value": 10, "height": 100, "has_data": True, "label": "10%"})

    def test_metric_history_maps_rows_to_expected_samples(self):
        rows = [
            (100, 25.0),
            (110, 50.0),
        ]

        with patch("src.history.history_sample_timestamps", return_value=[90, 100, 110]):
            points = history.get_metric_history_from_rows(
                rows,
                1,
                max_value=100,
                label_formatter=history.format_percent,
            )

        self.assertEqual([point["has_data"] for point in points], [False, True, True])
        self.assertEqual([point["height"] for point in points], [0, 25, 50])
        self.assertEqual([point["label"] for point in points], ["No data", "25.0%", "50.0%"])

    def test_network_history_scales_rx_and_tx_together(self):
        rows = [
            (100, 0, 0, 1024, 2048),
            (110, 0, 0, 4096, 1024),
        ]

        with patch("src.history.history_sample_timestamps", return_value=[100, 110]):
            points = history.get_network_history_from_rows(rows)

        self.assertEqual(points[0]["rx_height"], 25)
        self.assertEqual(points[0]["tx_height"], 50)
        self.assertEqual(points[1]["rx_height"], 100)
        self.assertEqual(points[1]["tx_height"], 25)
        self.assertEqual(points[0]["rx_label"], "1.0 KB/s")
        self.assertEqual(points[1]["tx_label"], "1.0 KB/s")


if __name__ == "__main__":
    unittest.main()
