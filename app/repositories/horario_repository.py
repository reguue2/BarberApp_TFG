# Consultas de horarios y días cerrados.

from datetime import date

from app.extensions import db
from app.models import DiaCerrado, HorarioApertura


class HorarioRepository:
    @staticmethod
    def list_active_for_weekday(peluqueria_id: int, dia_semana: int):
        return (
            HorarioApertura.query.filter_by(
                peluqueria_id=peluqueria_id,
                dia_semana=dia_semana,
                activo=True,
            )
            .order_by(HorarioApertura.hora_inicio.asc())
            .all()
        )

    @staticmethod
    def get_closed_day(peluqueria_id: int, fecha):
        return DiaCerrado.query.filter_by(peluqueria_id=peluqueria_id, fecha=fecha).first()

    @staticmethod
    def list_next_closed_days(peluqueria_id: int, desde, limite=5):
        return (
            DiaCerrado.query.filter(
                DiaCerrado.peluqueria_id == peluqueria_id,
                DiaCerrado.fecha >= desde,
            )
            .order_by(DiaCerrado.fecha.asc())
            .limit(limite)
            .all()
        )

    # ---- Panel ----

    @staticmethod
    def list_all_horarios(peluqueria_id: int):
        return (
            HorarioApertura.query.filter_by(peluqueria_id=peluqueria_id)
            .order_by(HorarioApertura.dia_semana.asc(), HorarioApertura.hora_inicio.asc())
            .all()
        )

    @staticmethod
    def list_all_dias_cerrados(peluqueria_id: int):
        return (
            DiaCerrado.query.filter_by(peluqueria_id=peluqueria_id)
            .order_by(DiaCerrado.fecha.asc())
            .all()
        )

    @staticmethod
    def get_dia_cerrado_by_id(peluqueria_id: int, dia_id: int):
        return DiaCerrado.query.filter_by(id=dia_id, peluqueria_id=peluqueria_id).first()

    @staticmethod
    def replace_horarios(peluqueria_id: int, tramos: list[dict]):
        """Reemplaza todos los horarios de la peluquería por la nueva lista.

        tramos: lista de dicts con dia_semana, hora_inicio, hora_fin, activo.
        """
        HorarioApertura.query.filter_by(peluqueria_id=peluqueria_id).delete()
        for tramo in tramos:
            db.session.add(HorarioApertura(
                peluqueria_id=peluqueria_id,
                dia_semana=tramo["dia_semana"],
                hora_inicio=tramo["hora_inicio"],
                hora_fin=tramo["hora_fin"],
                activo=tramo.get("activo", True),
            ))

    @staticmethod
    def add_dia_cerrado(peluqueria_id: int, fecha: date, motivo: str | None):
        dia = DiaCerrado(peluqueria_id=peluqueria_id, fecha=fecha, motivo=(motivo or "").strip() or None)
        db.session.add(dia)
        return dia
