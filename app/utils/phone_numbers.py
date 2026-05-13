# Normalización de teléfonos usados por el panel y el bot.
#
# El usuario puede escribir el teléfono con espacios, guiones o prefijo +34,
# pero internamente se guarda sin prefijo para evitar duplicados.

import re

SPANISH_PREFIX = "34"
LOCAL_PHONE_LENGTH = 9


def normalize_phone(phone: str) -> str:
    """Devuelve solo dígitos y elimina el prefijo español si viene informado.

    Ejemplos:
    - "+34 666 666 666" -> "666666666"
    - "34 666 666 666" -> "666666666"
    - "0034 666 666 666" -> "666666666"
    - "666666666" -> "666666666"
    """
    digits = re.sub(r"\D+", "", phone or "")

    if digits.startswith("00"):
        digits = digits[2:]

    if digits.startswith(SPANISH_PREFIX) and len(digits) == 11:
        return digits[len(SPANISH_PREFIX):]

    return digits


def is_valid_phone(phone: str) -> bool:
    """Valida teléfonos locales españoles guardados sin prefijo: 9 cifras."""
    normalized = normalize_phone(phone)
    return len(normalized) == LOCAL_PHONE_LENGTH and normalized[:1] in {"6", "7", "8", "9"}
