# Consultas de peluquerías.

from app.models import Peluqueria


class PeluqueriaRepository:
    @staticmethod
    def get_by_wa_phone_number_id(phone_number_id: str):
        if not phone_number_id:
            return None
        return Peluqueria.query.filter_by(wa_phone_number_id=phone_number_id).first()

    @staticmethod
    def get_by_id(peluqueria_id: int):
        return Peluqueria.query.get(peluqueria_id)
