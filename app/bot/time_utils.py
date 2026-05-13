# Funciones pequeñas para trabajar con horas y solapamientos.

from datetime import time


def to_min(value) -> int:
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    text = str(value).strip()
    parts = text.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def from_min(value: int) -> str:
    value = max(0, int(value))
    h, m = divmod(value, 60)
    return f"{h:02d}:{m:02d}"


def to_time(value) -> time:
    if isinstance(value, time):
        return value
    text = str(value).strip()
    if ":" not in text:
        text = f"{int(text):02d}:00"
    h, m = text.split(":")[:2]
    return time(int(h), int(m))


def hhmm(value) -> str:
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return to_time(value).strftime("%H:%M")


def overlap(start1, dur1: int, start2, dur2: int) -> bool:
    s1 = to_min(start1)
    e1 = s1 + int(dur1)
    s2 = to_min(start2)
    e2 = s2 + int(dur2)
    return s1 < e2 and s2 < e1
