# Consultas de profesionales.

from app.extensions import db
from app.models import Profesional


class ProfesionalRepository:
    @staticmethod
    def count_active_by_peluqueria(peluqueria_id: int) -> int:
        return Profesional.query.filter_by(peluqueria_id=peluqueria_id, activo=True).count()

    # ---- Panel ----

    @staticmethod
    def list_by_peluqueria(peluqueria_id: int):
        return (
            Profesional.query.filter_by(peluqueria_id=peluqueria_id)
            .order_by(Profesional.activo.desc(), Profesional.nombre.asc())
            .all()
        )

    @staticmethod
    def get_by_id(peluqueria_id: int, profesional_id: int):
        return Profesional.query.filter_by(id=profesional_id, peluqueria_id=peluqueria_id).first()

    @staticmethod
    def create(peluqueria_id: int, nombre: str):
        profesional = Profesional(peluqueria_id=peluqueria_id, nombre=nombre.strip(), activo=True)
        db.session.add(profesional)
        return profesional
