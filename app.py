import socket

from flask import Flask, render_template

from src.dashboard import get_dashboard_data

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("dashboard.html", hostname=socket.gethostname())


@app.route("/stats")
def stats():
    return render_template("_stats.html", **get_dashboard_data())


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
