# Consultas y cambios de reservas.

from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Reserva, Servicio


class ReservaRepository:
    @staticmethod
    def list_confirmed_by_day(peluqueria_id: int, fecha: date):
        return Reserva.query.filter_by(
            peluqueria_id=peluqueria_id,
            fecha=fecha,
            estado="confirmada",
        ).all()

    @staticmethod
    def list_future_confirmed_by_client(peluqueria_id: int, cliente_id: int, ahora: datetime):
        hoy = ahora.date()
        hora_actual = ahora.time()
        return (
            Reserva.query.filter(
                Reserva.peluqueria_id == peluqueria_id,
                Reserva.cliente_id == cliente_id,
                Reserva.estado == "confirmada",
                (
                    (Reserva.fecha > hoy)
                    | ((Reserva.fecha == hoy) & (Reserva.hora >= hora_actual))
                ),
            )
            .order_by(Reserva.fecha.asc(), Reserva.hora.asc())
            .all()
        )


    @staticmethod
    def count_future_confirmed_by_day(peluqueria_id: int, fecha: date, ahora: datetime) -> int:
        query = Reserva.query.filter(
            Reserva.peluqueria_id == peluqueria_id,
            Reserva.fecha == fecha,
            Reserva.estado == "confirmada",
        )
        if fecha == ahora.date():
            query = query.filter(Reserva.hora >= ahora.time())
        elif fecha < ahora.date():
            return 0
        return query.count()

    @staticmethod
    def count_future_confirmed_by_client(peluqueria_id: int, cliente_id: int, ahora: datetime) -> int:
        hoy = ahora.date()
        hora_actual = ahora.time()
        return Reserva.query.filter(
            Reserva.peluqueria_id == peluqueria_id,
            Reserva.cliente_id == cliente_id,
            Reserva.estado == "confirmada",
            (
                (Reserva.fecha > hoy)
                | ((Reserva.fecha == hoy) & (Reserva.hora >= hora_actual))
            ),
        ).count()

    @staticmethod
    def count_future_confirmed(peluqueria_id: int, ahora: datetime) -> int:
        hoy = ahora.date()
        hora_actual = ahora.time()
        return Reserva.query.filter(
            Reserva.peluqueria_id == peluqueria_id,
            Reserva.estado == "confirmada",
            (
                (Reserva.fecha > hoy)
                | ((Reserva.fecha == hoy) & (Reserva.hora >= hora_actual))
            ),
        ).count()

    @staticmethod
    def list_future_confirmed_with_relations(peluqueria_id: int, ahora: datetime):
        hoy = ahora.date()
        hora_actual = ahora.time()
        return (
            Reserva.query.options(joinedload(Reserva.servicio))
            .filter(
                Reserva.peluqueria_id == peluqueria_id,
                Reserva.estado == "confirmada",
                (
                    (Reserva.fecha > hoy)
                    | ((Reserva.fecha == hoy) & (Reserva.hora >= hora_actual))
                ),
            )
            .order_by(Reserva.fecha.asc(), Reserva.hora.asc())
            .all()
        )

    @staticmethod
    def get_by_id(peluqueria_id: int, reserva_id: int):
        return Reserva.query.filter_by(id=reserva_id, peluqueria_id=peluqueria_id).first()

    @staticmethod
    def create(peluqueria_id: int, cliente_id: int, servicio_id: int, fecha: date, hora: time, origen: str):
        reserva = Reserva(
            peluqueria_id=peluqueria_id,
            cliente_id=cliente_id,
            servicio_id=servicio_id,
            fecha=fecha,
            hora=hora,
            estado="confirmada",
            origen=origen,
        )
        db.session.add(reserva)
        return reserva

    @staticmethod
    def cancel(reserva: Reserva):
        reserva.estado = "cancelada"
        return reserva

    # ---- Panel ----

    @staticmethod
    def list_by_day_with_relations(peluqueria_id: int, fecha: date, only_confirmed: bool = False):
        """Devuelve reservas del día con cliente y servicio cargados."""
        query = (
            Reserva.query
            .options(joinedload(Reserva.cliente), joinedload(Reserva.servicio))
            .filter(Reserva.peluqueria_id == peluqueria_id, Reserva.fecha == fecha)
        )
        if only_confirmed:
            query = query.filter(Reserva.estado == "confirmada")
        return query.order_by(Reserva.hora.asc()).all()

    @staticmethod
    def count_confirmed_today(peluqueria_id: int, hoy: date) -> int:
        return Reserva.query.filter_by(
            peluqueria_id=peluqueria_id,
            fecha=hoy,
            estado="confirmada",
        ).count()

    @staticmethod
    def count_confirmed_upcoming(peluqueria_id: int, desde: date) -> int:
        return Reserva.query.filter(
            Reserva.peluqueria_id == peluqueria_id,
            Reserva.estado == "confirmada",
            Reserva.fecha >= desde,
        ).count()

    @staticmethod
    def list_by_client(peluqueria_id: int, cliente_id: int, limite: int = 20):
        return (
            Reserva.query.options(joinedload(Reserva.servicio))
            .filter_by(peluqueria_id=peluqueria_id, cliente_id=cliente_id)
            .order_by(Reserva.fecha.desc(), Reserva.hora.desc())
            .limit(limite)
            .all()
        )

    @staticmethod
    def list_with_reservas_in_month(peluqueria_id: int, anio: int, mes: int):
        """Conjunto de fechas (date) del mes con al menos una reserva confirmada."""
        primer_dia = date(anio, mes, 1)
        if mes == 12:
            sig = date(anio + 1, 1, 1)
        else:
            sig = date(anio, mes + 1, 1)
        ultimo_dia = sig - timedelta(days=1)

        rows = (
            db.session.query(Reserva.fecha)
            .filter(
                Reserva.peluqueria_id == peluqueria_id,
                Reserva.estado == "confirmada",
                Reserva.fecha >= primer_dia,
                Reserva.fecha <= ultimo_dia,
            )
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    # ---- Métricas (dashboard) ----

    @staticmethod
    def count_confirmed_by_origen(peluqueria_id: int):
        """Devuelve [(origen, count), ...] de reservas confirmadas agrupadas por canal."""
        return (
            db.session.query(Reserva.origen, func.count(Reserva.id))
            .filter(
                Reserva.peluqueria_id == peluqueria_id,
                Reserva.estado == "confirmada",
            )
            .group_by(Reserva.origen)
            .all()
        )

    @staticmethod
    def top_servicios_confirmados(peluqueria_id: int, limite: int = 5):
        """Top N servicios por número de reservas confirmadas.

        Devuelve [(servicio_id, nombre, count), ...] ordenado desc.
        """
        return (
            db.session.query(Servicio.id, Servicio.nombre, func.count(Reserva.id))
            .join(Reserva, Reserva.servicio_id == Servicio.id)
            .filter(
                Servicio.peluqueria_id == peluqueria_id,
                Reserva.estado == "confirmada",
            )
            .group_by(Servicio.id, Servicio.nombre)
            .order_by(func.count(Reserva.id).desc(), Servicio.nombre.asc())
            .limit(limite)
            .all()
        )
