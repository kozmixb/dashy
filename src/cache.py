import threading
import time


class TtlCache:
    def __init__(self, ttl_seconds):
        self.ttl_seconds = ttl_seconds
        self.expires_at = 0
        self.value = None
        self.lock = threading.Lock()

    def get(self, loader):
        now = time.monotonic()
        if now < self.expires_at:
            return self.value

        with self.lock:
            now = time.monotonic()
            if now < self.expires_at:
                return self.value

            self.value = loader()
            self.expires_at = now + self.ttl_seconds
            return self.value
