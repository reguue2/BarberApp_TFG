"""Pruebas unitarias de creación y cancelación de reservas."""

from datetime import time

from app.models import Cliente, Reserva
from app.services.cancellation_service import CancellationService
from app.services.reservation_service import ReservationService
from tests.conftest import next_open_day


def test_crea_reserva_y_cliente_normalizando_telefono(app, demo_data):
    result = ReservationService().create_from_whatsapp(
        peluqueria=demo_data["pelu"],
        servicio_id=demo_data["corte"].id,
        telefono_cliente="+34 600 000 000",
        nombre_cliente="Mario",
        fecha=next_open_day(),
        hora_txt="09:00",
    )

    assert result.ok is True
    assert Reserva.query.count() == 1
    assert Cliente.query.filter_by(telefono="600000000").count() == 1


def test_no_crea_reserva_si_la_hora_esta_llena(app, demo_data, make_reserva):
    fecha = next_open_day()
    make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000001", fecha=fecha, hora=time(9, 0))
    make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000002", fecha=fecha, hora=time(9, 0))

    result = ReservationService().create_from_whatsapp(
        demo_data["pelu"], demo_data["corte"].id, "600000003", "Ana", fecha, "09:00"
    )

    assert result.ok is False
    assert result.error == "slot_not_available"


def test_cancela_reserva_del_mismo_cliente(app, demo_data, make_reserva):
    reserva = make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000000")

    result = CancellationService().cancel_from_whatsapp(demo_data["pelu"].id, "600000000", reserva.id)

    assert result.ok is True
    assert result.reserva.estado == "cancelada"


def test_no_cancela_reserva_de_otro_cliente(app, demo_data, make_reserva):
    reserva = make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000111")

    result = CancellationService().cancel_from_whatsapp(demo_data["pelu"].id, "600000222", reserva.id)

    assert result.ok is False
    assert reserva.estado == "confirmada"
