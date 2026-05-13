# Fechas locales de la aplicación.
#
# El panel y el bot deben tomar "hoy" desde la misma zona horaria.
# Así evitamos diferencias si el servidor corre en UTC.

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app


def app_timezone() -> ZoneInfo:
    return ZoneInfo(current_app.config.get("APP_TZ", "Europe/Madrid"))


def now_local() -> datetime:
    return datetime.now(app_timezone()).replace(tzinfo=None)


def today_local():
    return now_local().date()
