# Consultas para los usuarios administradores del panel.

from app.models import UsuarioAdmin


class UsuarioAdminRepository:
    @staticmethod
    def get_by_email(email: str):
        if not email:
            return None
        return UsuarioAdmin.query.filter_by(email=email.strip().lower()).first()

    @staticmethod
    def get_by_id(usuario_id: int):
        return UsuarioAdmin.query.get(usuario_id)
