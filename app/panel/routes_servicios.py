# CRUD de servicios.

from flask import flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func

from app.extensions import db
from app.forms.validators import clean_str, parse_decimal, parse_int
from app.models import Reserva
from app.panel import panel_bp
from app.panel.helpers import current_peluqueria, current_peluqueria_id, login_required
from app.repositories.servicio_repository import ServicioRepository


def _servicio_to_dict(servicio) -> dict:
    return {
        "id": servicio.id,
        "nombre": servicio.nombre,
        "descripcion": servicio.descripcion or "",
        "descripcion_view": servicio.descripcion or "Sin descripción",
        "precio": f"{float(servicio.precio):.2f}",
        "duracion_min": servicio.duracion_min,
        "activo": bool(servicio.activo),
    }


def _wants_json_response() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


def _nombre_duplicado(peluqueria_id: int, nombre: str, servicio_id: int | None = None) -> bool:
    query = ServicioRepository.list_all_by_peluqueria(peluqueria_id, search=None)
    return any(
        s.nombre.lower() == nombre.lower() and (servicio_id is None or s.id != servicio_id)
        for s in query
    )


def _servicio_form_errors(
    peluqueria_id: int,
    nombre: str,
    precio,
    duracion: int | None,
    servicio_id: int | None = None,
) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not nombre or len(nombre) < 2:
        errors["nombre"] = "El nombre del servicio es obligatorio."
    elif _nombre_duplicado(peluqueria_id, nombre, servicio_id=servicio_id):
        errors["nombre"] = "Ya existe un servicio con ese nombre."

    if precio is None:
        errors["precio"] = "El precio debe ser un número válido."
    if duracion is None:
        errors["duracion_min"] = "La duración debe estar entre 5 y 600 minutos."
    return errors


@panel_bp.get("/servicios")
@login_required
def servicios():
    pelu = current_peluqueria()
    search = (request.args.get("q") or "").strip()
    items = ServicioRepository.list_all_by_peluqueria(pelu.id, search=search or None)

    if request.args.get("ajax") == "1" or _wants_json_response():
        return jsonify({"servicios": [_servicio_to_dict(s) for s in items]})

    return render_template("panel/servicios.html", peluqueria=pelu, servicios=items, search=search)


@panel_bp.post("/servicios/nuevo")
@login_required
def servicio_nuevo():
    pelu_id = current_peluqueria_id()
    nombre = clean_str(request.form.get("nombre"), 120)
    descripcion = clean_str(request.form.get("descripcion"), 255)
    precio = parse_decimal(request.form.get("precio"))
    duracion = parse_int(request.form.get("duracion_min"), minimum=5, maximum=600)
    errors = _servicio_form_errors(pelu_id, nombre, precio, duracion)

    if errors:
        if _wants_json_response():
            return jsonify({"ok": False, "errors": errors}), 400
        for message in errors.values():
            flash(message, "error")
        return redirect(url_for("panel.servicios"))

    ServicioRepository.create(pelu_id, nombre, descripcion or None, precio, duracion, activo=True)
    db.session.commit()

    if _wants_json_response():
        return jsonify({"ok": True, "redirect": url_for("panel.servicios")}), 201

    flash("Servicio creado.", "success")
    return redirect(url_for("panel.servicios"))


@panel_bp.post("/servicios/<int:servicio_id>/editar")
@login_required
def servicio_editar(servicio_id):
    pelu_id = current_peluqueria_id()
    servicio = ServicioRepository.get_by_id(pelu_id, servicio_id)
    if not servicio:
        if _wants_json_response():
            return jsonify({"ok": False, "errors": {"general": "Servicio no encontrado."}}), 404
        flash("Servicio no encontrado.", "error")
        return redirect(url_for("panel.servicios"))

    nombre = clean_str(request.form.get("nombre"), 120)
    descripcion = clean_str(request.form.get("descripcion"), 255)
    precio = parse_decimal(request.form.get("precio"))
    duracion = parse_int(request.form.get("duracion_min"), minimum=5, maximum=600)
    errors = _servicio_form_errors(pelu_id, nombre, precio, duracion, servicio_id=servicio.id)

    if errors:
        if _wants_json_response():
            return jsonify({"ok": False, "errors": errors}), 400
        for message in errors.values():
            flash(message, "error")
        return redirect(url_for("panel.servicios"))

    servicio.nombre = nombre
    servicio.descripcion = descripcion or None
    servicio.precio = precio
    servicio.duracion_min = duracion
    db.session.commit()

    if _wants_json_response():
        return jsonify({"ok": True, "redirect": url_for("panel.servicios")})

    flash("Servicio actualizado.", "success")
    return redirect(url_for("panel.servicios"))


@panel_bp.post("/servicios/<int:servicio_id>/toggle")
@login_required
def servicio_toggle(servicio_id):
    pelu_id = current_peluqueria_id()
    servicio = ServicioRepository.get_by_id(pelu_id, servicio_id)
    if not servicio:
        flash("Servicio no encontrado.", "error")
        return redirect(url_for("panel.servicios"))
    servicio.activo = not servicio.activo
    db.session.commit()
    flash("Servicio actualizado.", "success")
    return redirect(url_for("panel.servicios"))


@panel_bp.post("/servicios/<int:servicio_id>/eliminar")
@login_required
def servicio_eliminar(servicio_id):
    pelu_id = current_peluqueria_id()
    servicio = ServicioRepository.get_by_id(pelu_id, servicio_id)
    if not servicio:
        flash("Servicio no encontrado.", "error")
        return redirect(url_for("panel.servicios"))

    reservas_count = db.session.query(func.count(Reserva.id)).filter(
        Reserva.peluqueria_id == pelu_id,
        Reserva.servicio_id == servicio.id,
    ).scalar()
    if reservas_count:
        flash("No se puede eliminar un servicio con reservas asociadas.", "error")
        return redirect(url_for("panel.servicios"))

    db.session.delete(servicio)
    db.session.commit()
    flash("Servicio eliminado.", "success")
    return redirect(url_for("panel.servicios"))
