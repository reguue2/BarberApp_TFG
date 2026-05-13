# Modelo del usuario administrador del panel.
#
# Mantiene la restricción 1:1 con peluqueria (peluqueria_id unique).

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class UsuarioAdmin(db.Model, UserMixin):
    __tablename__ = "usuarios_admin"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    peluqueria_id = db.Column(db.Integer, db.ForeignKey("peluquerias.id"), nullable=False, unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    peluqueria = db.relationship("Peluqueria", back_populates="usuarios_admin")

    # -- Helpers de password --
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not raw_password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    # -- Flask-Login --
    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return bool(self.activo)
