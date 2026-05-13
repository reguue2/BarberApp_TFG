# Configuración general de la peluquería y datos de la cuenta.

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.validators import clean_str, parse_email, parse_int, parse_phone
from app.models import Peluqueria
from app.panel import panel_bp
from app.panel.helpers import current_peluqueria, login_required
from app.repositories.usuario_admin_repository import UsuarioAdminRepository


def _render_configuracion(errors=None, form_data=None, status_code: int = 200):
    return (
        render_template(
            "panel/configuracion.html",
            peluqueria=current_peluqueria(),
            errors=errors or {},
            form_data=form_data or {},
        ),
        status_code,
    )


@panel_bp.get("/configuracion")
@login_required
def configuracion():
    return render_template(
        "panel/configuracion.html",
        peluqueria=current_peluqueria(),
        errors={},
        form_data={},
    )


@panel_bp.post("/configuracion/negocio")
@login_required
def configuracion_guardar_negocio():
    pelu = current_peluqueria()
    form = {
        "nombre": clean_str(request.form.get("nombre"), 100),
        "direccion": clean_str(request.form.get("direccion"), 150),
        "telefono_peluqueria": request.form.get("telefono_peluqueria") or "",
        "info": clean_str(request.form.get("info"), 500),
    }
    telefono = parse_phone(form["telefono_peluqueria"]) if form["telefono_peluqueria"].strip() else None
    errors = {}

    if not form["nombre"] or len(form["nombre"]) < 2:
        errors["nombre"] = "El nombre del negocio es obligatorio."
    if form["telefono_peluqueria"].strip() and not telefono:
        errors["telefono_peluqueria"] = "El teléfono del negocio debe tener 9 cifras."

    if errors:
        return _render_configuracion(
            errors={"negocio": errors},
            form_data={"negocio": form},
            status_code=400,
        )

    pelu.nombre = form["nombre"]
    pelu.direccion = form["direccion"] or None
    pelu.telefono_peluqueria = telefono or None
    pelu.info = form["info"] or None
    db.session.commit()

    flash("Datos del negocio guardados.", "success")
    return redirect(url_for("panel.configuracion"))


@panel_bp.post("/configuracion/cuenta")
@login_required
def configuracion_guardar_cuenta():
    usuario = current_user
    form = {
        "usuario_nombre": clean_str(request.form.get("usuario_nombre"), 100),
        "email": (request.form.get("email") or "").strip().lower(),
    }
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    new_password_confirm = request.form.get("new_password_confirm") or ""
    wants_password_change = bool(current_password or new_password or new_password_confirm)
    errors = {}

    if not form["usuario_nombre"] or len(form["usuario_nombre"]) < 2:
        errors["usuario_nombre"] = "Introduce tu nombre."

    email = parse_email(form["email"])
    if not email:
        errors["email"] = "Introduce un email válido."
    else:
        existing = UsuarioAdminRepository.get_by_email(email)
        if existing and existing.id != usuario.id:
            errors["email"] = "Ya existe una cuenta con ese email."
        form["email"] = email

    if wants_password_change:
        if not current_password:
            errors["current_password"] = "Introduce tu contraseña actual."
        elif not usuario.check_password(current_password):
            errors["current_password"] = "La contraseña actual no es correcta."

        if len(new_password) < 8:
            errors["new_password"] = "La nueva contraseña debe tener al menos 8 caracteres."

        if not new_password_confirm:
            errors["new_password_confirm"] = "Repite la nueva contraseña."
        elif new_password != new_password_confirm:
            errors["new_password_confirm"] = "Las contraseñas no coinciden."

    if errors:
        return _render_configuracion(
            errors={"cuenta": errors},
            form_data={"cuenta": form},
            status_code=400,
        )

    usuario.nombre = form["usuario_nombre"]
    usuario.email = form["email"]
    if wants_password_change:
        usuario.set_password(new_password)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        errors["email"] = "Ya existe una cuenta con ese email."
        return _render_configuracion(
            errors={"cuenta": errors},
            form_data={"cuenta": form},
            status_code=400,
        )

    flash("Datos de la cuenta guardados.", "success")
    return redirect(url_for("panel.configuracion"))


@panel_bp.post("/configuracion/reservas")
@login_required
def configuracion_guardar_reservas():
    pelu = current_peluqueria()
    form = {"rango_reservas_min": request.form.get("rango_reservas_min") or ""}
    rango = parse_int(form["rango_reservas_min"], minimum=5, maximum=240)
    errors = {}

    if rango is None:
        errors["rango_reservas_min"] = "Rango de reservas inválido."

    if errors:
        return _render_configuracion(
            errors={"reservas": errors},
            form_data={"reservas": form},
            status_code=400,
        )

    pelu.rango_reservas_min = rango
    db.session.commit()

    flash("Parámetros de reservas guardados.", "success")
    return redirect(url_for("panel.configuracion"))


@panel_bp.post("/configuracion/whatsapp")
@login_required
def configuracion_guardar_whatsapp():
    pelu = current_peluqueria()
    form = {
        "wa_phone_number_id": clean_str(request.form.get("wa_phone_number_id"), 64),
        "wa_business_id": clean_str(request.form.get("wa_business_id"), 64),
    }
    wa_phone_number_id = form["wa_phone_number_id"] or None
    wa_business_id = form["wa_business_id"] or None
    errors = {}

    if wa_phone_number_id:
        owner = Peluqueria.query.filter_by(wa_phone_number_id=wa_phone_number_id).first()
        if owner and owner.id != pelu.id:
            errors["wa_phone_number_id"] = "Ese WhatsApp Phone Number ID ya está en uso."

    if errors:
        return _render_configuracion(
            errors={"whatsapp": errors},
            form_data={"whatsapp": form},
            status_code=400,
        )

    pelu.wa_phone_number_id = wa_phone_number_id
    pelu.wa_business_id = wa_business_id

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        errors["wa_phone_number_id"] = "Ese WhatsApp Phone Number ID ya está en uso."
        return _render_configuracion(
            errors={"whatsapp": errors},
            form_data={"whatsapp": form},
            status_code=400,
        )

    flash("Configuración de WhatsApp guardada.", "success")
    return redirect(url_for("panel.configuracion"))
