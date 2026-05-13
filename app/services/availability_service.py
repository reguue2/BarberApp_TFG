# Calcula huecos disponibles según horarios, reservas y profesionales.

from datetime import date, datetime, timedelta

from flask import current_app

from app.bot.time_utils import from_min, overlap, to_min
from app.repositories.horario_repository import HorarioRepository
from app.repositories.profesional_repository import ProfesionalRepository
from app.repositories.reserva_repository import ReservaRepository
from app.utils.datetime_utils import now_local


class AvailabilityService:
    def __init__(self, now_func=None):
        self.now_func = now_func

    def now(self):
        return self.now_func() if self.now_func else now_local()

    def get_available_slots_for_service(self, peluqueria, servicio, fecha: date) -> list[str]:
        now = self.now()
        if fecha < now.date():
            return []

        max_dias = current_app.config.get("DEFAULT_MAX_DIAS_RESERVA", 60)
        if fecha > now.date() + timedelta(days=max_dias):
            return []

        if HorarioRepository.get_closed_day(peluqueria.id, fecha):
            return []

        capacidad = ProfesionalRepository.count_active_by_peluqueria(peluqueria.id)
        if capacidad < 1:
            return []

        dia_semana = fecha.weekday() + 1
        tramos = HorarioRepository.list_active_for_weekday(peluqueria.id, dia_semana)
        if not tramos:
            return []

        reservas = ReservaRepository.list_confirmed_by_day(peluqueria.id, fecha)
        step = int(peluqueria.rango_reservas_min or 30)
        duracion = int(servicio.duracion_min)
        min_avance = current_app.config.get("DEFAULT_MIN_ADVANCE_MIN", 30)

        slots = []
        for tramo in tramos:
            cur = to_min(tramo.hora_inicio)
            end = to_min(tramo.hora_fin)
            while cur + duracion <= end:
                slot_hora = from_min(cur)
                if self._is_not_too_soon(fecha, slot_hora, now, min_avance):
                    ocupadas = self._count_overlaps(reservas, slot_hora, duracion)
                    if ocupadas < capacidad:
                        slots.append(slot_hora)
                cur += step
        return slots

    def _is_not_too_soon(self, fecha: date, hora_txt: str, now: datetime, min_avance: int) -> bool:
        if fecha != now.date():
            return True
        start_min = to_min(hora_txt)
        min_start = now.hour * 60 + now.minute + min_avance
        return start_min >= min_start

    def _count_overlaps(self, reservas, hora_txt: str, duracion: int) -> int:
        total = 0
        for reserva in reservas:
            if reserva.servicio and overlap(hora_txt, duracion, reserva.hora, reserva.servicio.duracion_min):
                total += 1
        return total
