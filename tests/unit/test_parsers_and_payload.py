"""Pruebas unitarias de utilidades pequeñas del bot."""

from app.bot.message_parser import detect_global_command, normalize_phone
from app.bot.whatsapp_payload_parser import WhatsAppPayloadParser
from app.forms.validators import parse_phone
from app.utils.phone_numbers import is_valid_phone


def test_detecta_comandos_globales_de_menu():
    assert detect_global_command("menú") == "menu"
    assert detect_global_command("volver") == "menu"


def test_normaliza_telefonos_espanoles():
    assert normalize_phone("+34 600 000 000") == "600000000"
    assert normalize_phone("0034 611 222 333") == "611222333"
    assert parse_phone("600 000 000") == "600000000"


def test_rechaza_telefonos_invalidos():
    assert is_valid_phone("1234567") is False
    assert parse_phone("1234567") is None
    assert parse_phone("6000000000") is None


def test_extrae_mensaje_de_texto_del_payload_de_whatsapp():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {"phone_number_id": "phone-1"},
                    "messages": [{
                        "id": "wamid.1",
                        "from": "34600000000",
                        "type": "text",
                        "text": {"body": "hola"},
                    }],
                }
            }]
        }]
    }

    messages = WhatsAppPayloadParser.parse(payload)

    assert len(messages) == 1
    assert messages[0].text == "hola"
    assert messages[0].phone_number_id == "phone-1"
