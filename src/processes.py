import psutil

from src.cache import TtlCache
from src.config import PROCESS_CACHE_SECONDS
from src.formatting import format_bytes

PROCESS_CACHES = {}


def collect_top_processes(limit):
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
                    "io_read": "n/a",
                    "io_write": "n/a",
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

    top_processes = processes[:limit]
    for process in top_processes:
        try:
            io_counters = psutil.Process(process["pid"]).io_counters()
            process["io_read"] = format_bytes(io_counters.read_bytes)
            process["io_write"] = format_bytes(io_counters.write_bytes)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return top_processes


def get_top_processes(limit=5):
    cache = PROCESS_CACHES.setdefault(limit, TtlCache(PROCESS_CACHE_SECONDS))
    return cache.get(lambda: collect_top_processes(limit))
