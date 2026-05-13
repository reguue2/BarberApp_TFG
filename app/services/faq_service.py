# Prepara el contexto de la peluquería para responder dudas.

from app.integrations.openai_client import OpenAIClient
from app.repositories.horario_repository import HorarioRepository
from app.repositories.servicio_repository import ServicioRepository
from app.utils.datetime_utils import today_local


DIAS_NOMBRE = {
    1: "lunes",
    2: "martes",
    3: "miércoles",
    4: "jueves",
    5: "viernes",
    6: "sábado",
    7: "domingo",
}


class FAQService:
    def __init__(self, openai_client: OpenAIClient | None = None):
        self.openai_client = openai_client

    def answer(self, peluqueria, question: str) -> str:
        context = self._build_context(peluqueria)
        client = self.openai_client or OpenAIClient()
        answer = client.answer_faq(question, context)
        if answer:
            return answer

        telefono = peluqueria.telefono_peluqueria or "la peluquería"
        return f"Ahora mismo no puedo responder esa duda con seguridad. Puedes contactar con {telefono}."

    def _build_context(self, peluqueria) -> str:
        servicios = ServicioRepository.list_active_by_peluqueria(peluqueria.id)
        cerrados = HorarioRepository.list_next_closed_days(peluqueria.id, today_local())

        lines = [
            f"Nombre: {peluqueria.nombre}",
            f"Dirección: {peluqueria.direccion or 'No indicada'}",
            f"Teléfono: {peluqueria.telefono_peluqueria or 'No indicado'}",
            f"Información: {peluqueria.info or 'No indicada'}",
            "",
            "Servicios activos:",
        ]
        for servicio in servicios:
            precio = f"{float(servicio.precio):.2f} €"
            lines.append(f"- {servicio.nombre}: {servicio.descripcion or 'Sin descripción'}, {servicio.duracion_min} min, {precio}")

        lines.append("")
        lines.append("Horarios:")
        for dia in range(1, 8):
            tramos = HorarioRepository.list_active_for_weekday(peluqueria.id, dia)
            if tramos:
                txt = ", ".join(f"{t.hora_inicio.strftime('%H:%M')}-{t.hora_fin.strftime('%H:%M')}" for t in tramos)
                lines.append(f"- {DIAS_NOMBRE[dia]}: {txt}")

        if cerrados:
            lines.append("")
            lines.append("Días cerrados próximos:")
            for cerrado in cerrados:
                motivo = f" ({cerrado.motivo})" if cerrado.motivo else ""
                lines.append(f"- {cerrado.fecha.strftime('%d/%m/%Y')}{motivo}")
        return "\n".join(lines)
