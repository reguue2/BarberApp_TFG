# Modelo de profesionales activos de la peluquería.

from datetime import datetime

from app.extensions import db


class Profesional(db.Model):
    __tablename__ = "profesionales"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    peluqueria_id = db.Column(db.Integer, db.ForeignKey("peluquerias.id"), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    peluqueria = db.relationship("Peluqueria", back_populates="profesionales")
