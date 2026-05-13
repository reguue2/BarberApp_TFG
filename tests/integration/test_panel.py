"""Pruebas de integración del panel web.

No se prueba cada detalle visual. Se prueban los casos que explican el proyecto:
login, multi-tenant, reservas, disponibilidad y operaciones básicas del panel.
"""

from datetime import time

from app.extensions import db
from app.models import Cliente, Profesional, Reserva, Servicio
from app.services.booking_service import BookingService
from app.services.reservation_service import ReservationService
from tests.conftest import next_open_day


def test_login_correcto_entra_al_panel(client, demo_data):
    response = client.post(
        "/login",
        data={"email": "admin1@test.com", "password": "secret123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/panel" in response.headers["Location"]


def test_dashboard_sin_login_redirige_a_login(client, demo_data):
    response = client.get("/panel/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_un_admin_no_ve_reservas_de_otra_peluqueria(logged_client_other, demo_data, make_reserva):
    make_reserva(
        demo_data["pelu"],
        demo_data["corte"],
        telefono="699999999",
        nombre="Cliente Privado",
        fecha=next_open_day(),
    )

    response = logged_client_other.get(f"/panel/reservas?fecha={next_open_day().isoformat()}")

    assert response.status_code == 200
    assert "Cliente Privado" not in response.get_data(as_text=True)


def test_crea_reserva_desde_panel(logged_client, demo_data):
    response = logged_client.post("/panel/reservas/nueva", data={
        "servicio_id": demo_data["corte"].id,
        "fecha": next_open_day().isoformat(),
        "hora": "09:00",
        "nombre": "Cliente Panel",
        "telefono": "+34 611 222 333",
    })

    reserva = Reserva.query.one()
    assert response.status_code == 302
    assert reserva.origen == "panel"
    assert reserva.cliente.nombre == "Cliente Panel"
    assert reserva.cliente.telefono == "611222333"


def test_no_crea_reserva_en_dia_cerrado(app, demo_data):
    result = BookingService().create_reservation(
        peluqueria=demo_data["pelu"],
        servicio_id=demo_data["corte"].id,
        telefono_cliente="611111222",
        nombre_cliente="Cliente Cerrado",
        fecha=demo_data["closed"],
        hora_txt="09:00",
        origen="panel",
    )

    assert result.ok is False
    assert result.error == "slot_not_available"


def test_no_crea_reserva_si_la_hora_esta_llena(app, demo_data, make_reserva):
    fecha = next_open_day()
    make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000001", fecha=fecha, hora=time(9, 0))
    make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000002", fecha=fecha, hora=time(9, 0))

    result = BookingService().create_reservation(
        peluqueria=demo_data["pelu"],
        servicio_id=demo_data["corte"].id,
        telefono_cliente="600000003",
        nombre_cliente="Tercer Cliente",
        fecha=fecha,
        hora_txt="09:00",
        origen="panel",
    )

    assert result.ok is False
    assert result.error == "slot_not_available"


def test_crea_servicio_y_profesional_desde_panel(logged_client, demo_data):
    response_servicio = logged_client.post("/panel/servicios/nuevo", data={
        "nombre": "Manicura",
        "descripcion": "Manicura completa",
        "precio": "15.50",
        "duracion_min": "45",
    })
    response_profesional = logged_client.post("/panel/profesionales/nuevo", data={"nombre": "Pedro"})

    assert response_servicio.status_code == 302
    assert response_profesional.status_code == 302
    assert Servicio.query.filter_by(peluqueria_id=demo_data["pelu"].id, nombre="Manicura").first() is not None
    assert Profesional.query.filter_by(peluqueria_id=demo_data["pelu"].id, nombre="Pedro").first() is not None


def test_no_elimina_profesional_si_hay_reservas_futuras(logged_client, demo_data, make_reserva):
    profesional = Profesional.query.filter_by(peluqueria_id=demo_data["pelu"].id, nombre="Laura").first()
    make_reserva(demo_data["pelu"], demo_data["corte"], telefono="600000333", fecha=next_open_day())

    response = logged_client.post(f"/panel/profesionales/{profesional.id}/eliminar", follow_redirects=True)

    assert response.status_code == 200
    assert db.session.get(Profesional, profesional.id) is not None
    assert "No se puede eliminar este profesional" in response.get_data(as_text=True)


def test_no_elimina_cliente_si_tiene_reservas_futuras(logged_client, demo_data, make_reserva):
    reserva = make_reserva(
        demo_data["pelu"],
        demo_data["corte"],
        telefono="611222333",
        nombre="Cliente Con Reserva",
        fecha=next_open_day(),
    )

    response = logged_client.post(f"/panel/clientes/{reserva.cliente_id}/eliminar", follow_redirects=True)

    assert response.status_code == 200
    assert db.session.get(Cliente, reserva.cliente_id) is not None
    assert "No se puede eliminar este cliente" in response.get_data(as_text=True)


def test_reserva_de_whatsapp_aparece_en_el_panel(logged_client, demo_data):
    fecha = next_open_day()
    result = ReservationService().create_from_whatsapp(
        peluqueria=demo_data["pelu"],
        servicio_id=demo_data["corte"].id,
        telefono_cliente="600111222",
        nombre_cliente="Cliente WhatsApp",
        fecha=fecha,
        hora_txt="09:00",
    )

    response = logged_client.get(f"/panel/reservas?fecha={fecha.isoformat()}")
    html = response.get_data(as_text=True)

    assert result.ok is True
    assert response.status_code == 200
    assert "Cliente WhatsApp" in html
    assert "600111222" in html


def test_agenda_no_muestra_huecos_disponibles_si_el_dia_esta_cerrado(logged_client, demo_data):
    response = logged_client.get(f"/panel/reservas?fecha={demo_data['closed'].isoformat()}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "La peluquería está cerrada este día" in html
    assert "Disponible" not in html
