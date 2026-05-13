# Webhook que recibe los mensajes enviados desde WhatsApp.

import hashlib
import hmac
import logging

from flask import Blueprint, current_app, jsonify, request

from app.bot.whatsapp_payload_parser import WhatsAppPayloadParser
from app.integrations.whatsapp_client import WhatsAppClient
from app.repositories.peluqueria_repository import PeluqueriaRepository
from app.services.conversation_service import ConversationService
from app.services.idempotency_service import IdempotencyService


whatsapp_bp = Blueprint("whatsapp", __name__, url_prefix="/webhook/whatsapp")
conversation_service = ConversationService()
whatsapp_client = WhatsAppClient()
idempotency_service = IdempotencyService()


@whatsapp_bp.get("")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == current_app.config.get("WABA_VERIFY_TOKEN"):
        return challenge or "", 200
    return "Forbidden", 403


@whatsapp_bp.post("")
def receive_webhook():
    raw_body = request.get_data()
    # Si hay App Secret, se valida que el mensaje venga de Meta.
    if not _valid_signature(raw_body):
        return jsonify({"status": "invalid_signature"}), 403

    payload = request.get_json(silent=True) or {}
    # El parser ignora estados y deja solo mensajes reales.
    messages = WhatsAppPayloadParser.parse(payload)
    if not messages:
        return jsonify({"status": "ignored"}), 200

    for msg in messages:
        if idempotency_service.already_processed(msg.wamid):
            continue

        # El phone_number_id decide a qué peluquería pertenece el mensaje.
        peluqueria = PeluqueriaRepository.get_by_wa_phone_number_id(msg.phone_number_id)
        if not peluqueria:
            logging.warning("Mensaje recibido para phone_number_id no registrado: %s", msg.phone_number_id)
            continue

        response = conversation_service.handle_message(
            peluqueria=peluqueria,
            telefono=msg.from_phone,
            text=msg.text,
            origin=msg.origin,
        )
        _send_response(msg.phone_number_id, msg.from_phone, response)

    return jsonify({"status": "ok"}), 200


def _send_response(phone_number_id: str, to: str, response):
    if response.kind == "main_menu":
        whatsapp_client.send_main_menu(phone_number_id, to, response.text)
    elif response.kind == "service_list":
        page = (response.extra or {}).get("page", 0)
        whatsapp_client.send_services_list(phone_number_id, to, response.text, response.items or [], page=page)
    elif response.kind == "hours_list":
        page = (response.extra or {}).get("page", 0)
        whatsapp_client.send_hours_list(phone_number_id, to, response.text, response.items or [], page=page)
    elif response.kind == "reservations_list":
        page = (response.extra or {}).get("page", 0)
        whatsapp_client.send_reservations_list(phone_number_id, to, response.text, response.items or [], page=page)
    elif response.kind == "confirm_buttons":
        extra = response.extra or {}
        whatsapp_client.send_confirm_buttons(
            phone_number_id,
            to,
            response.text or "",
            yes_title=extra.get("yes", "Sí"),
            no_title=extra.get("no", "No"),
        )
    elif response.kind == "text_then_menu":
        whatsapp_client.send_text(phone_number_id, to, response.text or "")
        menu_text = (response.extra or {}).get("menu_text", "¿Quieres hacer algo más?")
        whatsapp_client.send_main_menu(phone_number_id, to, menu_text)
    else:
        whatsapp_client.send_text(phone_number_id, to, response.text or "")


def _valid_signature(raw_body: bytes) -> bool:
    app_secret = current_app.config.get("WABA_APP_SECRET")
    if not app_secret:
        return True

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return False
    digest = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, "sha256=" + digest)
