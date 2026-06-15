import os
import socket

from flask import Flask, render_template

from src.dashboard import get_dashboard_data
from src.sampler import start_background_sampler

app = Flask(__name__)

if __name__ != "__main__" or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    start_background_sampler()


@app.after_request
def set_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "base-uri 'none'; "
        "frame-ancestors 'none'",
    )
    return response


@app.route("/")
def dashboard():
    return render_template("dashboard.html", hostname=socket.gethostname())


@app.route("/stats")
def stats():
    return render_template("_stats.html", **get_dashboard_data())


if __name__ == "__main__":
    debug_enabled = os.environ.get("FLASK_DEBUG") == "1"
    if not debug_enabled or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_background_sampler()

    host = os.environ.get("STATS_DASHBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("STATS_DASHBOARD_PORT", "5000"))

    app.run(
        host=host,
        port=port,
        debug=debug_enabled,
    )
