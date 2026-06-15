from datetime import timedelta


def gb(value):
    return round(value / (1024**3), 2)


def mb(value):
    return round(value / (1024**2), 1)


def format_bytes(value):
    if value is None:
        return "n/a"

    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    size = float(value)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{size:.0f} {unit}"
            if size >= 100:
                return f"{size:.0f} {unit}"
            if size >= 10:
                return f"{size:.1f} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024


def bytes_per_second(value):
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    size = float(value)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024


def format_nsec(value):
    if value is None:
        return "n/a"

    seconds = int(value / 1_000_000_000)
    return str(timedelta(seconds=seconds))


def format_percent(value):
    return f"{value:.1f}%"
