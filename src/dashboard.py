import socket

import psutil

from src.formatting import format_bytes_short
from src.history import get_chart_history
from src.host import get_primary_ip, get_uptime
from src.listeners import get_public_listeners
from src.processes import get_top_processes
from src.rates import get_disk_throughput, get_network_throughput
from src.services import get_tracked_services_status
from src.storage import get_mounted_disks


def get_dashboard_data():
    cpu_usage = psutil.cpu_percent(interval=0.1)
    cpu_per_core = list(enumerate(psutil.cpu_percent(interval=0.1, percpu=True)))
    cpu_count = psutil.cpu_count()

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    mounted_disks = get_mounted_disks()

    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()
    network_throughput = get_network_throughput(net_io)
    disk_throughput = get_disk_throughput(disk_io)
    chart_history = get_chart_history()

    return {
        "uptime": get_uptime(),
        "hostname": socket.gethostname(),
        "cpu_usage": cpu_usage,
        "cpu_per_core": cpu_per_core,
        "cpu_count": cpu_count,
        "memory": memory,
        "memory_used": format_bytes_short(memory.used),
        "memory_total": format_bytes_short(memory.total),
        "has_swap": swap.total > 0,
        "swap_total": format_bytes_short(swap.total),
        "swap_used": format_bytes_short(swap.used),
        "swap_percent": swap.percent,
        "mounted_disks": mounted_disks,
        "disk_read": format_bytes_short(disk_io.read_bytes),
        "disk_write": format_bytes_short(disk_io.write_bytes),
        "disk_read_rate": disk_throughput["read_rate_label"],
        "disk_write_rate": disk_throughput["write_rate_label"],
        "disk_total_rate": disk_throughput["total_rate_label"],
        "net_recv": format_bytes_short(net_io.bytes_recv),
        "net_sent": format_bytes_short(net_io.bytes_sent),
        "net_rx_rate": network_throughput["rx_rate_label"],
        "net_tx_rate": network_throughput["tx_rate_label"],
        "net_total_rate": network_throughput["total_rate_label"],
        "primary_ip": get_primary_ip(),
        "cpu_history": chart_history["cpu_history"],
        "memory_history": chart_history["memory_history"],
        "network_history": chart_history["network_history"],
        "services": get_tracked_services_status(),
        "top_processes": get_top_processes(),
        "listening_ports": get_public_listeners(),
    }
