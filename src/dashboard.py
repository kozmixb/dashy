import socket

import psutil

from src.formatting import gb, mb
from src.history import get_history
from src.host import get_primary_ip, get_uptime
from src.listeners import get_public_listening_ports
from src.processes import get_top_processes
from src.rates import get_disk_usage, get_network_usage
from src.services import get_services_status
from src.storage import get_disks


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
    history = get_history()

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
        "primary_ip": get_primary_ip(),
        "cpu_history": history["cpu_history"],
        "memory_history": history["memory_history"],
        "network_history": history["network_history"],
        "services": get_services_status(),
        "top_processes": get_top_processes(),
        "listening_ports": get_public_listening_ports(),
    }
