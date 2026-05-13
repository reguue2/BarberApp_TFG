"""Pruebas de integración del webhook de WhatsApp."""

import app.routes.whatsapp_routes as whatsapp_routes


class FakeWhatsAppClient:
    """Guarda los envíos en memoria para no llamar a Meta en los tests."""

    def __init__(self):
        self.sent = []

    def send_text(self, phone_number_id, to, body):
        self.sent.append(("text", phone_number_id, to, body))
        return True

    def send_main_menu(self, phone_number_id, to, body):
        self.sent.append(("main_menu", phone_number_id, to, body))
        return True

    def send_services_list(self, phone_number_id, to, body, servicios, page=0):
        self.sent.append(("services", phone_number_id, to, body, page))
        return True

    def send_hours_list(self, phone_number_id, to, body, horas, page=0):
        self.sent.append(("hours", phone_number_id, to, body, page))
        return True

    def send_reservations_list(self, phone_number_id, to, body, reservas, page=0):
        self.sent.append(("reservations", phone_number_id, to, body, page))
        return True


def payload(phone_id, user, wamid, text):
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {"phone_number_id": phone_id},
                    "messages": [{"id": wamid, "from": user, "type": "text", "text": {"body": text}}],
                }
            }]
        }]
    }


def test_webhook_envia_respuesta_usando_la_peluqueria_correcta(client, demo_data, monkeypatch):
    fake = FakeWhatsAppClient()
    monkeypatch.setattr(whatsapp_routes, "whatsapp_client", fake)

    response = client.post("/webhook/whatsapp", json=payload("phone-1", "600000000", "wamid.1", "menu_reservar"))

    assert response.status_code == 200
    assert fake.sent[0][0] == "services"
    assert fake.sent[0][1] == "phone-1"


def test_webhook_ignora_numeros_no_configurados(client, demo_data, monkeypatch):
    fake = FakeWhatsAppClient()
    monkeypatch.setattr(whatsapp_routes, "whatsapp_client", fake)

    response = client.post("/webhook/whatsapp", json=payload("desconocido", "600000000", "wamid.2", "reservar"))

    assert response.status_code == 200
    assert fake.sent == []


def test_webhook_no_procesa_dos_veces_el_mismo_wamid(client, demo_data, monkeypatch):
    fake = FakeWhatsAppClient()
    monkeypatch.setattr(whatsapp_routes, "whatsapp_client", fake)
    body = payload("phone-1", "600000000", "wamid.unico", "reservar")

    assert client.post("/webhook/whatsapp", json=body).status_code == 200
    assert client.post("/webhook/whatsapp", json=body).status_code == 200
    assert len(fake.sent) == 1
