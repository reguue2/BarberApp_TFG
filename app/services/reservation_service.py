# Crea reservas confirmadas desde el flujo de WhatsApp.
#
# Delega en BookingService para que panel y bot compartan exactamente
# la misma lógica de reservas. Mantiene la firma usada por el bot.

from dataclasses import dataclass
from datetime import date

from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService


@dataclass
class ReservationResult:
    ok: bool
    reserva: object | None = None
    error: str | None = None
    available_slots: list[str] | None = None


class ReservationService:
    def __init__(self, availability_service: AvailabilityService | None = None):
        self.availability_service = availability_service or AvailabilityService()
        self.booking_service = BookingService(availability_service=self.availability_service)

    def create_from_whatsapp(self, peluqueria, servicio_id: int, telefono_cliente: str,
                             nombre_cliente: str | None, fecha: date, hora_txt: str):
        result = self.booking_service.create_reservation(
            peluqueria=peluqueria,
            servicio_id=servicio_id,
            telefono_cliente=telefono_cliente,
            nombre_cliente=nombre_cliente,
            fecha=fecha,
            hora_txt=hora_txt,
            origen="whatsapp",
        )
        return ReservationResult(
            ok=result.ok,
            reserva=result.reserva,
            error=result.error,
            available_slots=result.available_slots,
        )
