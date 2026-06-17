# System Dashboard

A lightweight Flask and HTMX dashboard for monitoring a Linux host from a browser. It is built for small servers, home lab machines, nodes, and services where you want a quick read on system health without installing a full observability stack.

The dashboard shows CPU, memory, network throughput, storage usage, disk I/O, selected systemd service state, recent service logs, and top resource-heavy processes. It stores short-term metric history locally in SQLite so the graphs remain useful across refreshes while keeping the setup simple and self-contained.

![System Dashboard screenshot](dash.png)

## Why Use It

- Quick browser-based view of a Linux machine
- No external database, agent, or hosted monitoring service required
- HTMX updates keep the dashboard live without full page reloads
- Useful for checking service health, resource usage, and recent logs in one place
- Small enough to run directly on the server it monitors

## Requirements

- Python 3.10+
- Linux with systemd for service status and journal output
- Access to `systemctl` and `journalctl`
- A modern browser

## Local Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python3 app.py
```

Open:

```text
http://localhost:5000
```

Direct `python3 app.py` listens on `0.0.0.0:5000` by default so it can be opened
from another machine on the same network. Set `STATS_DASHBOARD_HOST` and
`STATS_DASHBOARD_PORT` if you need a different bind address.

## Configuration

Tracked services are configured in `src/config.py`:

```python
SERVICES_TO_TRACK = ["xmr"]
```

Update that list with the systemd unit names you want displayed.

Metric history is stored in a local SQLite database at `data/stats.sqlite3`.
The app runs a background sampler while the server process is running, keeps one sample every 10 seconds, and deletes samples older than one day.

The SQLite database is ignored by Git so runtime metric data is not committed.

## Running With Gunicorn

For a production-style run from the project directory:

```bash
source .venv/bin/activate
gunicorn --workers 2 --bind 0.0.0.0:5000 app:app
```

## Running With Docker

Build the image locally:

```bash
docker build -t stats-dashboard .
```

Create a persistent volume for SQLite metric history:

```bash
docker volume create stats-data
```

Run it with Docker only:

```bash
docker run -d \
  --name stats-dashboard \
  --restart unless-stopped \
  -p 5000:5000 \
  -v stats-data:/app/data \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  stats-dashboard
```

Open:

```text
http://localhost:5000
```

View logs:

```bash
docker logs -f stats-dashboard
```

Stop and remove the container:

```bash
docker stop stats-dashboard
docker rm stats-dashboard
```

Or use Docker Compose instead:

```bash
docker compose up --build
```

The image is based on Alpine Linux, runs as an unprivileged user, and stores
metric history in `/app/data`. The Docker and Compose examples add hardening
defaults such as a read-only root filesystem, dropped Linux capabilities,
`no-new-privileges`, and a tmpfs-backed `/tmp`.

Containers generally see container-scoped process and network information. If
you need full host-level service state and journal output, run the app directly
on the host with systemd access instead of inside Docker.

## Docker Hub Releases

Publishing to Docker Hub is handled by GitHub Actions when a GitHub release is
published. Configure these repository secrets first:

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

Release images are published to:

```text
DOCKERHUB_USERNAME/<github-repository-name>
```

## systemd Service

An example unit file is provided at `stats-dashboard.service.example`.

Copy it to systemd:

```bash
sudo cp stats-dashboard.service.example /etc/systemd/system/stats-dashboard.service
```

Edit these values in `/etc/systemd/system/stats-dashboard.service`:

```ini
User=your-user
Group=your-user
WorkingDirectory=/opt/stats
ExecStart=/opt/stats/.venv/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 app:app
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now stats-dashboard
sudo systemctl status stats-dashboard
```

View logs:

```bash
sudo journalctl -u stats-dashboard -f
```
