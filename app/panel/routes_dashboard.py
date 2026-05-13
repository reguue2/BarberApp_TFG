# Vista principal del panel con KPIs y métricas de negocio.
#
# Métricas incluidas:
# - KPIs (reservas de hoy, próximas, clientes, servicios y profesionales activos).
# - Banner llamativo SOLO si el bot de WhatsApp no está configurado.
# - Reservas por canal: cuánto valor aporta el bot vs el panel.
# - Servicios más reservados: inteligencia básica de negocio.
# - Próximos días cerrados: ayuda operativa para no olvidarlos.

from datetime import timedelta

from flask import render_template

from app.models import Cliente
from app.panel import panel_bp
from app.panel.helpers import current_peluqueria, login_required
from app.repositories.horario_repository import HorarioRepository
from app.repositories.profesional_repository import ProfesionalRepository
from app.repositories.reserva_repository import ReservaRepository
from app.repositories.servicio_repository import ServicioRepository
from app.utils.datetime_utils import today_local


@panel_bp.get("/")
@panel_bp.get("/dashboard")
@login_required
def dashboard():
    pelu = current_peluqueria()
    hoy = today_local()

    stats = {
        "reservas_hoy": ReservaRepository.count_confirmed_today(pelu.id, hoy),
        "proximas_reservas": ReservaRepository.count_confirmed_upcoming(
            pelu.id, hoy + timedelta(days=1)
        ),
        "clientes_registrados": Cliente.query.filter_by(peluqueria_id=pelu.id).count(),
        "servicios_activos": ServicioRepository.count_active(pelu.id),
        "profesionales_activos": ProfesionalRepository.count_active_by_peluqueria(pelu.id),
    }

    # --- Reservas por canal ---
    canal_rows = ReservaRepository.count_confirmed_by_origen(pelu.id)
    canal_dict = {origen: count for origen, count in canal_rows}
    wa_count = canal_dict.get("whatsapp", 0)
    panel_count = canal_dict.get("panel", 0)
    total_canal = wa_count + panel_count

    canales = []
    if total_canal:
        canales = [
            {"nombre": "WhatsApp", "key": "whatsapp", "count": wa_count,
             "pct": round(wa_count / total_canal * 100, 1)},
            {"nombre": "Panel", "key": "panel", "count": panel_count,
             "pct": round(panel_count / total_canal * 100, 1)},
        ]

    # --- Top servicios más reservados ---
    top_rows = ReservaRepository.top_servicios_confirmados(pelu.id, limite=5)
    total_top = sum(count for _, _, count in top_rows) or 1
    top_servicios = [
        {"id": sid, "nombre": nombre, "count": count,
         "pct": round(count / total_top * 100, 1)}
        for sid, nombre, count in top_rows
    ]

    # --- Próximos días cerrados ---
    proximos_cerrados = HorarioRepository.list_next_closed_days(pelu.id, hoy, limite=5)

    return render_template(
        "panel/dashboard.html",
        peluqueria=pelu,
        stats=stats,
        canales=canales,
        total_canal=total_canal,
        top_servicios=top_servicios,
        proximos_cerrados=proximos_cerrados,
        hoy=hoy,
    )
