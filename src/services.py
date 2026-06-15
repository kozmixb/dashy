import subprocess

from src.config import SERVICES_TO_TRACK
from src.formatting import format_bytes, format_nsec


def parse_systemd_value(value):
    if value in {"", "[not set]", "infinity"}:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def parse_systemd_show(output):
    properties = {}

    for line in output.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        properties[key] = value

    return properties


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

    show_result = subprocess.run(
        [
            "systemctl",
            "show",
            service_name,
            "--property=UnitFileState",
            "--property=CPUUsageNSec",
            "--property=MemoryPeak",
            "--property=MemoryCurrent",
            "--property=ActiveEnterTimestamp",
            "--no-pager",
        ],
        capture_output=True,
        text=True,
    )
    properties = parse_systemd_show(show_result.stdout)
    memory_peak = parse_systemd_value(properties.get("MemoryPeak", ""))
    memory_current = parse_systemd_value(properties.get("MemoryCurrent", ""))
    cpu_usage_nsec = parse_systemd_value(properties.get("CPUUsageNSec", ""))
    enabled_state = properties.get("UnitFileState") or "unknown"
    active_since = properties.get("ActiveEnterTimestamp") or "n/a"

    return {
        "name": service_name,
        "status": status,
        "is_active": status == "active",
        "enabled_state": enabled_state,
        "is_enabled": enabled_state == "enabled",
        "memory_peak": format_bytes(memory_peak),
        "memory_current": format_bytes(memory_current),
        "cpu_time": format_nsec(cpu_usage_nsec),
        "active_since": active_since,
        "logs": logs if logs else "No logs available.",
    }


def get_services_status():
    return [get_service_status(svc) for svc in SERVICES_TO_TRACK]
