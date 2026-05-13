# Evita procesar dos veces el mismo mensaje de WhatsApp.

from datetime import datetime, timedelta


class IdempotencyService:
    def __init__(self, ttl_minutes: int = 15):
        self.ttl = timedelta(minutes=ttl_minutes)
        self._seen = {}

    def already_processed(self, key: str) -> bool:
        self._clean()
        if not key:
            return False
        if key in self._seen:
            return True
        self._seen[key] = datetime.utcnow()
        return False

    def _clean(self):
        now = datetime.utcnow()
        expired = [key for key, value in self._seen.items() if now - value > self.ttl]
        for key in expired:
            self._seen.pop(key, None)
