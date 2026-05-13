# Listado, búsqueda, detalle, alta y eliminación de clientes.

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.forms.validators import clean_str, parse_phone
from app.models import Reserva
from app.panel import panel_bp
from app.panel.helpers import current_peluqueria, current_peluqueria_id, login_required, visual_estado
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.reserva_repository import ReservaRepository
from app.utils.datetime_utils import now_local
from app.utils.phone_numbers import normalize_phone


def _cliente_row_to_dict(row) -> dict:
    cliente, total_reservas, ultima_fecha = row
    return {
        "id": cliente.id,
        "nombre": cliente.nombre,
        "telefono": normalize_phone(cliente.telefono),
        "total_reservas": int(total_reservas or 0),
        "ultima_fecha": ultima_fecha.strftime("%d/%m/%Y") if ultima_fecha else None,
    }


def _cliente_form_errors(nombre: str, telefono: str | None, peluqueria_id: int) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not nombre or len(nombre) < 2:
        errors["nombre"] = "El nombre del cliente es obligatorio."
    if not telefono:
        errors["telefono"] = "El teléfono debe tener 9 cifras y empezar por 6, 7, 8 o 9."
    elif ClienteRepository.get_by_phone(peluqueria_id, telefono):
        errors["telefono"] = "Ya existe un cliente con ese teléfono."
    return errors


def _wants_json_response() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


@panel_bp.get("/clientes")
@login_required
def clientes():
    pelu = current_peluqueria()
    search = (request.args.get("q") or "").strip()
    rows = ClienteRepository.list_with_stats(pelu.id, search=search or None)

    if request.args.get("ajax") == "1" or _wants_json_response():
        return jsonify({"clientes": [_cliente_row_to_dict(row) for row in rows]})

    clientes_view = [
        {
            "cliente": row[0],
            "total_reservas": row[1],
            "ultima_fecha": row[2],
        }
        for row in rows
    ]
    return render_template(
        "panel/clientes.html",
        peluqueria=pelu,
        clientes=clientes_view,
        search=search,
    )


@panel_bp.get("/clientes/<int:cliente_id>")
@login_required
def cliente_detalle(cliente_id):
    pelu_id = current_peluqueria_id()
    cliente = ClienteRepository.get_by_id(pelu_id, cliente_id)
    if not cliente:
        return jsonify({"error": "not_found"}), 404

    reservas = ReservaRepository.list_by_client(pelu_id, cliente.id)
    items = [
        {
            "id": r.id,
            "fecha": r.fecha.strftime("%d/%m/%Y"),
            "hora": r.hora.strftime("%H:%M"),
            "servicio": r.servicio.nombre if r.servicio else "—",
            "estado": visual_estado(r),
        }
        for r in reservas
    ]
    return jsonify({
        "id": cliente.id,
        "nombre": cliente.nombre,
        "telefono": normalize_phone(cliente.telefono),
        "total_reservas": len(reservas),
        "reservas": items,
    })


@panel_bp.post("/clientes/nuevo")
@login_required
def cliente_nuevo():
    pelu_id = current_peluqueria_id()
    nombre = clean_str(request.form.get("nombre"), 100)
    telefono = parse_phone(request.form.get("telefono"))
    errors = _cliente_form_errors(nombre, telefono, pelu_id)

    if errors:
        if _wants_json_response():
            return jsonify({"ok": False, "errors": errors}), 400
        for message in errors.values():
            flash(message, "error")
        return redirect(url_for("panel.clientes"))

    ClienteRepository.create(pelu_id, telefono, nombre)
    db.session.commit()

    if _wants_json_response():
        return jsonify({"ok": True, "redirect": url_for("panel.clientes")}), 201

    flash("Cliente añadido.", "success")
    return redirect(url_for("panel.clientes"))


@panel_bp.post("/clientes/<int:cliente_id>/eliminar")
@login_required
def cliente_eliminar(cliente_id):
    pelu_id = current_peluqueria_id()
    cliente = ClienteRepository.get_by_id(pelu_id, cliente_id)
    if not cliente:
        flash("Cliente no encontrado.", "error")
        return redirect(url_for("panel.clientes"))

    futuras = ReservaRepository.count_future_confirmed_by_client(pelu_id, cliente.id, now_local())
    if futuras:
        flash(
            "No se puede eliminar este cliente porque tiene reserva(s) pendiente(s).",
            "error",
        )
        return redirect(url_for("panel.clientes"))

    try:
        # Si no hay reservas futuras, se permite borrar el cliente y su historial antiguo.
        Reserva.query.filter_by(peluqueria_id=pelu_id, cliente_id=cliente.id).delete(synchronize_session=False)
        db.session.delete(cliente)
        db.session.commit()
        flash("Cliente eliminado.", "success")
    except Exception:
        current_app.logger.exception("No se pudo eliminar el cliente %s", cliente_id)
        db.session.rollback()
        flash("No se pudo eliminar el cliente.", "error")
    return redirect(url_for("panel.clientes"))
