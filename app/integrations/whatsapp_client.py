# Envío de mensajes, botones y listas por WhatsApp.

import logging

import requests
from flask import current_app

from app.bot.message_formatters import format_date
from app.bot.time_utils import hhmm


class WhatsAppClient:
    def _url(self, phone_number_id: str) -> str:
        version = current_app.config.get("GRAPH_API_VERSION", "v23.0")
        return f"https://graph.facebook.com/{version}/{phone_number_id}/messages"

    def _headers(self) -> dict:
        token = current_app.config.get("WABA_TOKEN", "")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _post(self, phone_number_id: str, payload: dict) -> bool:
        token = current_app.config.get("WABA_TOKEN", "")
        if not token:
            logging.info("WABA_TOKEN no configurado. Respuesta no enviada: %s", payload)
            return True
        try:
            response = requests.post(self._url(phone_number_id), headers=self._headers(), json=payload, timeout=10)
            if response.status_code >= 300:
                logging.warning("Error enviando WhatsApp %s: %s", response.status_code, response.text[:300])
                return False
            return True
        except Exception:
            logging.exception("Error enviando mensaje a WhatsApp")
            return False

    def send_text(self, phone_number_id: str, to: str, body: str) -> bool:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body[:4000]},
        }
        return self._post(phone_number_id, payload)

    def send_main_menu(self, phone_number_id: str, to: str, body: str) -> bool:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body[:1024]},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "menu_reservar", "title": "Reservar"}},
                        {"type": "reply", "reply": {"id": "menu_cancelar", "title": "Cancelar"}},
                        {"type": "reply", "reply": {"id": "menu_duda", "title": "Duda"}},
                    ]
                },
            },
        }
        if self._post(phone_number_id, payload):
            return True
        return self.send_text(phone_number_id, to, body + "\n\nSelecciona una opción del menú de WhatsApp.")

    def send_confirm_buttons(self, phone_number_id: str, to: str, body: str, yes_title="Sí", no_title="No") -> bool:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body[:1024]},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "confirm_si", "title": yes_title[:20]}},
                        {"type": "reply", "reply": {"id": "confirm_no", "title": no_title[:20]}},
                    ]
                },
            },
        }
        if self._post(phone_number_id, payload):
            return True
        return self.send_text(phone_number_id, to, body + "\n\nUsa los botones para confirmar o cancelar.")

    def send_services_list(self, phone_number_id: str, to: str, body: str, servicios: list, page: int = 0) -> bool:
        rows = self._service_rows(servicios, page)
        payload = self._list_payload(to, body, "Ver servicios", "Servicios", rows)
        if self._post(phone_number_id, payload):
            return True
        fallback = body + "\n" + "\n".join(row["title"] for row in rows)
        return self.send_text(phone_number_id, to, fallback)

    def _service_rows(self, servicios: list, page: int) -> list[dict]:
        def to_row(servicio):
            precio = f"{float(servicio.precio):.2f} €"
            return {
                "id": f"servicio:{servicio.id}",
                "title": servicio.nombre[:24],
                "description": f"{servicio.duracion_min} min · {precio}"[:72],
            }

        return self._paginated_rows(
            servicios,
            page,
            item_to_row=to_row,
            prev_id="servicios_page",
            next_id="servicios_page",
        )

    def send_hours_list(self, phone_number_id: str, to: str, body: str, horas: list[str], page: int = 0) -> bool:
        rows = self._hour_rows(horas, page)
        payload = self._list_payload(to, body, "Ver horas", "Horas", rows)
        if self._post(phone_number_id, payload):
            return True
        fallback = body + "\n" + "\n".join(row["title"] for row in rows)
        return self.send_text(phone_number_id, to, fallback)

    def _hour_rows(self, horas: list[str], page: int) -> list[dict]:
        if len(horas) <= 10:
            return [{"id": f"hora:{hora}", "title": hora} for hora in horas]

        page = max(page, 0)
        total = len(horas)
        has_prev = page > 0
        start = 9 if page > 0 else 0
        if page > 0:
            start += (page - 1) * 8

        limit = 8 if has_prev else 9
        visible = horas[start:start + limit]
        rows = []
        if has_prev:
            rows.append({"id": f"horas_page:{page - 1}", "title": "Ver anteriores"})
        for hora in visible:
            rows.append({"id": f"hora:{hora}", "title": hora})
        if start + limit < total:
            rows.append({"id": f"horas_page:{page + 1}", "title": "Ver más"})
        return rows[:10]

    def send_reservations_list(self, phone_number_id: str, to: str, body: str, reservas: list, page: int = 0) -> bool:
        rows = self._reservation_rows(reservas, page)
        payload = self._list_payload(to, body, "Ver reservas", "Reservas", rows)
        if self._post(phone_number_id, payload):
            return True
        fallback = body + "\n" + "\n".join(row["title"] for row in rows)
        return self.send_text(phone_number_id, to, fallback)

    def _reservation_rows(self, reservas: list, page: int) -> list[dict]:
        def to_row(reserva):
            return {
                "id": f"reserva:{reserva.id}",
                "title": f"{format_date(reserva.fecha)} {hhmm(reserva.hora)}"[:24],
                "description": reserva.servicio.nombre[:72],
            }

        return self._paginated_rows(
            reservas,
            page,
            item_to_row=to_row,
            prev_id="reservas_page",
            next_id="reservas_page",
        )


    def _paginated_rows(self, items: list, page: int, item_to_row, prev_id: str, next_id: str) -> list[dict]:
        if len(items) <= 10:
            return [item_to_row(item) for item in items]

        page = max(int(page or 0), 0)
        has_prev = page > 0
        start = 9 if page > 0 else 0
        if page > 0:
            start += (page - 1) * 8

        limit = 8 if has_prev else 9
        visible = items[start:start + limit]

        rows = []
        if has_prev:
            rows.append({"id": f"{prev_id}:{page - 1}", "title": "Ver anteriores"})
        rows.extend(item_to_row(item) for item in visible)
        if start + limit < len(items):
            rows.append({"id": f"{next_id}:{page + 1}", "title": "Ver más"})
        return rows[:10]

    def _list_payload(self, to: str, body: str, button: str, section_title: str, rows: list) -> dict:
        return {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body[:1024]},
                "action": {
                    "button": button[:20],
                    "sections": [{"title": section_title[:24], "rows": rows}],
                },
            },
        }
