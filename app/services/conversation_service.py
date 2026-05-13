# Controla los pasos de la conversación por WhatsApp.

from dataclasses import dataclass
from datetime import date

from app.bot.message_formatters import format_date, format_reservation, format_service
from app.bot.message_parser import detect_global_command, normalize_phone
from app.bot.state_store import MemoryStateStore, empty_state
from app.integrations.openai_client import OpenAIClient
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.servicio_repository import ServicioRepository
from app.services.availability_service import AvailabilityService
from app.services.cancellation_service import CancellationService
from app.services.faq_service import FAQService
from app.services.reservation_service import ReservationService
from app.utils.datetime_utils import today_local


@dataclass
class BotResponse:
    kind: str
    text: str | None = None
    items: list | None = None
    extra: dict | None = None


class ConversationService:
    SERVICE_PAGE_SIZE = 9
    RESERVATION_PAGE_SIZE = 9

    def __init__(self, state_store=None, availability_service=None, reservation_service=None,
                 cancellation_service=None, faq_service=None, openai_client=None):
        self.state_store = state_store or MemoryStateStore()
        self.availability_service = availability_service or AvailabilityService()
        self.reservation_service = reservation_service or ReservationService(self.availability_service)
        self.cancellation_service = cancellation_service or CancellationService()
        self.faq_service = faq_service or FAQService()
        self.openai_client = openai_client

    def handle_message(self, peluqueria, telefono: str, text: str, origin: str = "text") -> BotResponse:
        telefono = normalize_phone(telefono)
        session_id = f"{peluqueria.id}:{telefono}"

        # "menú" o "volver" reinicia el flujo desde cualquier paso.
        command = detect_global_command(text)
        if command:
            self.state_store.delete(session_id)
            return self._main_menu(peluqueria)

        # El estado se guarda solo en memoria, no en la base de datos.
        state = self.state_store.get(session_id) or empty_state()
        step = state.get("step", "inicio")

        if step == "inicio":
            return self._handle_inicio(peluqueria, telefono, text, session_id)
        if step == "reservar_servicio":
            return self._handle_reservar_servicio(peluqueria, telefono, text, session_id, state)
        if step == "reservar_fecha":
            return self._handle_reservar_fecha(peluqueria, telefono, text, session_id, state)
        if step == "reservar_hora":
            return self._handle_reservar_hora(peluqueria, telefono, text, session_id, state)
        if step == "reservar_nombre":
            return self._handle_reservar_nombre(peluqueria, telefono, text, session_id, state)
        if step == "reservar_confirmar":
            return self._handle_reservar_confirmar(peluqueria, telefono, text, session_id, state)
        if step == "cancelar_listar":
            return self._handle_cancelar_listar(peluqueria, telefono, text, session_id, state)
        if step == "cancelar_confirmar":
            return self._handle_cancelar_confirmar(peluqueria, telefono, text, session_id, state)
        if step == "duda_preguntar":
            return self._handle_duda(peluqueria, telefono, text, session_id)

        self.state_store.delete(session_id)
        return self._main_menu(peluqueria)

    def _main_menu(self, peluqueria, text: str | None = None):
        body = text or (
            f"Hola, soy el asistente de la {peluqueria.nombre}✂️✨\n\n"
            "Puedes elegir una opción del menú. Si en algún momento quieres volver aquí, escribe \"menú\".\n\n"
            "¿Qué quieres hacer?"
        )
        return BotResponse(kind="main_menu", text=body)

    def _handle_inicio(self, peluqueria, telefono, text, session_id):
        value = (text or "").strip()
        if value == "menu_reservar":
            return self._start_reserva(peluqueria, telefono, session_id)
        if value == "menu_cancelar":
            return self._start_cancelacion(peluqueria, telefono, session_id)
        if value == "menu_duda":
            state = {"step": "duda_preguntar", "action": "duda", "data": {}}
            self.state_store.set(session_id, state)
            return BotResponse(kind="text", text="Consultame tu duda y te ayudo con lo que necesites.")

        return self._main_menu(
            peluqueria,
            f"Hola, soy el asistente de la {peluqueria.nombre}✂️✨\n\n"
            "Puedes elegir una opción del menú. Si en algún momento quieres volver aquí, escribe \"menú\".\n\n"
            "Selecciona una opción para continuar."
        )

    def _start_reserva(self, peluqueria, telefono, session_id):
        servicios = ServicioRepository.list_active_by_peluqueria(peluqueria.id)
        if not servicios:
            self.state_store.delete(session_id)
            return self._text_then_menu("Ahora mismo no hay servicios disponibles para reservar.", "¿Quieres hacer otra gestión?")

        state = {"step": "reservar_servicio", "action": "reservar", "data": {"servicio_page": 0}}
        self.state_store.set(session_id, state)
        return self._services_response(servicios, page=0, text="Elige el servicio que quieres reservar:")

    def _handle_reservar_servicio(self, peluqueria, telefono, text, session_id, state):
        servicios = ServicioRepository.list_active_by_peluqueria(peluqueria.id)
        value = (text or "").strip()
        if value.startswith("servicios_page:"):
            page = self._page_from_text(value)
            state["data"]["servicio_page"] = page
            self.state_store.set(session_id, state)
            return self._services_response(servicios, page=page, text="Elige el servicio que quieres reservar:")

        servicio = self._service_from_list_id(text, servicios)
        if not servicio:
            page = state["data"].get("servicio_page", 0)
            return self._services_response(servicios, page=page, text="Para continuar, elige un servicio desde la lista.")

        state["step"] = "reservar_fecha"
        state["data"]["servicio_id"] = servicio.id
        self.state_store.set(session_id, state)
        return BotResponse(kind="text", text=f"Has elegido {servicio.nombre}. ¿Para qué fecha quieres la cita? Por ejemplo: 15/05/2026")

    def _services_response(self, servicios, page=0, text=None):
        body = text or "Elige el servicio que quieres reservar:"
        return BotResponse(kind="service_list", text=body, items=servicios, extra={"page": page})

    def _service_from_list_id(self, text, servicios):
        value = (text or "").strip()
        if not value.startswith("servicio:"):
            return None
        try:
            sid = int(value.split(":", 1)[1])
        except ValueError:
            return None
        for servicio in servicios:
            if servicio.id == sid:
                return servicio
        return None

    def _handle_reservar_fecha(self, peluqueria, telefono, text, session_id, state):
        # La fecha se interpreta con IA porque aquí el usuario escribe texto libre.
        today = today_local()
        fecha = self._openai().parse_date(text, today=today)
        if not fecha:
            return BotResponse(
                kind="text",
                text="No he entendido bien la fecha. Escríbela de nuevo, por ejemplo: 15/05/2026.",
            )
        if fecha < today:
            return BotResponse(kind="text", text="No se puede reservar en una fecha pasada. Indica otra fecha.")

        servicio = ServicioRepository.get_active_by_id(peluqueria.id, state["data"].get("servicio_id"))
        if not servicio:
            self.state_store.delete(session_id)
            return self._text_then_menu("El servicio ya no está disponible. Vuelve a empezar desde el menú.", "¿Quieres hacer otra gestión?")

        horas = self.availability_service.get_available_slots_for_service(peluqueria, servicio, fecha)
        if not horas:
            return BotResponse(kind="text", text=f"No hay horas disponibles para el {format_date(fecha)}. Prueba con otra fecha.")

        state["step"] = "reservar_hora"
        state["data"]["fecha"] = fecha.isoformat()
        state["data"]["hora_page"] = 0
        self.state_store.set(session_id, state)
        return self._hours_response(fecha, horas, page=0)

    def _handle_reservar_hora(self, peluqueria, telefono, text, session_id, state):
        fecha = date.fromisoformat(state["data"]["fecha"])
        servicio = ServicioRepository.get_active_by_id(peluqueria.id, state["data"].get("servicio_id"))
        horas = self.availability_service.get_available_slots_for_service(peluqueria, servicio, fecha)
        if not horas:
            return BotResponse(kind="text", text="Ya no quedan horas disponibles para esa fecha. Prueba con otra fecha.")

        value = (text or "").strip()
        if value.startswith("horas_page:"):
            page = self._page_from_text(value)
            state["data"]["hora_page"] = page
            self.state_store.set(session_id, state)
            return self._hours_response(fecha, horas, page=page)

        # Las horas solo se aceptan desde la lista de WhatsApp.
        if not value.startswith("hora:"):
            page = state["data"].get("hora_page", 0)
            return self._hours_response(fecha, horas, page=page, text="Para continuar, elige una hora desde la lista.")

        hora = value.split(":", 1)[1]
        if hora not in horas:
            return self._hours_response(fecha, horas, page=state["data"].get("hora_page", 0), text="Esa hora no está disponible. Elige una de la lista.")

        state["data"]["hora"] = hora
        cliente = ClienteRepository.get_by_phone(peluqueria.id, telefono)
        if cliente:
            state["data"]["cliente_nombre"] = cliente.nombre
            state["step"] = "reservar_confirmar"
            self.state_store.set(session_id, state)
            return self._resumen_reserva(peluqueria, state)

        state["step"] = "reservar_nombre"
        self.state_store.set(session_id, state)
        return BotResponse(kind="text", text="Perfecto. ¿A nombre de quién hago la reserva?")

    def _page_from_text(self, text):
        try:
            page = int(text.split(":", 1)[1])
            return max(page, 0)
        except ValueError:
            return 0

    def _hours_response(self, fecha, horas, page=0, text=None):
        body = text or f"Horas disponibles para el {format_date(fecha)}:"
        return BotResponse(kind="hours_list", text=body, items=horas, extra={"page": page})

    def _handle_reservar_nombre(self, peluqueria, telefono, text, session_id, state):
        # El nombre también puede venir escrito de muchas formas.
        nombre = self._openai().extract_name(text)
        if not nombre:
            return BotResponse(kind="text", text="No he podido identificar el nombre. Escríbelo de nuevo de forma sencilla, por ejemplo: Mario García.")
        state["data"]["cliente_nombre"] = nombre
        state["step"] = "reservar_confirmar"
        self.state_store.set(session_id, state)
        return self._resumen_reserva(peluqueria, state)

    def _resumen_reserva(self, peluqueria, state):
        data = state["data"]
        servicio = ServicioRepository.get_active_by_id(peluqueria.id, data["servicio_id"])
        fecha = date.fromisoformat(data["fecha"])
        text = (
            "Resumen de tu reserva:\n\n"
            f"Servicio: {format_service(servicio)}\n"
            f"Fecha: {format_date(fecha)}\n"
            f"Hora: {data['hora']}\n"
            f"Nombre: {data['cliente_nombre']}\n\n"
            "¿Confirmas la reserva?"
        )
        return BotResponse(kind="confirm_buttons", text=text, extra={"yes": "Sí, confirmar", "no": "No, cancelar"})

    def _handle_reservar_confirmar(self, peluqueria, telefono, text, session_id, state):
        value = (text or "").strip()
        if value not in {"confirm_si", "confirm_no"}:
            return self._resumen_reserva(peluqueria, state)
        if value == "confirm_no":
            self.state_store.delete(session_id)
            return self._text_then_menu("❌ Reserva no confirmada.", "¿Quieres hacer otra gestión?")

        data = state["data"]
        result = self.reservation_service.create_from_whatsapp(
            peluqueria=peluqueria,
            servicio_id=data["servicio_id"],
            telefono_cliente=telefono,
            nombre_cliente=data["cliente_nombre"],
            fecha=date.fromisoformat(data["fecha"]),
            hora_txt=data["hora"],
        )

        if not result.ok:
            if result.error == "slot_not_available" and result.available_slots:
                state["step"] = "reservar_hora"
                state["data"].pop("hora", None)
                state["data"]["hora_page"] = 0
                self.state_store.set(session_id, state)

                return BotResponse(
                    kind="hours_list",
                    text="Esa hora se acaba de ocupar. Elige otra:",
                    items=result.available_slots,
                    extra={"page": 0},
                )

            if result.error == "slot_not_available":
                state["step"] = "reservar_fecha"
                state["data"].pop("fecha", None)
                state["data"].pop("hora", None)
                state["data"].pop("hora_page", None)
                self.state_store.set(session_id, state)

                return BotResponse(
                    kind="text",
                    text="Ya no quedan horas disponibles para esa fecha. Dime otra fecha para la cita.",
                )

            self.state_store.delete(session_id)
            return self._text_then_menu(
                "No he podido crear la reserva. Prueba otra vez o contacta con la peluquería.",
                "¿Quieres hacer otra gestión?",
            )

        self.state_store.delete(session_id)
        text = f"✅ Reserva confirmada.\n\n{format_reservation(result.reserva)}"
        return self._text_then_menu(text, "¿Quieres hacer algo más?")

    def _start_cancelacion(self, peluqueria, telefono, session_id):
        reservas = self.cancellation_service.list_future_reservations(peluqueria.id, normalize_phone(telefono))
        if not reservas:
            self.state_store.delete(session_id)
            return self._text_then_menu("No encuentro reservas futuras asociadas a este número de WhatsApp.", "¿Quieres hacer otra gestión?")

        state = {"step": "cancelar_listar", "action": "cancelar", "data": {"reserva_page": 0}}
        self.state_store.set(session_id, state)
        if len(reservas) == 1:
            state["step"] = "cancelar_confirmar"
            state["data"]["reserva_id"] = reservas[0].id
            self.state_store.set(session_id, state)
            return self._resumen_cancelacion(reservas[0])
        return self._reservations_response(reservas, page=0, text="Elige la reserva que quieres cancelar:")

    def _handle_cancelar_listar(self, peluqueria, telefono, text, session_id, state):
        reservas = self.cancellation_service.list_future_reservations(peluqueria.id, normalize_phone(telefono))
        if not reservas:
            self.state_store.delete(session_id)
            return self._text_then_menu("No encuentro reservas futuras asociadas a este número de WhatsApp.", "¿Quieres hacer otra gestión?")

        value = (text or "").strip()
        if value.startswith("reservas_page:"):
            page = self._page_from_text(value)
            state["data"]["reserva_page"] = page
            self.state_store.set(session_id, state)
            return self._reservations_response(reservas, page=page, text="Elige la reserva que quieres cancelar:")

        reserva_id = self._reserva_id_from_text(text)
        if not reserva_id:
            page = state["data"].get("reserva_page", 0)
            return self._reservations_response(reservas, page=page, text="Para continuar, elige una reserva desde la lista.")

        reserva = self._reservation_from_list_id(reserva_id, reservas)
        if not reserva:
            page = state["data"].get("reserva_page", 0)
            return self._reservations_response(reservas, page=page, text="No encuentro esa reserva asociada a tu número. Elige una de la lista.")

        state["step"] = "cancelar_confirmar"
        state["data"]["reserva_id"] = reserva_id
        self.state_store.set(session_id, state)
        return self._resumen_cancelacion(reserva)

    def _reservations_response(self, reservas, page=0, text=None):
        body = text or "Elige la reserva que quieres cancelar:"
        return BotResponse(kind="reservations_list", text=body, items=reservas, extra={"page": page})

    def _reservation_from_list_id(self, reserva_id, reservas):
        for reserva in reservas:
            if reserva.id == reserva_id:
                return reserva
        return None

    def _resumen_cancelacion(self, reserva):
        text = f"Vas a cancelar esta reserva:\n\n{format_reservation(reserva)}\n\n¿Confirmas la cancelación?"
        return BotResponse(kind="confirm_buttons", text=text, extra={"yes": "Sí, cancelar", "no": "No, mantener"})

    def _reserva_id_from_text(self, text):
        value = (text or "").strip()
        if value.startswith("reserva:"):
            try:
                return int(value.split(":", 1)[1])
            except ValueError:
                return None
        return None

    def _handle_cancelar_confirmar(self, peluqueria, telefono, text, session_id, state):
        value = (text or "").strip()
        reservas = self.cancellation_service.list_future_reservations(peluqueria.id, normalize_phone(telefono))
        reserva = self._reservation_from_list_id(state["data"].get("reserva_id"), reservas)
        if value not in {"confirm_si", "confirm_no"}:
            if reserva:
                return self._resumen_cancelacion(reserva)
            self.state_store.delete(session_id)
            return self._text_then_menu("No encuentro esa reserva asociada a tu número.", "¿Quieres hacer otra gestión?")
        if value == "confirm_no":
            self.state_store.delete(session_id)
            return self._text_then_menu("No he cancelado la reserva.", "¿Quieres hacer otra gestión?")

        result = self.cancellation_service.cancel_from_whatsapp(
            peluqueria_id=peluqueria.id,
            telefono_cliente=normalize_phone(telefono),
            reserva_id=state["data"].get("reserva_id"),
        )
        self.state_store.delete(session_id)
        if not result.ok:
            return self._text_then_menu("No he podido cancelar la reserva. Puede que ya esté cancelada o que sea una reserva pasada.", "¿Quieres hacer otra gestión?")
        text = f"❌ Reserva cancelada.\n\n{format_reservation(result.reserva)}"
        return self._text_then_menu(text, "¿Quieres hacer algo más?")

    def _handle_duda(self, peluqueria, telefono, text, session_id):
        self.state_store.delete(session_id)
        answer = self.faq_service.answer(peluqueria, text)
        return self._text_then_menu(answer, "¿Tienes alguna otra duda o quieres hacer otra gestión?")

    def _text_then_menu(self, text, menu_text):
        return BotResponse(kind="text_then_menu", text=text, extra={"menu_text": menu_text})

    def _openai(self):
        return self.openai_client or OpenAIClient()
