# Formatea fechas, servicios y reservas para los mensajes.

from app.bot.time_utils import hhmm


def format_date(fecha):
    return fecha.strftime("%d/%m/%Y")


def format_service(servicio):
    precio = f"{float(servicio.precio):.2f} €"
    return f"{servicio.nombre} · {servicio.duracion_min} min · {precio}"


def format_reservation(reserva):
    return (
        f"Servicio: {reserva.servicio.nombre}\n"
        f"Fecha: {format_date(reserva.fecha)}\n"
        f"Hora: {hhmm(reserva.hora)}"
    )
