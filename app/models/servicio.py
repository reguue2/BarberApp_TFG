# Modelo de servicios que se pueden reservar.

from datetime import datetime

from app.extensions import db


class Servicio(db.Model):
    __tablename__ = "servicios"
    __table_args__ = (
        db.UniqueConstraint("peluqueria_id", "nombre", name="uq_servicio_peluqueria_nombre"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    peluqueria_id = db.Column(db.Integer, db.ForeignKey("peluquerias.id"), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(255))
    precio = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    duracion_min = db.Column(db.Integer, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    peluqueria = db.relationship("Peluqueria", back_populates="servicios")
    reservas = db.relationship("Reserva", back_populates="servicio")
