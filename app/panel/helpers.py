# Utilidades comunes del panel.

from datetime import date, datetime
from functools import wraps

from flask import abort
from flask_login import current_user, login_required as _login_required

from app.repositories.peluqueria_repository import PeluqueriaRepository
from app.utils.datetime_utils import today_local


def login_required(view_func):
    """Wrapper de Flask-Login que añade comprobación de cuenta activa."""
    decorated = _login_required(view_func)

    @wraps(decorated)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and not current_user.activo:
            abort(403)
        return decorated(*args, **kwargs)

    return wrapper


def current_peluqueria_id() -> int:
    """ID de la peluquería del usuario autenticado.

    Nunca aceptar este valor desde un formulario: siempre sale del usuario.
    """
    if not current_user.is_authenticated:
        abort(401)
    return current_user.peluqueria_id


def current_peluqueria():
    pelu = PeluqueriaRepository.get_by_id(current_peluqueria_id())
    if not pelu:
        abort(404)
    return pelu


# ---- Filtros Jinja ----

def fmt_date(value) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d/%m/%Y")


def fmt_time(value) -> str:
    if not value:
        return "—"
    return value.strftime("%H:%M")


def fmt_money(value) -> str:
    if value is None:
        return "—"
    return f"{float(value):.2f} €"


def visual_estado(reserva, hoy: date | None = None) -> str:
    """Estado mostrado al admin: cancelada, completada (pasada) o confirmada."""
    if reserva.estado == "cancelada":
        return "cancelada"
    today = hoy or today_local()
    if reserva.fecha < today:
        return "completada"
    return "confirmada"
