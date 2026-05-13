# Utilidades pequeñas para limpiar teléfonos y comandos generales.

import re
import unicodedata

from app.utils.phone_numbers import normalize_phone as _normalize_phone


def normalize_phone(phone: str) -> str:
    return _normalize_phone(phone)


def _clean_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text)


def detect_global_command(text: str):
    clean = _clean_text(text)
    if clean in {"menu", "menú", "inicio", "empezar", "volver"}:
        return "menu"
    if clean in {"salir", "reset", "cancelar todo"}:
        return "reset"
    return None
