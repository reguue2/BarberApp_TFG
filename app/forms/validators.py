# Validadores ligeros para los formularios del panel.
#
# No usamos WTForms en este TFG para no añadir capas; se valida a mano
# con funciones simples y mensajes de error claros en español.

import re
from datetime import date, time
from decimal import Decimal, InvalidOperation

from app.utils.phone_numbers import is_valid_phone, normalize_phone

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s]{9,30}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
TIME_DIGITS_RE = re.compile(r"^\d{3,4}$")


def clean_str(value, max_len: int) -> str:
    text = (value or "").strip()
    return text[:max_len]


def parse_email(value: str) -> str | None:
    text = (value or "").strip().lower()
    if not text or not EMAIL_RE.match(text) or len(text) > 150:
        return None
    return text


def parse_phone(value: str) -> str | None:
    text = (value or "").strip()
    if not text or not PHONE_RE.match(text):
        return None
    digits = normalize_phone(text)
    if not is_valid_phone(digits):
        return None
    return digits


def parse_int(value, minimum: int | None = None, maximum: int | None = None) -> int | None:
    try:
        n = int(str(value).strip())
    except (ValueError, AttributeError, TypeError):
        return None
    if minimum is not None and n < minimum:
        return None
    if maximum is not None and n > maximum:
        return None
    return n


def parse_decimal(value, max_digits: int = 8, decimals: int = 2) -> Decimal | None:
    try:
        d = Decimal(str(value).replace(",", ".").strip())
    except (InvalidOperation, AttributeError, TypeError):
        return None
    if d < 0:
        return None
    quantized = d.quantize(Decimal("0.01"))
    # 8,2 → máximo 999999.99
    if quantized >= Decimal(10) ** (max_digits - decimals):
        return None
    return quantized


def parse_date(value) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except (ValueError, TypeError):
        return None


def parse_time(value) -> time | None:
    text = (value or "").strip()
    if not text:
        return None
    if TIME_DIGITS_RE.match(text):
        padded = text.zfill(4)
        text = f"{padded[:2]}:{padded[2:]}"
    if not TIME_RE.match(text):
        return None
    try:
        return time.fromisoformat(text + ":00" if len(text) == 5 else text)
    except (ValueError, TypeError):
        return None


def parse_dia_semana(value) -> int | None:
    return parse_int(value, minimum=1, maximum=7)
