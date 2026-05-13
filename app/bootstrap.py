# Crea la base de datos y mete datos de ejemplo si está vacía.

import logging
import time as sleep_time
from datetime import time, timedelta
from decimal import Decimal

from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import DiaCerrado, HorarioApertura, Peluqueria, Profesional, Servicio, UsuarioAdmin
from app.utils.datetime_utils import today_local


def init_database(app):
    if not app.config.get("AUTO_INIT_DB", True):
        return

    # MySQL tarda unos segundos en arrancar cuando se levanta Docker.
    for attempt in range(1, 31):
        try:
            with app.app_context():
                db.create_all()
                _seed_if_empty()
            logging.info("Base de datos preparada.")
            return
        except OperationalError:
            if attempt == 30:
                raise
            sleep_time.sleep(2)


def _seed_if_empty():
    if Peluqueria.query.first():
        return

    pelu1 = Peluqueria(
        nombre="Peluquería Centro",
        direccion="Calle Mayor 12",
        telefono_peluqueria="948000111",
        info="Peluquería unisex especializada en cortes, barba y color.",
        rango_reservas_min=30,
        wa_phone_number_id="111111111111111",
        wa_business_id="222222222222222",
    )
    pelu2 = Peluqueria(
        nombre="Barbería Norte",
        direccion="Avenida Norte 8",
        telefono_peluqueria="948000222",
        info="Barbería enfocada en corte masculino y arreglo de barba.",
        rango_reservas_min=30,
        wa_phone_number_id="333333333333333",
        wa_business_id="444444444444444",
    )

    db.session.add_all([pelu1, pelu2])
    db.session.flush()

    db.session.add_all([
        UsuarioAdmin(peluqueria=pelu1, nombre="Admin Centro", email="centro@example.com",
                     password_hash=generate_password_hash("admin123")),
        UsuarioAdmin(peluqueria=pelu2, nombre="Admin Norte", email="norte@example.com",
                     password_hash=generate_password_hash("admin123")),
        Profesional(peluqueria=pelu1, nombre="Laura", activo=True),
        Profesional(peluqueria=pelu1, nombre="Marta", activo=True),
        Profesional(peluqueria=pelu2, nombre="Iván", activo=True),
        Servicio(peluqueria=pelu1, nombre="Corte de pelo", descripcion="Corte y peinado básico",
                 precio=Decimal("12.00"), duracion_min=30, activo=True),
        Servicio(peluqueria=pelu1, nombre="Barba", descripcion="Arreglo de barba",
                 precio=Decimal("8.00"), duracion_min=20, activo=True),
        Servicio(peluqueria=pelu1, nombre="Tinte", descripcion="Coloración completa",
                 precio=Decimal("35.00"), duracion_min=90, activo=True),
        Servicio(peluqueria=pelu2, nombre="Corte masculino", descripcion="Corte clásico o degradado",
                 precio=Decimal("14.00"), duracion_min=30, activo=True),
        Servicio(peluqueria=pelu2, nombre="Barba premium", descripcion="Arreglo de barba con acabado",
                 precio=Decimal("10.00"), duracion_min=30, activo=True),
    ])

    for dia in range(1, 6):
        _add_horario(pelu1, dia, "09:00", "14:00")
        _add_horario(pelu1, dia, "16:00", "20:00")
        _add_horario(pelu2, dia, "10:00", "14:00")
        _add_horario(pelu2, dia, "16:00", "19:00")
    _add_horario(pelu1, 6, "09:00", "14:00")

    db.session.add(DiaCerrado(peluqueria=pelu1, fecha=today_local() + timedelta(days=10), motivo="Cierre de prueba"))
    db.session.commit()


def _add_horario(peluqueria, dia, inicio, fin):
    db.session.add(
        HorarioApertura(
            peluqueria=peluqueria,
            dia_semana=dia,
            hora_inicio=time.fromisoformat(inicio),
            hora_fin=time.fromisoformat(fin),
            activo=True,
        )
    )
