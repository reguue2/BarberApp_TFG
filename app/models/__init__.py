# Importa todos los modelos para que SQLAlchemy los registre.

from app.models.peluqueria import Peluqueria
from app.models.usuario_admin import UsuarioAdmin
from app.models.cliente import Cliente
from app.models.servicio import Servicio
from app.models.profesional import Profesional
from app.models.horario_apertura import HorarioApertura
from app.models.dia_cerrado import DiaCerrado
from app.models.reserva import Reserva

__all__ = [
    "Peluqueria",
    "UsuarioAdmin",
    "Cliente",
    "Servicio",
    "Profesional",
    "HorarioApertura",
    "DiaCerrado",
    "Reserva",
]
