# Modelo principal de cada peluquería.

from datetime import datetime

from app.extensions import db


class Peluqueria(db.Model):
    __tablename__ = "peluquerias"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(150))
    telefono_peluqueria = db.Column(db.String(20))
    info = db.Column(db.String(500))
    rango_reservas_min = db.Column(db.Integer, nullable=False, default=30)
    wa_phone_number_id = db.Column(db.String(64), unique=True)
    wa_business_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuarios_admin = db.relationship("UsuarioAdmin", back_populates="peluqueria", uselist=False)
    clientes = db.relationship("Cliente", back_populates="peluqueria")
    servicios = db.relationship("Servicio", back_populates="peluqueria")
    profesionales = db.relationship("Profesional", back_populates="peluqueria")
    horarios_apertura = db.relationship("HorarioApertura", back_populates="peluqueria")
    dias_cerrados = db.relationship("DiaCerrado", back_populates="peluqueria")
    reservas = db.relationship("Reserva", back_populates="peluqueria")
