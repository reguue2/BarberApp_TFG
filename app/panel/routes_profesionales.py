# CRUD de profesionales.

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.forms.validators import clean_str
from app.panel import panel_bp
from app.panel.helpers import current_peluqueria, current_peluqueria_id, login_required
from app.repositories.profesional_repository import ProfesionalRepository
from app.repositories.reserva_repository import ReservaRepository
from app.utils.datetime_utils import now_local


def _wants_json_response() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


def _profesional_form_errors(nombre: str) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not nombre or len(nombre) < 2:
        errors["nombre"] = "El nombre del profesional es obligatorio."
    return errors


@panel_bp.get("/profesionales")
@login_required
def profesionales():
    pelu = current_peluqueria()
    items = ProfesionalRepository.list_by_peluqueria(pelu.id)
    return render_template("panel/profesionales.html", peluqueria=pelu, profesionales=items)


@panel_bp.post("/profesionales/nuevo")
@login_required
def profesional_nuevo():
    pelu_id = current_peluqueria_id()
    nombre = clean_str(request.form.get("nombre"), 100)
    errors = _profesional_form_errors(nombre)

    if errors:
        if _wants_json_response():
            return jsonify({"ok": False, "errors": errors}), 400
        for message in errors.values():
            flash(message, "error")
        return redirect(url_for("panel.profesionales"))

    ProfesionalRepository.create(pelu_id, nombre)
    db.session.commit()

    if _wants_json_response():
        return jsonify({"ok": True, "redirect": url_for("panel.profesionales")}), 201

    flash("Profesional añadido.", "success")
    return redirect(url_for("panel.profesionales"))


@panel_bp.post("/profesionales/<int:profesional_id>/editar")
@login_required
def profesional_editar(profesional_id):
    pelu_id = current_peluqueria_id()
    profesional = ProfesionalRepository.get_by_id(pelu_id, profesional_id)
    if not profesional:
        if _wants_json_response():
            return jsonify({"ok": False, "errors": {"general": "Profesional no encontrado."}}), 404
        flash("Profesional no encontrado.", "error")
        return redirect(url_for("panel.profesionales"))

    nombre = clean_str(request.form.get("nombre"), 100)
    errors = _profesional_form_errors(nombre)

    if errors:
        if _wants_json_response():
            return jsonify({"ok": False, "errors": errors}), 400
        for message in errors.values():
            flash(message, "error")
        return redirect(url_for("panel.profesionales"))

    profesional.nombre = nombre
    db.session.commit()

    if _wants_json_response():
        return jsonify({"ok": True, "redirect": url_for("panel.profesionales")})

    flash("Profesional actualizado.", "success")
    return redirect(url_for("panel.profesionales"))


@panel_bp.post("/profesionales/<int:profesional_id>/toggle")
@login_required
def profesional_toggle(profesional_id):
    pelu_id = current_peluqueria_id()
    profesional = ProfesionalRepository.get_by_id(pelu_id, profesional_id)
    if not profesional:
        flash("Profesional no encontrado.", "error")
        return redirect(url_for("panel.profesionales"))
    profesional.activo = not profesional.activo
    db.session.commit()
    flash("Estado del profesional actualizado.", "success")
    return redirect(url_for("panel.profesionales"))


@panel_bp.post("/profesionales/<int:profesional_id>/eliminar")
@login_required
def profesional_eliminar(profesional_id):
    pelu_id = current_peluqueria_id()
    profesional = ProfesionalRepository.get_by_id(pelu_id, profesional_id)
    if not profesional:
        flash("Profesional no encontrado.", "error")
        return redirect(url_for("panel.profesionales"))

    reservas_futuras = ReservaRepository.count_future_confirmed(pelu_id, now_local())
    if reservas_futuras:
        flash(
            "No se puede eliminar este profesional porque hay reservas futuras confirmadas.",
            "error",
        )
        return redirect(url_for("panel.profesionales"))

    try:
        db.session.delete(profesional)
        db.session.commit()
        flash("Profesional eliminado.", "success")
    except Exception:
        current_app.logger.exception("No se pudo eliminar el profesional %s", profesional_id)
        db.session.rollback()
        flash("No se pudo eliminar el profesional.", "error")
    return redirect(url_for("panel.profesionales"))
