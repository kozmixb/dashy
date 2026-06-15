import os
import socket

from flask import Flask, render_template

from src.dashboard import get_dashboard_data
from src.sampler import start_background_sampler

app = Flask(__name__)

if __name__ != "__main__" or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    start_background_sampler()


@app.route("/")
def dashboard():
    return render_template("dashboard.html", hostname=socket.gethostname())


@app.route("/stats")
def stats():
    return render_template("_stats.html", **get_dashboard_data())


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_background_sampler()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
