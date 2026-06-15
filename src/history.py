import sqlite3
import time

from src.config import (
    DATA_DIR,
    DB_PATH,
    HISTORY_LIMIT,
    HISTORY_SAMPLE_INTERVAL,
    RETENTION_SECONDS,
)
from src.formatting import bytes_per_second, format_percent

LAST_HISTORY_BUCKET = None


def init_db():
    DATA_DIR.mkdir(exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
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
    cutoff = int(time.time()) - RETENTION_SECONDS

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM metric_samples WHERE sampled_at < ?", (cutoff,))


def sample_bucket(timestamp=None):
    timestamp = time.time() if timestamp is None else timestamp
    return int(timestamp // HISTORY_SAMPLE_INTERVAL) * HISTORY_SAMPLE_INTERVAL


def save_metric_sample(
    cpu_usage,
    memory_usage,
    network_bps,
    network_rx_bps,
    network_tx_bps,
    disk_read_bps,
    disk_write_bps,
):
    global LAST_HISTORY_BUCKET

    bucket = sample_bucket()
    if LAST_HISTORY_BUCKET == bucket:
        return

    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO metric_samples (
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
            """,
            (
                bucket,
                cpu_usage,
                memory_usage,
                network_bps,
                network_rx_bps,
                network_tx_bps,
                disk_read_bps,
                disk_write_bps,
            ),
        )

    LAST_HISTORY_BUCKET = bucket
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


def history_buckets():
    current_bucket = sample_bucket()
    return [
        current_bucket - ((HISTORY_LIMIT - 1 - index) * HISTORY_SAMPLE_INTERVAL)
        for index in range(HISTORY_LIMIT)
    ]


def get_metric_history(column, max_value=None, label_formatter=None):
    init_db()
    buckets = history_buckets()

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            f"""
            SELECT sampled_at, {column}
            FROM metric_samples
            WHERE sampled_at >= ?
            ORDER BY sampled_at
            """,
            (buckets[0],),
        ).fetchall()

    values_by_bucket = {sampled_at: value for sampled_at, value in rows}
    values = [
        (values_by_bucket.get(bucket, 0), bucket in values_by_bucket)
        for bucket in buckets
    ]

    return graph_points(
        values,
        max_value=max_value,
        label_formatter=label_formatter,
    )


def get_network_history():
    init_db()
    buckets = history_buckets()

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT sampled_at, network_rx_bps, network_tx_bps
            FROM metric_samples
            WHERE sampled_at >= ?
            ORDER BY sampled_at
            """,
            (buckets[0],),
        ).fetchall()

    values_by_bucket = {
        sampled_at: (rx_bps, tx_bps)
        for sampled_at, rx_bps, tx_bps in rows
    }
    populated_values = [
        value
        for bucket in buckets
        if bucket in values_by_bucket
        for value in values_by_bucket[bucket]
    ]
    scale = max(populated_values, default=0) or 1

    points = []
    for bucket in buckets:
        rx_bps, tx_bps = values_by_bucket.get(bucket, (0, 0))
        has_data = bucket in values_by_bucket
        points.append(
            {
                "rx_height": max(4, round((rx_bps / scale) * 100)) if has_data else 0,
                "tx_height": max(4, round((tx_bps / scale) * 100)) if has_data else 0,
                "has_data": has_data,
                "rx_label": bytes_per_second(rx_bps) if has_data else "No data",
                "tx_label": bytes_per_second(tx_bps) if has_data else "No data",
            }
        )

    return points


def get_history():
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
