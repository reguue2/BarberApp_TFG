# Configuración principal de Flask.
#
# Registra modelos, blueprints, login y CSRF.

from flask import Flask, redirect, url_for
from flask_login import current_user

from app.bootstrap import init_database
from app.config import Config
from app.extensions import csrf, db, login_manager


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    _configure_login(app)
    _register_template_filters(app)
    _register_blueprints(app)

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("panel.dashboard"))
        return redirect(url_for("auth.login"))

    # En Docker deja la base lista al arrancar el contenedor.
    init_database(app)

    return app


def _configure_login(app):
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para acceder al panel."
    login_manager.login_message_category = "error"

    from app.repositories.usuario_admin_repository import UsuarioAdminRepository

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return UsuarioAdminRepository.get_by_id(int(user_id))
        except (ValueError, TypeError):
            return None


def _register_template_filters(app):
    from app.utils.phone_numbers import normalize_phone

    app.jinja_env.filters["phone_local"] = normalize_phone


def _register_blueprints(app):
    from app.auth.routes import auth_bp
    from app.panel import panel_bp
    from app.routes.health_routes import health_bp
    from app.routes.whatsapp_routes import whatsapp_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(panel_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(whatsapp_bp)

    # El webhook de WhatsApp lo llama Meta: nunca tiene CSRF token.
    csrf.exempt(whatsapp_bp)
