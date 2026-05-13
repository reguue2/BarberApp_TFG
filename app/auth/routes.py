# Rutas de login, registro y logout para el panel.

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.validators import clean_str, parse_email
from app.models import Peluqueria, UsuarioAdmin
from app.repositories.usuario_admin_repository import UsuarioAdminRepository


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("panel.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        errors = {}

        if not parse_email(email):
            errors["email"] = "Introduce un email válido."
        if not password:
            errors["password"] = "Introduce tu contraseña."

        if errors:
            return render_template("panel/login.html", email=email, errors=errors), 400

        usuario = UsuarioAdminRepository.get_by_email(email)
        if not usuario or not usuario.activo or not usuario.check_password(password):
            errors["password"] = "Email o contraseña incorrectos."
            return render_template("panel/login.html", email=email, errors=errors), 401

        login_user(usuario)
        return redirect(url_for("panel.dashboard"))

    return render_template("panel/login.html", errors={})


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("panel.dashboard"))

    if request.method == "POST":
        form = {
            "nombre": clean_str(request.form.get("nombre"), 100),
            "nombre_peluqueria": clean_str(request.form.get("nombre_peluqueria"), 100),
            "email": (request.form.get("email") or "").strip().lower(),
        }
        password = request.form.get("password") or ""
        password_confirm = request.form.get("password_confirm") or ""
        errors = _validate_registro(form, password, password_confirm)

        if errors:
            return render_template("panel/registro.html", form=form, errors=errors), 400

        peluqueria = Peluqueria(nombre=form["nombre_peluqueria"], rango_reservas_min=30)
        usuario = UsuarioAdmin(
            peluqueria=peluqueria,
            nombre=form["nombre"],
            email=form["email"],
            activo=True,
        )
        usuario.set_password(password)

        db.session.add_all([peluqueria, usuario])
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            errors["email"] = "Ya existe una cuenta con ese email."
            return render_template("panel/registro.html", form=form, errors=errors), 400

        login_user(usuario)
        return redirect(url_for("panel.dashboard"))

    return render_template("panel/registro.html", form={}, errors={})


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def _validate_registro(form: dict, password: str, password_confirm: str) -> dict:
    errors = {}

    if not form["nombre"] or len(form["nombre"]) < 2:
        errors["nombre"] = "Introduce tu nombre."

    if not form["nombre_peluqueria"] or len(form["nombre_peluqueria"]) < 2:
        errors["nombre_peluqueria"] = "Introduce el nombre de la peluquería."

    email = parse_email(form["email"])
    if not email:
        errors["email"] = "Introduce un email válido."
    elif UsuarioAdminRepository.get_by_email(email):
        errors["email"] = "Ya existe una cuenta con ese email."
    else:
        form["email"] = email

    if len(password) < 8:
        errors["password"] = "La contraseña debe tener al menos 8 caracteres."

    if not password_confirm:
        errors["password_confirm"] = "Repite la contraseña."
    elif password and password_confirm != password:
        errors["password_confirm"] = "Las contraseñas no coinciden."

    return errors
