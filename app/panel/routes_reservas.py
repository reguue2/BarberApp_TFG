# Reservas: calendario mensual + agenda diaria con vista tipo timeline.

import calendar
from datetime import date
from math import ceil

from flask import flash, jsonify, redirect, render_template, request, url_for

from app.bot.time_utils import from_min, to_min
from app.forms.validators import clean_str, parse_date, parse_int, parse_phone, parse_time
from app.panel import panel_bp
from app.panel.agenda_layout import UNIT_HEIGHT_PX, build_tramo_layout
from app.panel.helpers import current_peluqueria, login_required
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.horario_repository import HorarioRepository
from app.repositories.reserva_repository import ReservaRepository
from app.repositories.servicio_repository import ServicioRepository
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from app.utils.datetime_utils import now_local, today_local
from app.utils.phone_numbers import normalize_phone


@panel_bp.get("/reservas")
@login_required
def reservas():
    pelu = current_peluqueria()
    hoy = today_local()

    fecha = parse_date(request.args.get("fecha")) or hoy
    estado_filtro = request.args.get("estado") or "confirmadas"

    return _render_reservas_page(pelu, fecha, estado_filtro)


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
    agenda = _build_agenda(pelu, fecha, reservas_dia, dia_cerrado=dia_cerrado)

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
        agenda=agenda,
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
    """Prepara los datos del timeline diario para el template."""
    
    unit_min = peluqueria.rango_reservas_min or 30

    dia_semana = fecha.weekday() + 1
    tramos_db = [] if dia_cerrado else HorarioRepository.list_active_for_weekday(peluqueria.id, dia_semana)

    hoy = today_local()
    es_hoy = fecha == hoy
    ahora_min = 0
    if es_hoy:
        now = now_local()
        ahora_min = now.hour * 60 + now.minute

    reserva_items = []
    for r in reservas:
        dur = (r.servicio.duracion_min if r.servicio else None) or unit_min
        reserva_items.append({
            "start_min": to_min(r.hora),
            "dur_min": int(dur),
            "payload": r,
        })

    tramos_visibles = [
        (to_min(t.hora_inicio), to_min(t.hora_fin))
        for t in tramos_db
    ]

    if not tramos_visibles and reserva_items:
        inicio = min(r["start_min"] for r in reserva_items)
        fin = max(r["start_min"] + r["dur_min"] for r in reserva_items)
        safe_unit = unit_min if unit_min and unit_min > 0 else 30
        inicio = (inicio // safe_unit) * safe_unit
        fin = int(ceil(fin / safe_unit)) * safe_unit
        if fin <= inicio:
            fin = inicio + safe_unit
        tramos_visibles = [(inicio, fin)]

    tramos_layout = []
    encajadas = set()
    for ts, te in tramos_visibles:
        tramo = build_tramo_layout(ts, te, reserva_items, unit_min)
        tramos_layout.append(tramo)
        for ev in tramo["reservas"]:
            encajadas.add(id(ev["payload"]))

    fuera = [
        r["payload"]
        for r in reserva_items
        if id(r["payload"]) not in encajadas
    ]

    now_marker = None
    if es_hoy:
        safe_unit = unit_min if unit_min and unit_min > 0 else 30
        px_per_min = UNIT_HEIGHT_PX / safe_unit
        for tramo_idx, (ts, te) in enumerate(tramos_visibles):
            if ts <= ahora_min <= te:
                now_marker = {
                    "tramo_index": tramo_idx,
                    "top_px": int(round((ahora_min - ts) * px_per_min)),
                    "label": from_min(ahora_min),
                }
                break

    return {
        "tramos": tramos_layout,
        "fuera_horario": fuera,
        "unit_min": unit_min,
        "unit_height_px": UNIT_HEIGHT_PX,
        "now_marker": now_marker,
    }


def _filter_future_hours_for_today(horas, fecha):
    if fecha != today_local():
        return horas

    now = now_local()
    current_min = now.hour * 60 + now.minute
    return [hora for hora in horas if to_min(hora) >= current_min]


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
