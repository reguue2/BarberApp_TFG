# Guarda temporalmente el paso actual de cada conversación.

from copy import deepcopy
from datetime import datetime, timedelta


class MemoryStateStore:
    def __init__(self, ttl_minutes: int = 30):
        self.ttl = timedelta(minutes=ttl_minutes)
        self._data = {}

    def get(self, session_id: str):
        item = self._data.get(session_id)
        if not item:
            return None
        state, updated_at = item
        if datetime.utcnow() - updated_at > self.ttl:
            self.delete(session_id)
            return None
        return deepcopy(state)

    def set(self, session_id: str, state: dict):
        self._data[session_id] = (deepcopy(state), datetime.utcnow())

    def delete(self, session_id: str):
        self._data.pop(session_id, None)


def empty_state():
    return {
        "step": "inicio",
        "action": None,
        "data": {},
    }
