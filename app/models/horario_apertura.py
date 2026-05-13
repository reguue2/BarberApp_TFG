# Modelo de horarios de apertura por día.

from app.extensions import db


class HorarioApertura(db.Model):
    __tablename__ = "horarios_apertura"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    peluqueria_id = db.Column(db.Integer, db.ForeignKey("peluquerias.id"), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    peluqueria = db.relationship("Peluqueria", back_populates="horarios_apertura")
