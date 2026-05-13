# Modelo de días cerrados de una peluquería.

from datetime import datetime

from app.extensions import db


class DiaCerrado(db.Model):
    __tablename__ = "dias_cerrados"
    __table_args__ = (
        db.UniqueConstraint("peluqueria_id", "fecha", name="uq_dia_cerrado_peluqueria_fecha"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    peluqueria_id = db.Column(db.Integer, db.ForeignKey("peluquerias.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    motivo = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    peluqueria = db.relationship("Peluqueria", back_populates="dias_cerrados")
