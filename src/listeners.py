import ipaddress
import socket

import psutil

from src.config import HIDDEN_LISTENER_PORTS


def is_public_ipv4(address):
    try:
        ip_address = ipaddress.ip_address(address)
    except ValueError:
        return False

    return ip_address.version == 4 and not ip_address.is_loopback


def format_listener_address(host, port):
    if host == "0.0.0.0":
        return f":{port}"

    return f"{host}:{port}"


def get_public_listeners():
    listeners = []
    seen = set()

    try:
        connections = psutil.net_connections(kind="inet")
    except psutil.AccessDenied:
        return listeners

    for connection in connections:
        if not connection.laddr:
            continue

        is_tcp_listener = (
            connection.type == socket.SOCK_STREAM
            and connection.status == psutil.CONN_LISTEN
        )
        is_udp_bound = connection.type == socket.SOCK_DGRAM
        if not is_tcp_listener and not is_udp_bound:
            continue

        host = connection.laddr.ip
        port = connection.laddr.port
        if port in HIDDEN_LISTENER_PORTS or not is_public_ipv4(host):
            continue

        protocol = "tcp" if connection.type == socket.SOCK_STREAM else "udp"
        process_name = "-"
        if connection.pid:
            try:
                process_name = psutil.Process(connection.pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                process_name = "-"

        key = (protocol, host, port, process_name)
        if key in seen:
            continue

        seen.add(key)
        listeners.append(
            {
                "protocol": protocol,
                "host": host,
                "port": port,
                "display_address": format_listener_address(host, port),
                "process": process_name,
            }
        )

    listeners.sort(
        key=lambda listener: (
            listener["port"],
            listener["protocol"],
            listener["host"],
        )
    )
    return listeners
