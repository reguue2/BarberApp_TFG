# Cancela reservas futuras del cliente de WhatsApp.
#
# Mantiene las reglas extra del bot (cliente debe ser dueño de la reserva,
# no se cancelan reservas pasadas). El panel usa BookingService.cancel_from_panel.

from dataclasses import dataclass
from flask import current_app

from app.extensions import db
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.reserva_repository import ReservaRepository
from app.utils.datetime_utils import now_local


@dataclass
class CancellationResult:
    ok: bool
    reserva: object | None = None
    reservas: list | None = None
    error: str | None = None


class CancellationService:
    def __init__(self, now_func=None):
        self.now_func = now_func

    def now(self):
        return self.now_func() if self.now_func else now_local()

    def list_future_reservations(self, peluqueria_id: int, telefono_cliente: str):
        cliente = ClienteRepository.get_by_phone(peluqueria_id, telefono_cliente)
        if not cliente:
            return []
        return ReservaRepository.list_future_confirmed_by_client(peluqueria_id, cliente.id, self.now())

    def cancel_from_whatsapp(self, peluqueria_id: int, telefono_cliente: str, reserva_id: int):
        cliente = ClienteRepository.get_by_phone(peluqueria_id, telefono_cliente)
        if not cliente:
            return CancellationResult(False, error="client_not_found")

        reserva = ReservaRepository.get_by_id(peluqueria_id, reserva_id)
        if not reserva or reserva.cliente_id != cliente.id:
            return CancellationResult(False, error="reservation_not_found")

        if reserva.estado != "confirmada":
            return CancellationResult(False, error="already_cancelled")

        now = self.now()
        if reserva.fecha < now.date() or (reserva.fecha == now.date() and reserva.hora < now.time()):
            return CancellationResult(False, error="past_reservation")

        try:
            ReservaRepository.cancel(reserva)
            db.session.commit()
            return CancellationResult(True, reserva=reserva)
        except Exception:
            current_app.logger.exception("Error cancelando reserva %s desde WhatsApp", reserva_id)
            db.session.rollback()
            return CancellationResult(False, error="unexpected_error")
