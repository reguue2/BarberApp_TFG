# Modelo de reservas creadas por WhatsApp o panel.

from datetime import datetime

from app.extensions import db


class Reserva(db.Model):
    __tablename__ = "reservas"
    __table_args__ = (
        db.Index("ix_reservas_peluqueria_fecha", "peluqueria_id", "fecha"),
        db.Index("ix_reservas_peluqueria_fecha_hora", "peluqueria_id", "fecha", "hora"),
        db.Index("ix_reservas_peluqueria_fecha_estado", "peluqueria_id", "fecha", "estado"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    peluqueria_id = db.Column(db.Integer, db.ForeignKey("peluquerias.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    servicio_id = db.Column(db.Integer, db.ForeignKey("servicios.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="confirmada")
    origen = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    peluqueria = db.relationship("Peluqueria", back_populates="reservas")
    cliente = db.relationship("Cliente", back_populates="reservas")
    servicio = db.relationship("Servicio", back_populates="reservas")
