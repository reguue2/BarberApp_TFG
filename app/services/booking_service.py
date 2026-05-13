# Servicio central para crear y cancelar reservas.
#
# Este servicio es la única fuente de verdad de la lógica de reservas.
# Tanto el bot de WhatsApp como el panel web crean y cancelan reservas
# llamando aquí, para que las reglas (solapamientos, capacidad, días
# cerrados, horarios, anticipación mínima) sean idénticas.

from dataclasses import dataclass
from datetime import date, datetime
import re
import unicodedata

from flask import current_app

from app.utils.phone_numbers import is_valid_phone, normalize_phone
from app.bot.time_utils import to_time
from app.extensions import db
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.reserva_repository import ReservaRepository
from app.repositories.servicio_repository import ServicioRepository
from app.services.availability_service import AvailabilityService
from app.utils.datetime_utils import now_local


@dataclass
class BookingResult:
    ok: bool
    reserva: object | None = None
    error: str | None = None
    available_slots: list[str] | None = None
    details: dict | None = None


@dataclass
class CancellationResult:
    ok: bool
    reserva: object | None = None
    error: str | None = None


class BookingService:
    """Orquesta creación y cancelación de reservas para cualquier canal."""

    def __init__(self, availability_service: AvailabilityService | None = None, now_func=None):
        self.availability_service = availability_service or AvailabilityService(now_func=now_func)
        self.now_func = now_func

    def now(self) -> datetime:
        return self.now_func() if self.now_func else now_local()

    # -------- Crear reserva --------

    def create_reservation(
        self,
        peluqueria,
        servicio_id: int,
        telefono_cliente: str,
        nombre_cliente: str | None,
        fecha: date,
        hora_txt: str,
        origen: str,
    ) -> BookingResult:
        """Crea una reserva confirmada validando disponibilidad real.

        - peluqueria: instancia Peluqueria (el peluqueria_id del usuario sale de su sesión, no del form).
        - origen: 'whatsapp' o 'panel'.
        """
        if not telefono_cliente or not telefono_cliente.strip():
            return BookingResult(False, error="phone_required")

        if not nombre_cliente or not nombre_cliente.strip():
            return BookingResult(False, error="client_name_required")

        servicio = ServicioRepository.get_active_by_id(peluqueria.id, servicio_id)
        if not servicio:
            return BookingResult(False, error="service_not_found")

        telefono = normalize_phone(telefono_cliente)
        if not telefono:
            return BookingResult(False, error="phone_required")
        if not is_valid_phone(telefono):
            return BookingResult(False, error="invalid_phone")

        try:
            hora = to_time(hora_txt)
        except (ValueError, AttributeError, TypeError):
            return BookingResult(False, error="invalid_time")

        try:
            cliente = ClienteRepository.get_by_phone(peluqueria.id, telefono)
            if cliente and _different_client_name(cliente.nombre, nombre_cliente):
                return BookingResult(
                    False,
                    error="client_phone_conflict",
                    details={
                        "existing_name": cliente.nombre,
                        "existing_phone": normalize_phone(cliente.telefono),
                    },
                )

            available = self.availability_service.get_available_slots_for_service(peluqueria, servicio, fecha)
            if hora.strftime("%H:%M") not in available:
                return BookingResult(False, error="slot_not_available", available_slots=available)

            if not cliente:
                cliente = ClienteRepository.create(peluqueria.id, telefono, nombre_cliente)
            db.session.flush()
            reserva = ReservaRepository.create(
                peluqueria_id=peluqueria.id,
                cliente_id=cliente.id,
                servicio_id=servicio.id,
                fecha=fecha,
                hora=hora,
                origen=origen,
            )
            db.session.commit()
            return BookingResult(True, reserva=reserva)
        except Exception:
            current_app.logger.exception("Error creando reserva para peluquería %s", peluqueria.id)
            db.session.rollback()
            return BookingResult(False, error="unexpected_error")

    # -------- Cancelar desde el panel --------
    # (sin verificar pertenencia al cliente: el admin de la peluquería puede cancelar
    # cualquier reserva de su propia peluquería)

    def cancel_from_panel(self, peluqueria_id: int, reserva_id: int) -> CancellationResult:
        reserva = ReservaRepository.get_by_id(peluqueria_id, reserva_id)
        if not reserva:
            return CancellationResult(False, error="reservation_not_found")

        if reserva.estado != "confirmada":
            return CancellationResult(False, error="already_cancelled")

        try:
            ReservaRepository.cancel(reserva)
            db.session.commit()
            return CancellationResult(True, reserva=reserva)
        except Exception:
            current_app.logger.exception("Error cancelando reserva %s desde el panel", reserva_id)
            db.session.rollback()
            return CancellationResult(False, error="unexpected_error")


def _normalize_name_for_match(value: str | None) -> str:
    """Normaliza nombres para detectar conflictos sin ser sensible a mayúsculas o tildes."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text


def _different_client_name(existing_name: str | None, submitted_name: str | None) -> bool:
    return _normalize_name_for_match(existing_name) != _normalize_name_for_match(submitted_name)
