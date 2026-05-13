# Reservas: calendario mensual + agenda diaria con bloques de hora.

import calendar
from datetime import date
from math import ceil

from flask import flash, jsonify, redirect, render_template, request, url_for

from app.bot.time_utils import from_min, to_min
from app.forms.validators import clean_str, parse_date, parse_int, parse_phone, parse_time
from app.panel import panel_bp
from app.panel.helpers import current_peluqueria, login_required
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.horario_repository import HorarioRepository
from app.repositories.reserva_repository import ReservaRepository
from app.repositories.servicio_repository import ServicioRepository
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from app.utils.datetime_utils import now_local, today_local
from app.utils.phone_numbers import normalize_phone

AGENDA_PAGE_SIZE = 10


@panel_bp.get("/reservas")
@login_required
def reservas():
    pelu = current_peluqueria()
    hoy = today_local()

    fecha = parse_date(request.args.get("fecha")) or hoy
    estado_filtro = request.args.get("estado") or "confirmadas"
    page = parse_int(request.args.get("page"), minimum=1) or 1

    return _render_reservas_page(pelu, fecha, estado_filtro, page)


@panel_bp.post("/reservas/nueva")
@login_required
def nueva_reserva():
    pelu = current_peluqueria()

    raw_servicio_id = request.form.get("servicio_id") or ""
    raw_fecha = request.form.get("fecha") or ""
    raw_hora = request.form.get("hora") or ""
    raw_nombre = request.form.get("nombre") or ""
    raw_telefono = request.form.get("telefono") or ""

    servicio_id = parse_int(raw_servicio_id, minimum=1)
    fecha = parse_date(raw_fecha)
    hora_txt = clean_str(raw_hora, 5)
    nombre = clean_str(raw_nombre, 100)
    telefono = parse_phone(raw_telefono)

    form_values = {
        "servicio_id": raw_servicio_id,
        "fecha": raw_fecha,
        "hora": raw_hora,
        "nombre": raw_nombre,
        "telefono": raw_telefono,
    }
    form_errors = _validate_reserva_form(servicio_id, fecha, hora_txt, nombre, telefono)
    fecha_contexto = fecha or today_local()

    if form_errors:
        return _render_reservas_page(
            pelu,
            fecha_contexto,
            "confirmadas",
            1,
            form_errors=form_errors,
            form_values=form_values,
            abrir_modal_nueva_reserva=True,
        ), 400

    booking = BookingService()
    result = booking.create_reservation(
        peluqueria=pelu,
        servicio_id=servicio_id,
        telefono_cliente=telefono,
        nombre_cliente=nombre,
        fecha=fecha,
        hora_txt=hora_txt,
        origen="panel",
    )

    if not result.ok:
        field = _error_to_field(result.error)
        if field:
            form_errors[field] = _error_to_message(result.error, result.details)
            return _render_reservas_page(
                pelu,
                fecha_contexto,
                "confirmadas",
                1,
                form_errors=form_errors,
                form_values=form_values,
                abrir_modal_nueva_reserva=True,
            ), 409

        flash(_error_to_message(result.error, result.details), "error")
        return redirect(url_for("panel.reservas", fecha=fecha_contexto.isoformat()))

    flash("Reserva creada correctamente.", "success")
    return redirect(url_for("panel.reservas", fecha=fecha.isoformat()))


@panel_bp.post("/reservas/<int:reserva_id>/cancelar")
@login_required
def cancelar_reserva(reserva_id):
    pelu = current_peluqueria()
    booking = BookingService()
    result = booking.cancel_from_panel(pelu.id, reserva_id)

    if not result.ok:
        flash(_error_to_message(result.error), "error")
    else:
        flash("Reserva cancelada.", "success")

    fecha_param = parse_date(request.form.get("fecha")) or today_local()
    return redirect(url_for("panel.reservas", fecha=fecha_param.isoformat()))


@panel_bp.get("/reservas/horas-disponibles")
@login_required
def horas_disponibles():
    """Endpoint JSON para el modal de nueva reserva."""
    pelu = current_peluqueria()
    servicio_id = parse_int(request.args.get("servicio_id"), minimum=1)
    fecha = parse_date(request.args.get("fecha"))

    if not servicio_id or not fecha:
        return jsonify({"horas": []})

    servicio = ServicioRepository.get_active_by_id(pelu.id, servicio_id)
    if not servicio:
        return jsonify({"horas": []})

    dia_cerrado = HorarioRepository.get_closed_day(pelu.id, fecha)
    if dia_cerrado:
        return jsonify({
            "horas": [],
            "closed": True,
            "message": "La peluquería está cerrada ese día.",
        })

    horas = AvailabilityService().get_available_slots_for_service(pelu, servicio, fecha)
    horas = _filter_future_hours_for_today(horas, fecha)
    return jsonify({"horas": horas})


@panel_bp.get("/reservas/clientes-buscar")
@login_required
def buscar_clientes_reserva():
    """Endpoint JSON para sugerir clientes existentes en nueva reserva."""
    pelu = current_peluqueria()
    search = (request.args.get("q") or "").strip()
    field = (request.args.get("field") or "").strip()

    clientes = ClienteRepository.search_for_reservation(
        peluqueria_id=pelu.id,
        search=search,
        field=field,
        limit=8,
    )

    return jsonify({
        "clientes": [
            {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "telefono": normalize_phone(cliente.telefono),
            }
            for cliente in clientes
        ]
    })


# ---------- helpers internos ----------

def _render_reservas_page(
        pelu,
        fecha,
        estado_filtro,
        page,
        form_errors=None,
        form_values=None,
        abrir_modal_nueva_reserva=False):
    hoy = today_local()
    anio = fecha.year
    mes = fecha.month

    cal = calendar.Calendar(firstweekday=0)  # 0 = lunes
    semanas = cal.monthdatescalendar(anio, mes)

    only_confirmed = estado_filtro == "confirmadas"
    reservas_dia = ReservaRepository.list_by_day_with_relations(pelu.id, fecha, only_confirmed=only_confirmed)
    if estado_filtro == "canceladas":
        reservas_dia = [r for r in reservas_dia if r.estado == "cancelada"]

    dia_cerrado = HorarioRepository.get_closed_day(pelu.id, fecha)
    bloques = _build_agenda(pelu, fecha, reservas_dia, dia_cerrado=dia_cerrado)
    bloques, agenda_pagination = _paginate_agenda(bloques, page)

    if mes == 1:
        prev_mes_fecha = date(anio - 1, 12, 1)
    else:
        prev_mes_fecha = date(anio, mes - 1, 1)
    if mes == 12:
        next_mes_fecha = date(anio + 1, 1, 1)
    else:
        next_mes_fecha = date(anio, mes + 1, 1)

    return render_template(
        "panel/reservas.html",
        peluqueria=pelu,
        fecha=fecha,
        hoy=hoy,
        anio=anio,
        mes=mes,
        semanas=semanas,
        bloques=bloques,
        agenda_pagination=agenda_pagination,
        dia_cerrado=dia_cerrado,
        estado_filtro=estado_filtro,
        prev_mes=prev_mes_fecha,
        next_mes=next_mes_fecha,
        servicios=ServicioRepository.list_active_by_peluqueria(pelu.id),
        nombre_mes=_nombre_mes(mes),
        form_errors=form_errors or {},
        form_values=form_values or {},
        abrir_modal_nueva_reserva=abrir_modal_nueva_reserva,
    )


def _build_agenda(peluqueria, fecha, reservas, dia_cerrado=None):
    """Construye los bloques visibles de la agenda diaria.

    Si la fecha está cerrada, no se muestran huecos libres de horario. Solo se
    mantienen reservas existentes para que el administrador pueda revisarlas.
    Si la fecha es hoy, se ocultan huecos libres pasados, pero no reservas existentes.
    """
    dia_semana = fecha.weekday() + 1
    tramos = [] if dia_cerrado else HorarioRepository.list_active_for_weekday(peluqueria.id, dia_semana)

    paso = peluqueria.rango_reservas_min or 30
    bloques_horarios = []
    if tramos:
        for tramo in tramos:
            inicio = to_min(tramo.hora_inicio)
            fin = to_min(tramo.hora_fin)
            cur = inicio
            while cur < fin:
                bloques_horarios.append(from_min(cur))
                cur += paso

    bloques_reservas = sorted({r.hora.strftime("%H:%M") for r in reservas})
    todas_horas = sorted(set(bloques_horarios) | set(bloques_reservas))
    todas_horas = _filter_visible_hours_for_agenda(todas_horas, fecha, reservas)

    if not todas_horas and not reservas:
        # día sin horario y sin reservas: render vacío con cabecera
        return []

    bloques = []
    for hora in todas_horas:
        match = [r for r in reservas if r.hora.strftime("%H:%M") == hora]
        bloques.append({"hora": hora, "reservas": match})

    return bloques


def _paginate_agenda(bloques, page):
    """Pagina la agenda por entradas visibles, no solo por horas.

    Una hora con varias reservas cuenta como varias entradas. Así la paginación
    mantiene un tamaño realista aunque existan varias reservas en el mismo tramo.
    Los huecos libres cuentan como una entrada para no perder horas disponibles.
    """
    agenda_items = []
    for bloque in bloques:
        if bloque["reservas"]:
            for reserva in bloque["reservas"]:
                agenda_items.append({"hora": bloque["hora"], "reserva": reserva})
        else:
            agenda_items.append({"hora": bloque["hora"], "reserva": None})

    total = len(agenda_items)
    total_pages = max(1, ceil(total / AGENDA_PAGE_SIZE)) if total else 1
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * AGENDA_PAGE_SIZE
    end = start + AGENDA_PAGE_SIZE

    page_items = agenda_items[start:end]
    page_blocks = []
    for item in page_items:
        if not page_blocks or page_blocks[-1]["hora"] != item["hora"]:
            page_blocks.append({"hora": item["hora"], "reservas": []})
        if item["reserva"] is not None:
            page_blocks[-1]["reservas"].append(item["reserva"])

    pagination = {
        "page": current_page,
        "total_pages": total_pages,
        "has_prev": current_page > 1,
        "has_next": current_page < total_pages,
        "prev_page": current_page - 1,
        "next_page": current_page + 1,
        "total_items": total,
    }
    return page_blocks, pagination


def _filter_future_hours_for_today(horas, fecha):
    if fecha != today_local():
        return horas

    now = now_local()
    current_min = now.hour * 60 + now.minute
    return [hora for hora in horas if to_min(hora) >= current_min]


def _filter_visible_hours_for_agenda(horas, fecha, reservas):
    if fecha != today_local():
        return horas

    now = now_local()
    current_min = now.hour * 60 + now.minute
    reservation_hours = {r.hora.strftime("%H:%M") for r in reservas}
    return [
        hora for hora in horas
        if hora in reservation_hours or to_min(hora) >= current_min
    ]


def _validate_reserva_form(servicio_id, fecha, hora_txt, nombre, telefono):
    errors = {}

    if not servicio_id:
        errors["servicio_id"] = "Selecciona un servicio."
    if not fecha:
        errors["fecha"] = "Selecciona una fecha válida."
    elif fecha < today_local():
        errors["fecha"] = "La fecha no puede ser anterior a hoy."
    if not hora_txt or not parse_time(hora_txt):
        errors["hora"] = "Selecciona una hora disponible."
    if not nombre or len(nombre) < 2:
        errors["nombre"] = "Indica el nombre del cliente."
    if not telefono:
        errors["telefono"] = "El teléfono debe tener 9 cifras y empezar por 6, 7, 8 o 9."

    return errors


def _nombre_mes(mes: int) -> str:
    nombres = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    return nombres[mes - 1]


def _error_to_field(error: str | None) -> str | None:
    return {
        "service_not_found": "servicio_id",
        "phone_required": "telefono",
        "invalid_phone": "telefono",
        "client_name_required": "nombre",
        "invalid_time": "hora",
        "slot_not_available": "hora",
        "client_phone_conflict": "telefono",
    }.get(error)


def _error_to_message(error: str | None, details: dict | None = None) -> str:
    if error == "client_phone_conflict":
        existing_name = (details or {}).get("existing_name")
        if existing_name:
            return f"Ese teléfono ya pertenece a {existing_name}. Selecciona ese cliente o usa otro teléfono."
        return "Ese teléfono ya pertenece a otro cliente. Selecciona ese cliente o usa otro teléfono."

    return {
        "service_not_found": "El servicio seleccionado no existe o no está activo.",
        "phone_required": "Falta el teléfono del cliente.",
        "invalid_phone": "El teléfono debe tener 9 cifras y empezar por 6, 7, 8 o 9.",
        "client_name_required": "Falta el nombre del cliente.",
        "invalid_time": "La hora indicada no es válida.",
        "slot_not_available": "Esa hora ya no está disponible.",
        "reservation_not_found": "No se ha encontrado la reserva.",
        "already_cancelled": "La reserva ya estaba cancelada.",
        "unexpected_error": "Ha ocurrido un error inesperado. Inténtalo de nuevo.",
    }.get(error, "No se ha podido completar la operación.")
