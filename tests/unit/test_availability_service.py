"""Pruebas unitarias de disponibilidad.

Aquí se prueba la regla más importante: cuándo existe hueco para reservar.
"""

from datetime import time

from app.extensions import db
from app.models import Profesional
from app.services.availability_service import AvailabilityService
from tests.conftest import next_open_day


def test_devuelve_horas_libres_dentro_del_horario(app, demo_data):
    slots = AvailabilityService().get_available_slots_for_service(
        demo_data["pelu"],
        demo_data["corte"],
        next_open_day(),
    )

    assert "09:00" in slots
    assert "11:30" in slots
    assert "12:00" not in slots


def test_no_devuelve_horas_si_el_dia_esta_cerrado(app, demo_data):
    slots = AvailabilityService().get_available_slots_for_service(
        demo_data["pelu"],
        demo_data["corte"],
        demo_data["closed"],
    )

    assert slots == []


def test_no_permite_superar_la_capacidad_de_profesionales(app, demo_data, make_reserva):
    fecha = next_open_day()

    # Hay dos profesionales activos, así que entran dos reservas a la misma hora.
    make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000001", fecha=fecha, hora=time(9, 0))
    make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000002", fecha=fecha, hora=time(9, 0))

    slots = AvailabilityService().get_available_slots_for_service(demo_data["pelu"], demo_data["corte"], fecha)

    assert "09:00" not in slots


def test_sin_profesionales_activos_no_hay_horas(app, demo_data):
    Profesional.query.filter_by(peluqueria_id=demo_data["pelu"].id).update({"activo": False})
    db.session.commit()

    slots = AvailabilityService().get_available_slots_for_service(
        demo_data["pelu"],
        demo_data["corte"],
        next_open_day(),
    )

    assert slots == []
