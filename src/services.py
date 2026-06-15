import subprocess
from datetime import datetime

from src.config import SERVICE_COMMAND_TIMEOUT_SECONDS, SERVICES_TO_TRACK
from src.formatting import format_bytes


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


def run_service_command(command):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=SERVICE_COMMAND_TIMEOUT_SECONDS,
            errors="replace",
        )
    except (subprocess.TimeoutExpired, OSError):
        return None


def format_service_uptime(active_since):
    if not active_since or active_since == "n/a":
        return "n/a"

    try:
        started_at = datetime.strptime(
            active_since.rsplit(" ", 1)[0],
            "%a %Y-%m-%d %H:%M:%S",
        )
    except ValueError:
        return "n/a"

    elapsed = datetime.now() - started_at
    days = elapsed.days
    hours, remainder = divmod(elapsed.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_service_status(service_name):
    result = run_service_command(["systemctl", "is-active", service_name])
    status = result.stdout.strip() if result else "unknown"

    log_result = run_service_command(
        ["journalctl", "-u", service_name, "-n", "5", "--no-pager"]
    )
    logs = log_result.stdout.strip() if log_result else ""

    show_result = run_service_command(
        [
            "systemctl",
            "show",
            service_name,
            "--property=UnitFileState",
            "--property=MemoryPeak",
            "--property=MemoryCurrent",
            "--property=ActiveEnterTimestamp",
            "--no-pager",
        ]
    )
    properties = parse_systemd_show(show_result.stdout) if show_result else {}
    memory_peak = parse_systemd_value(properties.get("MemoryPeak", ""))
    memory_current = parse_systemd_value(properties.get("MemoryCurrent", ""))
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
        "active_since": active_since,
        "uptime": format_service_uptime(active_since),
        "logs": logs if logs else "No logs available.",
    }


def get_tracked_services_status():
    return [get_service_status(svc) for svc in SERVICES_TO_TRACK]
