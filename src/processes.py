import psutil

from src.formatting import format_bytes


def get_top_processes(limit=5):
    processes = []

    for proc in psutil.process_iter(
        ["pid", "name", "username", "cpu_percent", "memory_percent"]
    ):
        try:
            info = proc.info
            try:
                io_counters = proc.io_counters()
                read_bytes = io_counters.read_bytes
                write_bytes = io_counters.write_bytes
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                read_bytes = None
                write_bytes = None

            processes.append(
                {
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "username": info["username"] or "-",
                    "cpu_percent": round(info["cpu_percent"] or 0, 1),
                    "memory_percent": round(info["memory_percent"] or 0, 1),
                    "io_read": format_bytes(read_bytes),
                    "io_write": format_bytes(write_bytes),
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
