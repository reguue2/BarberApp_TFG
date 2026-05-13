"""Datos comunes para los tests de PeluGestor."""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    Cliente,
    DiaCerrado,
    HorarioApertura,
    Peluqueria,
    Profesional,
    Reserva,
    Servicio,
    UsuarioAdmin,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    APP_TZ = "Europe/Madrid"
    DEFAULT_MIN_ADVANCE_MIN = 0
    DEFAULT_MAX_DIAS_RESERVA = 60
    WABA_TOKEN = ""
    WABA_VERIFY_TOKEN = "test-token"
    WABA_APP_SECRET = ""
    GRAPH_API_VERSION = "v23.0"
    OPENAI_API_KEY = ""
    OPENAI_MODEL = "gpt-4o-mini"
    AUTO_INIT_DB = False


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def demo_data(app):
    """Crea dos peluquerías para poder probar el aislamiento multi-tenant."""
    pelu = Peluqueria(
        nombre="Pelu Test",
        direccion="Calle Test 1",
        telefono_peluqueria="948123123",
        info="Peluquería de prueba",
        rango_reservas_min=30,
        wa_phone_number_id="phone-1",
        wa_business_id="business-1",
    )
    otra_pelu = Peluqueria(
        nombre="Otra Pelu",
        direccion="Calle Dos 2",
        rango_reservas_min=30,
        wa_phone_number_id="phone-2",
    )
    db.session.add_all([pelu, otra_pelu])
    db.session.flush()

    db.session.add_all([
        UsuarioAdmin(
            peluqueria_id=pelu.id,
            nombre="Admin 1",
            email="admin1@test.com",
            password_hash=generate_password_hash("secret123"),
            activo=True,
        ),
        UsuarioAdmin(
            peluqueria_id=otra_pelu.id,
            nombre="Admin 2",
            email="admin2@test.com",
            password_hash=generate_password_hash("secret123"),
            activo=True,
        ),
    ])

    corte = Servicio(
        peluqueria_id=pelu.id,
        nombre="Corte",
        descripcion="Corte básico",
        precio=Decimal("12.00"),
        duracion_min=30,
        activo=True,
    )
    tinte = Servicio(
        peluqueria_id=pelu.id,
        nombre="Tinte",
        descripcion="Color completo",
        precio=Decimal("35.00"),
        duracion_min=90,
        activo=True,
    )
    barba = Servicio(
        peluqueria_id=otra_pelu.id,
        nombre="Barba",
        descripcion="Arreglo",
        precio=Decimal("8.00"),
        duracion_min=30,
        activo=True,
    )
    db.session.add_all([corte, tinte, barba])
    db.session.flush()

    db.session.add_all([
        Profesional(peluqueria_id=pelu.id, nombre="Laura", activo=True),
        Profesional(peluqueria_id=pelu.id, nombre="Marta", activo=True),
        Profesional(peluqueria_id=otra_pelu.id, nombre="Iván", activo=True),
    ])

    # Lunes a viernes, de 09:00 a 12:00.
    for dia in range(1, 6):
        db.session.add(HorarioApertura(
            peluqueria_id=pelu.id,
            dia_semana=dia,
            hora_inicio=time(9, 0),
            hora_fin=time(12, 0),
            activo=True,
        ))
        db.session.add(HorarioApertura(
            peluqueria_id=otra_pelu.id,
            dia_semana=dia,
            hora_inicio=time(10, 0),
            hora_fin=time(12, 0),
            activo=True,
        ))

    closed = next_open_day() + timedelta(days=7)
    db.session.add(DiaCerrado(peluqueria_id=pelu.id, fecha=closed, motivo="cerrado"))
    db.session.commit()

    return {
        "pelu": pelu,
        "otra_pelu": otra_pelu,
        "corte": corte,
        "tinte": tinte,
        "barba": barba,
        "closed": closed,
    }


@pytest.fixture
def make_reserva(app):
    def _make(pelu, servicio, telefono="600000000", nombre="Mario", fecha=None, hora=time(9, 0)):
        fecha = fecha or next_open_day()
        cliente = Cliente.query.filter_by(peluqueria_id=pelu.id, telefono=telefono).first()
        if not cliente:
            cliente = Cliente(peluqueria_id=pelu.id, telefono=telefono, nombre=nombre)
            db.session.add(cliente)
            db.session.flush()

        reserva = Reserva(
            peluqueria_id=pelu.id,
            cliente_id=cliente.id,
            servicio_id=servicio.id,
            fecha=fecha,
            hora=hora,
            estado="confirmada",
            origen="whatsapp",
        )
        db.session.add(reserva)
        db.session.commit()
        return reserva

    return _make


@pytest.fixture
def logged_client(client, demo_data):
    client.post("/login", data={"email": "admin1@test.com", "password": "secret123"})
    return client


@pytest.fixture
def logged_client_other(app, demo_data):
    other = app.test_client()
    other.post("/login", data={"email": "admin2@test.com", "password": "secret123"})
    return other


def next_open_day():
    """Devuelve el siguiente día laborable para que los tests no dependan del calendario."""
    day = date.today() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day
