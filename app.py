from pathlib import Path
import socket
import sqlite3
import subprocess
import time
from datetime import timedelta

import psutil
from flask import Flask, render_template

app = Flask(__name__)

# --- CONFIGURATION ---
SERVICES_TO_TRACK = ["xmr"]
HISTORY_SAMPLE_INTERVAL = 10
HISTORY_LIMIT = 360
RETENTION_SECONDS = 24 * 60 * 60
DATA_DIR = Path(__file__).with_name("data")
DB_PATH = DATA_DIR / "stats.sqlite3"

LAST_NET_SAMPLE = None
LAST_DISK_SAMPLE = None
LAST_HISTORY_BUCKET = None


def gb(value):
    return round(value / (1024**3), 2)


def mb(value):
    return round(value / (1024**2), 1)


def bytes_per_second(value):
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    size = float(value)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024


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


def minute_bucket(timestamp=None):
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

    bucket = minute_bucket()
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


def graph_points(values, max_value=None):
    populated_values = [value for value, has_data in values if has_data]
    scale = max_value or max(populated_values, default=0) or 1

    return [
        {
            "value": value,
            "height": max(4, round((value / scale) * 100)) if has_data else 0,
            "has_data": has_data,
        }
        for value, has_data in values
    ]


def get_metric_history(column, max_value=None):
    init_db()

    current_bucket = minute_bucket()
    buckets = [
        current_bucket - ((HISTORY_LIMIT - 1 - index) * HISTORY_SAMPLE_INTERVAL)
        for index in range(HISTORY_LIMIT)
    ]

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

    return graph_points(values, max_value=max_value)


def get_network_history():
    init_db()

    current_bucket = minute_bucket()
    buckets = [
        current_bucket - ((HISTORY_LIMIT - 1 - index) * HISTORY_SAMPLE_INTERVAL)
        for index in range(HISTORY_LIMIT)
    ]

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
            }
        )

    return points


def get_history():
    return {
        "cpu_history": get_metric_history("cpu_percent", max_value=100),
        "memory_history": get_metric_history("memory_percent", max_value=100),
        "network_history": get_network_history(),
        "disk_read_history": get_metric_history("disk_read_bps"),
        "disk_write_history": get_metric_history("disk_write_bps"),
    }


def get_network_usage(net_io):
    global LAST_NET_SAMPLE

    now = time.monotonic()
    current_sample = (now, net_io.bytes_recv, net_io.bytes_sent)

    if LAST_NET_SAMPLE is None:
        LAST_NET_SAMPLE = current_sample
        return {
            "rx_rate": 0,
            "tx_rate": 0,
            "total_rate": 0,
            "rx_rate_label": bytes_per_second(0),
            "tx_rate_label": bytes_per_second(0),
            "total_rate_label": bytes_per_second(0),
        }

    last_time, last_recv, last_sent = LAST_NET_SAMPLE
    elapsed = max(now - last_time, 0.001)
    rx_rate = max((net_io.bytes_recv - last_recv) / elapsed, 0)
    tx_rate = max((net_io.bytes_sent - last_sent) / elapsed, 0)
    total_rate = rx_rate + tx_rate

    LAST_NET_SAMPLE = current_sample

    return {
        "rx_rate": rx_rate,
        "tx_rate": tx_rate,
        "total_rate": total_rate,
        "rx_rate_label": bytes_per_second(rx_rate),
        "tx_rate_label": bytes_per_second(tx_rate),
        "total_rate_label": bytes_per_second(total_rate),
    }


def get_disk_usage(disk_io):
    global LAST_DISK_SAMPLE

    now = time.monotonic()
    current_sample = (now, disk_io.read_bytes, disk_io.write_bytes)

    if LAST_DISK_SAMPLE is None:
        LAST_DISK_SAMPLE = current_sample
        return {
            "read_rate": 0,
            "write_rate": 0,
            "total_rate": 0,
            "read_rate_label": bytes_per_second(0),
            "write_rate_label": bytes_per_second(0),
            "total_rate_label": bytes_per_second(0),
        }

    last_time, last_read, last_write = LAST_DISK_SAMPLE
    elapsed = max(now - last_time, 0.001)
    read_rate = max((disk_io.read_bytes - last_read) / elapsed, 0)
    write_rate = max((disk_io.write_bytes - last_write) / elapsed, 0)
    total_rate = read_rate + write_rate

    LAST_DISK_SAMPLE = current_sample

    return {
        "read_rate": read_rate,
        "write_rate": write_rate,
        "total_rate": total_rate,
        "read_rate_label": bytes_per_second(read_rate),
        "write_rate_label": bytes_per_second(write_rate),
        "total_rate_label": bytes_per_second(total_rate),
    }


def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            return str(timedelta(seconds=int(uptime_seconds)))
    except Exception:
        uptime_seconds = time.time() - psutil.boot_time()
        return str(timedelta(seconds=int(uptime_seconds)))


def get_service_status(service_name):
    result = subprocess.run(
        ["systemctl", "is-active", service_name],
        capture_output=True,
        text=True,
    )

    status = result.stdout.strip()

    log_result = subprocess.run(
        ["journalctl", "-u", service_name, "-n", "5", "--no-pager"],
        capture_output=True,
        text=True,
    )

    logs = log_result.stdout.strip()

    return {
        "name": service_name,
        "status": status,
        "is_active": status == "active",
        "logs": logs if logs else "No logs available.",
    }


def get_disks():
    skip_fs = {
        "tmpfs",
        "devtmpfs",
        "proc",
        "sysfs",
        "overlay",
        "squashfs",
        "tracefs",
        "cgroup2",
        "securityfs",
        "debugfs",
        "configfs",
        "fusectl",
        "pstore",
    }

    disks = []
    seen_devices = set()

    for part in psutil.disk_partitions(all=False):
        if part.fstype in skip_fs:
            continue

        mountpoint = part.mountpoint.lower()
        if "/log" in mountpoint or "\\log" in mountpoint:
            continue

        if part.device in seen_devices:
            continue

        try:
            usage = psutil.disk_usage(part.mountpoint)
            seen_devices.add(part.device)

            disks.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": gb(usage.total),
                    "used": gb(usage.used),
                    "free": gb(usage.free),
                    "percent": usage.percent,
                }
            )

        except PermissionError:
            continue

    disks.sort(key=lambda d: d["mountpoint"])

    return disks


def get_top_processes(limit=10):
    processes = []

    for proc in psutil.process_iter(
        ["pid", "name", "username", "cpu_percent", "memory_percent"]
    ):
        try:
            info = proc.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "username": info["username"] or "-",
                    "cpu_percent": round(info["cpu_percent"] or 0, 1),
                    "memory_percent": round(info["memory_percent"] or 0, 1),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    processes.sort(
        key=lambda process: (
            process["cpu_percent"],
            process["memory_percent"],
        ),
        reverse=True,
    )

    return processes[:limit]


def get_dashboard_data():
    cpu_usage = psutil.cpu_percent(interval=0.1)
    cpu_per_core = list(enumerate(psutil.cpu_percent(interval=0.1, percpu=True)))
    cpu_count = psutil.cpu_count()

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    mounted_disks = get_disks()

    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()
    network_usage = get_network_usage(net_io)
    disk_usage = get_disk_usage(disk_io)
    save_metric_sample(
        cpu_usage,
        memory.percent,
        network_usage["total_rate"],
        network_usage["rx_rate"],
        network_usage["tx_rate"],
        disk_usage["read_rate"],
        disk_usage["write_rate"],
    )
    history = get_history()

    services_stats = [get_service_status(svc) for svc in SERVICES_TO_TRACK]
    top_processes = get_top_processes()

    return {
        "uptime": get_uptime(),
        "hostname": socket.gethostname(),
        "cpu_usage": cpu_usage,
        "cpu_per_core": cpu_per_core,
        "cpu_count": cpu_count,
        "memory": memory,
        "memory_used": gb(memory.used),
        "memory_total": gb(memory.total),
        "has_swap": swap.total > 0,
        "swap_total": gb(swap.total),
        "swap_used": gb(swap.used),
        "swap_percent": swap.percent,
        "mounted_disks": mounted_disks,
        "disk_read": mb(disk_io.read_bytes),
        "disk_write": mb(disk_io.write_bytes),
        "disk_read_rate": disk_usage["read_rate_label"],
        "disk_write_rate": disk_usage["write_rate_label"],
        "disk_total_rate": disk_usage["total_rate_label"],
        "net_recv": mb(net_io.bytes_recv),
        "net_sent": mb(net_io.bytes_sent),
        "net_rx_rate": network_usage["rx_rate_label"],
        "net_tx_rate": network_usage["tx_rate_label"],
        "net_total_rate": network_usage["total_rate_label"],
        "cpu_history": history["cpu_history"],
        "memory_history": history["memory_history"],
        "network_history": history["network_history"],
        "services": services_stats,
        "top_processes": top_processes,
    }


@app.route("/")
def dashboard():
    return render_template("dashboard.html", hostname=socket.gethostname())


@app.route("/stats")
def stats():
    return render_template("_stats.html", **get_dashboard_data())


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
