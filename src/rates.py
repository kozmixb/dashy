import time

from src.formatting import bytes_per_second

LAST_NET_SAMPLE = None
LAST_DISK_SAMPLE = None


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
