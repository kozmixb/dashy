import threading
import time

import psutil

from src.config import HISTORY_SAMPLE_INTERVAL_SECONDS
from src.history import save_history_sample
from src.rates import get_disk_throughput, get_network_throughput

SAMPLER_THREAD = None


def collect_metric_sample():
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()

    network_throughput = get_network_throughput(net_io)
    disk_throughput = get_disk_throughput(disk_io)

    save_history_sample(
        cpu_usage,
        memory.percent,
        network_throughput["total_rate"],
        network_throughput["rx_rate"],
        network_throughput["tx_rate"],
        disk_throughput["read_rate"],
        disk_throughput["write_rate"],
    )


def sampler_loop():
    while True:
        try:
            collect_metric_sample()
        except Exception:
            pass

        time.sleep(HISTORY_SAMPLE_INTERVAL_SECONDS)


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
