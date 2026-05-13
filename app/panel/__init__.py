# Blueprint del panel web de gestión.

from flask import Blueprint


panel_bp = Blueprint(
    "panel",
    __name__,
    url_prefix="/panel",
    template_folder="templates",
    static_folder="static",
    static_url_path="/panel/static",
)

# Importa los módulos de rutas para registrarlos en el blueprint.
from app.panel import (  # noqa: E402, F401
    routes_dashboard,
    routes_reservas,
    routes_clientes,
    routes_servicios,
    routes_profesionales,
    routes_disponibilidad,
    routes_configuracion,
)
