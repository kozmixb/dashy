from pathlib import Path

SERVICES_TO_TRACK = ["xmr"]
HIDDEN_LISTENER_PORTS = {68, 5355}
HISTORY_SAMPLE_INTERVAL = 10
HISTORY_LIMIT = 60
RETENTION_SECONDS = 24 * 60 * 60

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "stats.sqlite3"
