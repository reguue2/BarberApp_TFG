# Consultas de servicios de una peluquería.

from app.extensions import db
from app.models import Servicio


class ServicioRepository:
    @staticmethod
    def list_active_by_peluqueria(peluqueria_id: int):
        return (
            Servicio.query.filter_by(peluqueria_id=peluqueria_id, activo=True)
            .order_by(Servicio.nombre.asc())
            .all()
        )

    @staticmethod
    def get_active_by_id(peluqueria_id: int, servicio_id: int):
        return Servicio.query.filter_by(
            id=servicio_id,
            peluqueria_id=peluqueria_id,
            activo=True,
        ).first()

    # ---- Panel ----

    @staticmethod
    def list_all_by_peluqueria(peluqueria_id: int, search: str | None = None):
        query = Servicio.query.filter_by(peluqueria_id=peluqueria_id)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(Servicio.nombre.ilike(term))
        return query.order_by(Servicio.activo.desc(), Servicio.nombre.asc()).all()

    @staticmethod
    def get_by_id(peluqueria_id: int, servicio_id: int):
        return Servicio.query.filter_by(id=servicio_id, peluqueria_id=peluqueria_id).first()

    @staticmethod
    def count_active(peluqueria_id: int) -> int:
        return Servicio.query.filter_by(peluqueria_id=peluqueria_id, activo=True).count()

    @staticmethod
    def create(peluqueria_id: int, nombre: str, descripcion: str | None, precio, duracion_min: int, activo: bool = True):
        servicio = Servicio(
            peluqueria_id=peluqueria_id,
            nombre=nombre.strip(),
            descripcion=(descripcion or "").strip() or None,
            precio=precio,
            duracion_min=duracion_min,
            activo=activo,
        )
        db.session.add(servicio)
        return servicio
