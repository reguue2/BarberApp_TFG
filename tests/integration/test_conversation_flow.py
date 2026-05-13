"""Pruebas de integración del flujo conversacional del bot."""

from datetime import date, time

from app.bot.state_store import MemoryStateStore
from app.extensions import db
from app.models import Cliente, Reserva
from app.services.conversation_service import ConversationService
from tests.conftest import next_open_day


class FakeOpenAI:
    """Sustituye a OpenAI para que el test sea rápido y repetible."""

    def parse_date(self, text, today=None):
        return date.fromisoformat(text)

    def extract_name(self, text):
        return text.strip().title()


def make_service():
    return ConversationService(state_store=MemoryStateStore(), openai_client=FakeOpenAI())


def test_flujo_completo_de_reserva_por_whatsapp(app, demo_data):
    service = make_service()
    pelu = demo_data["pelu"]
    telefono = "600000000"
    fecha = next_open_day().isoformat()

    assert service.handle_message(pelu, telefono, "menu_reservar").kind == "service_list"
    assert "fecha" in service.handle_message(pelu, telefono, f"servicio:{demo_data['corte'].id}").text.lower()
    assert service.handle_message(pelu, telefono, fecha).kind == "hours_list"
    assert "nombre" in service.handle_message(pelu, telefono, "hora:09:00").text.lower()
    assert "Resumen" in service.handle_message(pelu, telefono, "Mario").text

    response = service.handle_message(pelu, telefono, "confirm_si")

    assert response.kind == "text_then_menu"
    assert "Reserva confirmada" in response.text
    assert Reserva.query.count() == 1
    assert Cliente.query.filter_by(telefono="600000000").first().nombre == "Mario"


def test_cliente_existente_no_vuelve_a_pedir_nombre(app, demo_data):
    pelu = demo_data["pelu"]
    db.session.add(Cliente(peluqueria_id=pelu.id, telefono="611111111", nombre="Laura"))
    db.session.commit()

    service = make_service()
    service.handle_message(pelu, "611111111", "menu_reservar")
    service.handle_message(pelu, "611111111", f"servicio:{demo_data['corte'].id}")
    service.handle_message(pelu, "611111111", next_open_day().isoformat())
    response = service.handle_message(pelu, "611111111", "hora:09:30")

    assert "Resumen" in response.text
    assert "Laura" in response.text


def test_si_escribe_texto_en_un_paso_de_lista_se_repite_la_lista(app, demo_data):
    service = make_service()
    service.handle_message(demo_data["pelu"], "600000000", "menu_reservar")

    response = service.handle_message(demo_data["pelu"], "600000000", "quiero corte")

    assert response.kind == "service_list"
    assert "elige un servicio" in response.text.lower()


def test_cancelacion_no_deja_cancelar_reservas_de_otro_cliente(app, demo_data, make_reserva):
    pelu = demo_data["pelu"]
    reserva_ajena = make_reserva(
        pelu,
        demo_data["corte"],
        telefono="600000111",
        nombre="Cliente Ajeno",
        fecha=next_open_day(),
    )
    make_reserva(
        pelu,
        demo_data["corte"],
        telefono="600000222",
        nombre="Cliente Propio",
        fecha=next_open_day(),
        hora=time(9, 30),
    )
    make_reserva(
        pelu,
        demo_data["tinte"],
        telefono="600000222",
        nombre="Cliente Propio",
        fecha=next_open_day(),
        hora=time(10, 30),
    )

    service = make_service()
    service.handle_message(pelu, "600000222", "menu_cancelar")
    response = service.handle_message(pelu, "600000222", f"reserva:{reserva_ajena.id}")

    assert response.kind == "reservations_list"
    assert "asociada a tu número" in response.text
    assert "Cliente Ajeno" not in response.text
