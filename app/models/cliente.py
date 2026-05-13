# Modelo de clientes de cada peluquería.

from datetime import datetime

from app.extensions import db


class Cliente(db.Model):
    __tablename__ = "clientes"
    __table_args__ = (
        db.UniqueConstraint("peluqueria_id", "telefono", name="uq_cliente_peluqueria_telefono"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    peluqueria_id = db.Column(db.Integer, db.ForeignKey("peluquerias.id"), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    peluqueria = db.relationship("Peluqueria", back_populates="clientes")
    reservas = db.relationship("Reserva", back_populates="cliente")
