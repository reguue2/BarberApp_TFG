# Disponibilidad: horarios semanales y días cerrados.

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for

from app.bot.time_utils import to_min
from app.extensions import db
from app.forms.validators import clean_str, parse_date, parse_dia_semana, parse_time
from app.panel import panel_bp
from app.panel.helpers import current_peluqueria, current_peluqueria_id, login_required
from app.repositories.horario_repository import HorarioRepository
from app.repositories.reserva_repository import ReservaRepository
from app.utils.datetime_utils import now_local, today_local

DIAS_NOMBRE = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo",
}

MAX_TRAMOS_POR_DIA = 3


def _wants_json_response() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


def _dia_cerrado_form_errors(fecha) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not fecha:
        errors["fecha"] = "Indica una fecha válida."
    elif fecha < today_local():
        errors["fecha"] = "La fecha no puede ser anterior a hoy."
    return errors


@panel_bp.get("/disponibilidad")
@login_required
def disponibilidad():
    pelu = current_peluqueria()
    horarios = HorarioRepository.list_all_horarios(pelu.id)
    hoy = today_local()
    dias_cerrados = [
        dia for dia in HorarioRepository.list_all_dias_cerrados(pelu.id)
        if dia.fecha >= hoy
    ]

    horarios_por_dia = {dia: [] for dia in range(1, 8)}
    for h in horarios:
        if h.activo:
            horarios_por_dia[h.dia_semana].append(h)

    return render_template(
        "panel/disponibilidad.html",
        peluqueria=pelu,
        horarios_por_dia=horarios_por_dia,
        dias_nombre=DIAS_NOMBRE,
        dias_cerrados=dias_cerrados,
        hoy=hoy,
        max_tramos=MAX_TRAMOS_POR_DIA,
    )


@panel_bp.post("/disponibilidad/horarios")
@login_required
def guardar_horarios():
    pelu_id = current_peluqueria_id()

    dias = request.form.getlist("tramo_dia")
    inicios = request.form.getlist("tramo_inicio")
    fines = request.form.getlist("tramo_fin")

    if not (len(dias) == len(inicios) == len(fines)):
        flash("Datos de horarios incompletos.", "error")
        return redirect(url_for("panel.disponibilidad"))

    nuevos = []
    for d_raw, i_raw, f_raw in zip(dias, inicios, fines):
        if not d_raw and not i_raw and not f_raw:
            continue
        dia = parse_dia_semana(d_raw)
        inicio = parse_time(i_raw)
        fin = parse_time(f_raw)
        if dia is None or inicio is None or fin is None:
            flash("Algún tramo de horario tiene valores inválidos.", "error")
            return redirect(url_for("panel.disponibilidad"))
        if inicio >= fin:
            flash(f"En {DIAS_NOMBRE.get(dia, '')} la hora de inicio debe ser menor que la de fin.", "error")
            return redirect(url_for("panel.disponibilidad"))
        nuevos.append({"dia_semana": dia, "hora_inicio": inicio, "hora_fin": fin, "activo": True})

    por_dia = {}
    for tramo in nuevos:
        por_dia.setdefault(tramo["dia_semana"], []).append(tramo)
    for dia, tramos in por_dia.items():
        if len(tramos) > MAX_TRAMOS_POR_DIA:
            flash(
                f"En {DIAS_NOMBRE.get(dia, '')} no puedes tener más de {MAX_TRAMOS_POR_DIA} tramos.",
                "error",
            )
            return redirect(url_for("panel.disponibilidad"))
        tramos.sort(key=lambda t: t["hora_inicio"])
        for a, b in zip(tramos, tramos[1:]):
            if a["hora_fin"] > b["hora_inicio"]:
                flash(f"Hay tramos solapados en {DIAS_NOMBRE.get(dia, '')}.", "error")
                return redirect(url_for("panel.disponibilidad"))

    reservas_fuera = _count_future_reservations_outside_schedule(pelu_id, nuevos)

    try:
        HorarioRepository.replace_horarios(pelu_id, nuevos)
        db.session.commit()
        flash("Horarios guardados.", "success")
        if reservas_fuera:
            flash(
                f"Aviso: {reservas_fuera} reserva(s) futura(s) quedan fuera del nuevo horario. Revísalas en Reservas.",
                "warning",
            )
    except Exception:
        current_app.logger.exception("No se pudieron guardar los horarios de la peluquería %s", pelu_id)
        db.session.rollback()
        flash("No se pudieron guardar los horarios.", "error")
    return redirect(url_for("panel.disponibilidad"))


@panel_bp.post("/disponibilidad/dias-cerrados/nuevo")
@login_required
def dia_cerrado_nuevo():
    pelu_id = current_peluqueria_id()
    fecha = parse_date(request.form.get("fecha"))
    motivo = clean_str(request.form.get("motivo"), 150)
    confirmed = request.form.get("confirm_reservas") == "1"
    errors = _dia_cerrado_form_errors(fecha)

    if not errors and HorarioRepository.get_closed_day(pelu_id, fecha):
        errors["fecha"] = "Esa fecha ya está marcada como cerrada."

    if errors:
        if _wants_json_response():
            return jsonify({"ok": False, "errors": errors}), 400
        for message in errors.values():
            flash(message, "error")
        return redirect(url_for("panel.disponibilidad"))

    reservas_count = ReservaRepository.count_future_confirmed_by_day(pelu_id, fecha, now_local())
    if reservas_count and not confirmed:
        message = (
            f"Ese día tiene {reservas_count} reserva(s) confirmada(s). "
            "Si marcas el día como cerrado, las reservas seguirán existiendo y tendrás que revisarlas manualmente."
        )
        if _wants_json_response():
            return jsonify({
                "ok": False,
                "confirm_required": True,
                "message": message,
                "reservas_count": reservas_count,
            }), 409
        flash(message, "warning")
        return redirect(url_for("panel.disponibilidad"))

    try:
        HorarioRepository.add_dia_cerrado(pelu_id, fecha, motivo or None)
        db.session.commit()
    except Exception:
        current_app.logger.exception("No se pudo añadir el día cerrado %s para peluquería %s", fecha, pelu_id)
        db.session.rollback()
        if _wants_json_response():
            return jsonify({"ok": False, "errors": {"general": "No se pudo guardar el día cerrado."}}), 500
        flash("No se pudo guardar el día cerrado.", "error")
        return redirect(url_for("panel.disponibilidad"))

    if _wants_json_response():
        return jsonify({"ok": True, "redirect": url_for("panel.disponibilidad")}), 201

    if reservas_count:
        flash("Día cerrado añadido. Revisa las reservas confirmadas de esa fecha.", "warning")
    else:
        flash("Día cerrado añadido.", "success")
    return redirect(url_for("panel.disponibilidad"))


@panel_bp.post("/disponibilidad/dias-cerrados/<int:dia_id>/eliminar")
@login_required
def dia_cerrado_eliminar(dia_id):
    pelu_id = current_peluqueria_id()
    dia = HorarioRepository.get_dia_cerrado_by_id(pelu_id, dia_id)
    if not dia:
        flash("Día cerrado no encontrado.", "error")
        return redirect(url_for("panel.disponibilidad"))
    try:
        db.session.delete(dia)
        db.session.commit()
        flash("Día cerrado eliminado.", "success")
    except Exception:
        current_app.logger.exception("No se pudo eliminar el día cerrado %s", dia_id)
        db.session.rollback()
        flash("No se pudo eliminar el día cerrado.", "error")
    return redirect(url_for("panel.disponibilidad"))


def _count_future_reservations_outside_schedule(peluqueria_id: int, tramos: list[dict]) -> int:
    tramos_por_dia: dict[int, list[dict]] = {}
    for tramo in tramos:
        tramos_por_dia.setdefault(tramo["dia_semana"], []).append(tramo)

    total = 0
    for reserva in ReservaRepository.list_future_confirmed_with_relations(peluqueria_id, now_local()):
        dia = reserva.fecha.weekday() + 1
        if not _reservation_fits_any_slot(reserva, tramos_por_dia.get(dia, [])):
            total += 1
    return total


def _reservation_fits_any_slot(reserva, tramos: list[dict]) -> bool:
    if not reserva.servicio:
        return False
    inicio = to_min(reserva.hora)
    fin = inicio + int(reserva.servicio.duracion_min or 0)
    for tramo in tramos:
        if inicio >= to_min(tramo["hora_inicio"]) and fin <= to_min(tramo["hora_fin"]):
            return True
    return False
