import sqlite3
import time

from src.config import (
    DATA_DIR,
    DB_PATH,
    HISTORY_POINT_COUNT,
    HISTORY_RETENTION_SECONDS,
    HISTORY_SAMPLE_INTERVAL_SECONDS,
)
from src.formatting import format_bytes_per_second, format_percent

LAST_SAVED_SAMPLE_TIMESTAMP = None


def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db():
    DATA_DIR.mkdir(exist_ok=True)

    with connect_db() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_samples (
                sampled_at INTEGER PRIMARY KEY,
                cpu_percent REAL NOT NULL,
                memory_percent REAL NOT NULL,
                network_bps REAL NOT NULL,
                network_rx_bps REAL NOT NULL DEFAULT 0,
                network_tx_bps REAL NOT NULL DEFAULT 0,
                disk_read_bps REAL NOT NULL,
                disk_write_bps REAL NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_metric_samples_sampled_at "
            "ON metric_samples (sampled_at)"
        )

        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(metric_samples)").fetchall()
        }
        if "network_rx_bps" not in columns:
            conn.execute(
                "ALTER TABLE metric_samples "
                "ADD COLUMN network_rx_bps REAL NOT NULL DEFAULT 0"
            )
        if "network_tx_bps" not in columns:
            conn.execute(
                "ALTER TABLE metric_samples "
                "ADD COLUMN network_tx_bps REAL NOT NULL DEFAULT 0"
            )


def prune_old_samples():
    cutoff = int(time.time()) - HISTORY_RETENTION_SECONDS

    with connect_db() as conn:
        conn.execute("DELETE FROM metric_samples WHERE sampled_at < ?", (cutoff,))


def sample_timestamp(timestamp=None):
    timestamp = time.time() if timestamp is None else timestamp
    return (
        int(timestamp // HISTORY_SAMPLE_INTERVAL_SECONDS)
        * HISTORY_SAMPLE_INTERVAL_SECONDS
    )


def save_history_sample(
    cpu_usage,
    memory_usage,
    network_bps,
    network_rx_bps,
    network_tx_bps,
    disk_read_bps,
    disk_write_bps,
):
    global LAST_SAVED_SAMPLE_TIMESTAMP

    sampled_at = sample_timestamp()
    if LAST_SAVED_SAMPLE_TIMESTAMP == sampled_at:
        return

    init_db()

    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO metric_samples (
                sampled_at,
                cpu_percent,
                memory_percent,
                network_bps,
                network_rx_bps,
                network_tx_bps,
                disk_read_bps,
                disk_write_bps
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sampled_at) DO UPDATE SET
                cpu_percent = excluded.cpu_percent,
                memory_percent = excluded.memory_percent,
                network_bps = excluded.network_bps,
                network_rx_bps = excluded.network_rx_bps,
                network_tx_bps = excluded.network_tx_bps,
                disk_read_bps = excluded.disk_read_bps,
                disk_write_bps = excluded.disk_write_bps
            """,
            (
                sampled_at,
                cpu_usage,
                memory_usage,
                network_bps,
                network_rx_bps,
                network_tx_bps,
                disk_read_bps,
                disk_write_bps,
            ),
        )

    LAST_SAVED_SAMPLE_TIMESTAMP = sampled_at
    prune_old_samples()


def graph_points(values, max_value=None, label_formatter=None):
    populated_values = [value for value, has_data in values if has_data]
    scale = max_value or max(populated_values, default=0) or 1
    label_formatter = label_formatter or (lambda value: str(value))

    return [
        {
            "value": value,
            "height": max(4, round((value / scale) * 100)) if has_data else 0,
            "has_data": has_data,
            "label": label_formatter(value) if has_data else "No data",
        }
        for value, has_data in values
    ]


def fill_short_gaps(values, max_gap=2):
    filled_values = list(values)
    index = 0

    while index < len(filled_values):
        value, has_data = filled_values[index]
        if has_data:
            index += 1
            continue

        gap_start = index
        while index < len(filled_values) and not filled_values[index][1]:
            index += 1

        gap_length = index - gap_start
        has_previous = gap_start > 0 and filled_values[gap_start - 1][1]
        has_next = index < len(filled_values) and filled_values[index][1]
        if not has_previous or not has_next or gap_length > max_gap:
            continue

        previous_value = filled_values[gap_start - 1][0]
        for gap_index in range(gap_start, index):
            filled_values[gap_index] = (previous_value, True)

    return filled_values


def history_sample_timestamps():
    current_sample = sample_timestamp(time.time() - HISTORY_SAMPLE_INTERVAL_SECONDS)
    return [
        current_sample
        - ((HISTORY_POINT_COUNT - 1 - index) * HISTORY_SAMPLE_INTERVAL_SECONDS)
        for index in range(HISTORY_POINT_COUNT)
    ]


def get_metric_history(column, max_value=None, label_formatter=None):
    init_db()
    sample_timestamps = history_sample_timestamps()

    with connect_db() as conn:
        rows = conn.execute(
            f"""
            SELECT sampled_at, {column}
            FROM metric_samples
            WHERE sampled_at >= ?
            ORDER BY sampled_at
            """,
            (sample_timestamps[0],),
        ).fetchall()

    values_by_sample = {sampled_at: value for sampled_at, value in rows}
    values = [
        (values_by_sample.get(sampled_at, 0), sampled_at in values_by_sample)
        for sampled_at in sample_timestamps
    ]
    values = fill_short_gaps(values)

    return graph_points(
        values,
        max_value=max_value,
        label_formatter=label_formatter,
    )


def get_network_history():
    init_db()
    sample_timestamps = history_sample_timestamps()

    with connect_db() as conn:
        rows = conn.execute(
            """
            SELECT sampled_at, network_rx_bps, network_tx_bps
            FROM metric_samples
            WHERE sampled_at >= ?
            ORDER BY sampled_at
            """,
            (sample_timestamps[0],),
        ).fetchall()

    values_by_sample = {
        sampled_at: (rx_bps, tx_bps)
        for sampled_at, rx_bps, tx_bps in rows
    }
    values = [
        (values_by_sample.get(sampled_at, (0, 0)), sampled_at in values_by_sample)
        for sampled_at in sample_timestamps
    ]
    values = fill_short_gaps(values)
    populated_values = [
        value
        for sample_values, has_data in values
        if has_data
        for value in sample_values
    ]
    scale = max(populated_values, default=0) or 1

    points = []
    for (rx_bps, tx_bps), has_data in values:
        points.append(
            {
                "rx_height": max(4, round((rx_bps / scale) * 100)) if has_data else 0,
                "tx_height": max(4, round((tx_bps / scale) * 100)) if has_data else 0,
                "has_data": has_data,
                "rx_label": (
                    format_bytes_per_second(rx_bps) if has_data else "No data"
                ),
                "tx_label": (
                    format_bytes_per_second(tx_bps) if has_data else "No data"
                ),
            }
        )

    return points


def get_chart_history():
    return {
        "cpu_history": get_metric_history(
            "cpu_percent",
            label_formatter=format_percent,
        ),
        "memory_history": get_metric_history(
            "memory_percent",
            label_formatter=format_percent,
        ),
        "network_history": get_network_history(),
    }
