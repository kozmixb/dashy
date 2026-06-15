import threading
import time

import psutil

from src.config import HISTORY_SAMPLE_INTERVAL
from src.history import save_metric_sample
from src.rates import get_disk_usage, get_network_usage

SAMPLER_THREAD = None


def collect_metric_sample():
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
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


def sampler_loop():
    while True:
        try:
            collect_metric_sample()
        except Exception:
            pass

        time.sleep(HISTORY_SAMPLE_INTERVAL)


def start_background_sampler():
    global SAMPLER_THREAD

    if SAMPLER_THREAD and SAMPLER_THREAD.is_alive():
        return

    SAMPLER_THREAD = threading.Thread(
        target=sampler_loop,
        name="stats-metric-sampler",
        daemon=True,
    )
    SAMPLER_THREAD.start()
