import psutil

from src.formatting import format_bytes


def get_mounted_disks():
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
            used_percent = (
                round((usage.used / usage.total) * 100, 1) if usage.total else 0
            )

            disks.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": format_bytes(usage.total),
                    "used": format_bytes(usage.used),
                    "free": format_bytes(usage.free),
                    "percent": used_percent,
                }
            )

        except PermissionError:
            continue

    disks.sort(key=lambda d: d["mountpoint"])

    return disks
