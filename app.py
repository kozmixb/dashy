import subprocess
import time
from datetime import timedelta

import psutil
from flask import Flask, render_template_string

app = Flask(__name__)

# --- CONFIGURATION ---
SERVICES_TO_TRACK = ["xmr"]


def gb(value):
    return round(value / (1024**3), 2)


def mb(value):
    return round(value / (1024**2), 1)


def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            return str(timedelta(seconds=int(uptime_seconds)))
    except Exception:
        uptime_seconds = time.time() - psutil.boot_time()
        return str(timedelta(seconds=int(uptime_seconds)))


def get_service_status(service_name):
    result = subprocess.run(
        ["systemctl", "is-active", service_name],
        capture_output=True,
        text=True,
    )

    status = result.stdout.strip()

    log_result = subprocess.run(
        ["journalctl", "-u", service_name, "-n", "5", "--no-pager"],
        capture_output=True,
        text=True,
    )

    logs = log_result.stdout.strip()

    return {
        "name": service_name,
        "status": status,
        "is_active": status == "active",
        "logs": logs if logs else "No logs available.",
    }


def get_disks():
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

    for part in psutil.disk_partitions(all=False):
        if part.fstype in skip_fs:
            continue

        try:
            usage = psutil.disk_usage(part.mountpoint)

            disks.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": gb(usage.total),
                    "used": gb(usage.used),
                    "free": gb(usage.free),
                    "percent": usage.percent,
                }
            )

        except PermissionError:
            continue

    disks.sort(key=lambda d: d["mountpoint"])

    return disks


@app.route("/")
def dashboard():

    cpu_usage = psutil.cpu_percent(interval=0.1)
    cpu_per_core = list(enumerate(psutil.cpu_percent(interval=0.1, percpu=True)))
    cpu_count = psutil.cpu_count()

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    mounted_disks = get_disks()

    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()

    services_stats = [get_service_status(svc) for svc in SERVICES_TO_TRACK]

    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>System Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<meta http-equiv="refresh" content="5">
</head>

<body class="bg-slate-900 text-slate-100 min-h-screen font-sans antialiased p-6 md:p-12">

<div class="max-w-7xl mx-auto space-y-8">

<header class="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-800 pb-6 gap-4">

<div>
<h1 class="text-3xl font-bold text-white">System Dashboard</h1>
<p class="text-sm text-slate-400">
Lightweight real-time node monitoring
</p>
</div>

<div class="bg-slate-800 border border-slate-700 px-4 py-2 rounded-xl">

<span class="text-slate-400 text-sm">
Uptime
</span>

<div class="font-mono text-white">
{{ uptime }}
</div>

</div>

</header>


<section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

<div class="bg-slate-800/40 border border-slate-800 rounded-2xl p-6">

<div class="text-sm text-slate-400 uppercase">
CPU Usage
</div>

<div class="text-4xl font-bold mt-2">
{{ cpu_usage }}%
</div>

<div class="text-xs text-slate-500 mt-1">
{{ cpu_count }} Logical Cores
</div>

<div class="w-full bg-slate-700 rounded-full h-2 mt-4 overflow-hidden">
<div class="bg-indigo-500 h-2 rounded-full"
style="width: {{ cpu_usage }}%">
</div>
</div>

<div class="mt-5 space-y-2">

{% for core, usage in cpu_per_core %}

<div>

<div class="flex justify-between text-xs mb-1">

<span class="text-slate-400">
Core {{ core }}
</span>

<span class="text-white">
{{ usage }}%
</span>

</div>

<div class="w-full bg-slate-700 rounded-full h-1 overflow-hidden">

<div class="bg-indigo-400 h-1 rounded-full"
style="width: {{ usage }}%">
</div>

</div>

</div>

{% endfor %}

</div>

</div>


<div class="bg-slate-800/40 border border-slate-800 rounded-2xl p-6">

<div class="text-sm text-slate-400 uppercase">
RAM Usage
</div>

<div class="text-4xl font-bold mt-2">
{{ memory.percent }}%
</div>

<div class="text-xs text-slate-500 mt-1">

{{ memory_used }} GB /
{{ memory_total }} GB

</div>

<div class="w-full bg-slate-700 rounded-full h-2 mt-4 overflow-hidden">

<div class="bg-emerald-500 h-2 rounded-full"
style="width: {{ memory.percent }}%">
</div>

</div>

{% if has_swap %}

<div class="border-t border-slate-700 mt-5 pt-5">

<div class="text-sm text-slate-400 uppercase">
Swap
</div>

<div class="text-2xl font-bold mt-1">
{{ swap_percent }}%
</div>

<div class="text-xs text-slate-500">

{{ swap_used }} GB /
{{ swap_total }} GB

</div>

<div class="w-full bg-slate-700 rounded-full h-2 mt-4 overflow-hidden">

<div class="bg-cyan-500 h-2 rounded-full"
style="width: {{ swap_percent }}%">
</div>

</div>

</div>

{% endif %}

</div>


<div class="bg-slate-800/40 border border-slate-800 rounded-2xl p-6">

<div class="text-sm text-slate-400 uppercase">
Accumulated I/O
</div>

<div class="mt-6 space-y-3 font-mono text-sm">

<div class="flex justify-between">
<span>Disk Read</span>
<span>{{ disk_read }} MB</span>
</div>

<div class="flex justify-between">
<span>Disk Write</span>
<span>{{ disk_write }} MB</span>
</div>

<div class="border-t border-slate-700 pt-3 flex justify-between">
<span>Network RX</span>
<span>{{ net_recv }} MB</span>
</div>

<div class="flex justify-between">
<span>Network TX</span>
<span>{{ net_sent }} MB</span>
</div>

</div>

</div>

</section>


<section class="space-y-4">

<h2 class="text-xl font-bold">
Mounted Storage
</h2>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

{% for disk in mounted_disks %}

<div class="bg-slate-800/30 border border-slate-800 rounded-2xl p-5">

<div class="flex justify-between">

<div>

<div class="font-mono text-white">
{{ disk.mountpoint }}
</div>

<div class="text-xs text-slate-500">
{{ disk.device }}
</div>

</div>

<div class="text-xs text-slate-500">
{{ disk.fstype }}
</div>

</div>

<div class="text-3xl font-bold mt-4">
{{ disk.percent }}%
</div>

<div class="text-xs text-slate-500">

{{ disk.used }} GB /
{{ disk.total }} GB

</div>

<div class="w-full bg-slate-700 rounded-full h-2 mt-4 overflow-hidden">

<div class="bg-amber-500 h-2 rounded-full"
style="width: {{ disk.percent }}%">
</div>

</div>

<div class="text-xs text-slate-400 mt-3">

Free: {{ disk.free }} GB

</div>

</div>

{% endfor %}

</div>

</section>


<section class="space-y-4">

<h2 class="text-xl font-bold">
Systemd Managed Services
</h2>

{% for svc in services %}

<div class="bg-slate-800/30 border border-slate-800 rounded-2xl p-5">

<div class="flex items-center justify-between">

<div class="font-mono text-lg">

{{ svc.name }}

</div>

{% if svc.is_active %}

<div class="text-emerald-400">

● Active

</div>

{% else %}

<div class="text-rose-400">

● {{ svc.status }}

</div>

{% endif %}

</div>

<div class="bg-slate-950 rounded-xl mt-4 p-4 border border-slate-800">

<div class="text-xs text-slate-500 mb-2 uppercase">

Recent Logs

</div>

<pre class="text-xs text-slate-400 whitespace-pre-wrap overflow-x-auto">

{{ svc.logs }}

</pre>

</div>

</div>

{% endfor %}

</section>

</div>

</body>
</html>
"""

    return render_template_string(
        HTML_TEMPLATE,
        uptime=get_uptime(),
        cpu_usage=cpu_usage,
        cpu_per_core=cpu_per_core,
        cpu_count=cpu_count,
        memory=memory,
        memory_used=gb(memory.used),
        memory_total=gb(memory.total),
        has_swap=swap.total > 0,
        swap_total=gb(swap.total),
        swap_used=gb(swap.used),
        swap_percent=swap.percent,
        mounted_disks=mounted_disks,
        disk_read=mb(disk_io.read_bytes),
        disk_write=mb(disk_io.write_bytes),
        net_recv=mb(net_io.bytes_recv),
        net_sent=mb(net_io.bytes_sent),
        services=services_stats,
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
