# Crea la base de datos y mete datos de ejemplo si está vacía.

import calendar
import logging
import time as sleep_time
from datetime import time, timedelta
from decimal import Decimal

from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    Cliente,
    DiaCerrado,
    HorarioApertura,
    Peluqueria,
    Profesional,
    Reserva,
    Servicio,
    UsuarioAdmin,
)
from app.utils.datetime_utils import today_local


def init_database(app):
    if not app.config.get("AUTO_INIT_DB", True):
        return

    # MySQL tarda unos segundos en arrancar cuando se levanta Docker.
    for attempt in range(1, 31):
        try:
            with app.app_context():
                db.create_all()
                _seed_if_empty()
            logging.info("Base de datos preparada.")
            return
        except OperationalError:
            if attempt == 30:
                raise
            sleep_time.sleep(2)


def _seed_if_empty():
    # Si ya existe una peluquería, no tocamos nada para no duplicar datos.
    if Peluqueria.query.first():
        return

    fecha_inicio, fecha_fin = _rango_reservas_demo()

    pelu1 = Peluqueria(
        nombre="Peluquería Centro",
        direccion="Calle Mayor 12",
        telefono_peluqueria="948000111",
        info="Peluquería unisex especializada en cortes, barba, color y peinados.",
        rango_reservas_min=30,
        wa_phone_number_id="111111111111111",
        wa_business_id="222222222222222",
    )
    pelu2 = Peluqueria(
        nombre="Barbería Norte",
        direccion="Avenida Norte 8",
        telefono_peluqueria="948000222",
        info="Barbería enfocada en corte masculino, degradados y arreglo de barba.",
        rango_reservas_min=30,
        wa_phone_number_id="333333333333333",
        wa_business_id="444444444444444",
    )

    db.session.add_all([pelu1, pelu2])
    db.session.flush()

    db.session.add_all([
        UsuarioAdmin(
            peluqueria=pelu1,
            nombre="Admin Centro",
            email="centro@example.com",
            password_hash=generate_password_hash("admin123"),
        ),
        UsuarioAdmin(
            peluqueria=pelu2,
            nombre="Admin Norte",
            email="norte@example.com",
            password_hash=generate_password_hash("admin123"),
        ),
    ])

    profesionales_pelu1 = ["Laura", "Marta", "Sergio", "Nerea"]
    profesionales_pelu2 = ["Iván", "Raúl", "Carlos"]
    db.session.add_all([
        Profesional(peluqueria=pelu1, nombre=nombre, activo=True)
        for nombre in profesionales_pelu1
    ])
    db.session.add_all([
        Profesional(peluqueria=pelu2, nombre=nombre, activo=True)
        for nombre in profesionales_pelu2
    ])

    servicios_pelu1 = [
        _servicio(pelu1, "Corte de pelo", "Corte y peinado básico", "12.00", 30),
        _servicio(pelu1, "Corte infantil", "Corte para niños", "10.00", 30),
        _servicio(pelu1, "Barba", "Arreglo de barba", "8.00", 20),
        _servicio(pelu1, "Lavado y peinado", "Lavado con peinado final", "16.00", 30),
        _servicio(pelu1, "Tinte raíz", "Retoque de raíz", "28.00", 60),
        _servicio(pelu1, "Tinte completo", "Coloración completa", "35.00", 90),
        _servicio(pelu1, "Mechas", "Mechas y matizado", "55.00", 120),
        _servicio(pelu1, "Tratamiento hidratante", "Tratamiento capilar hidratante", "22.00", 45),
        _servicio(pelu1, "Recogido sencillo", "Recogido para evento", "30.00", 60),
    ]
    servicios_pelu2 = [
        _servicio(pelu2, "Corte masculino", "Corte clásico o degradado", "14.00", 30),
        _servicio(pelu2, "Degradado", "Degradado con acabado", "16.00", 30),
        _servicio(pelu2, "Barba premium", "Arreglo de barba con acabado", "10.00", 30),
        _servicio(pelu2, "Afeitado clásico", "Afeitado con toalla caliente", "12.00", 30),
        _servicio(pelu2, "Corte y barba", "Servicio combinado", "22.00", 60),
        _servicio(pelu2, "Diseño de barba", "Perfilado y diseño de barba", "15.00", 45),
        _servicio(pelu2, "Arreglo express", "Repaso rápido de laterales", "9.00", 20),
        _servicio(pelu2, "Tratamiento capilar", "Tratamiento básico para cuero cabelludo", "18.00", 45),
    ]
    db.session.add_all(servicios_pelu1 + servicios_pelu2)

    clientes_pelu1 = _crear_clientes(pelu1, 90, "61010")
    clientes_pelu2 = _crear_clientes(pelu2, 75, "62020")
    db.session.add_all(clientes_pelu1 + clientes_pelu2)

    _crear_horarios(pelu1, pelu2)

    cierres_pelu1 = _crear_dias_cerrados(
        pelu1,
        fecha_inicio,
        fecha_fin,
        [18, 36, 51],
        {1, 2, 3, 4, 5, 6},
    )
    cierres_pelu2 = _crear_dias_cerrados(
        pelu2,
        fecha_inicio,
        fecha_fin,
        [12, 29, 47],
        {1, 2, 3, 4, 5},
    )

    db.session.flush()

    _crear_reservas_demo(
        peluqueria=pelu1,
        clientes=clientes_pelu1,
        servicios=servicios_pelu1,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        fechas_cerradas=cierres_pelu1,
        slots_por_dia={
            1: _slots_peluqueria_centro_laborable(),
            2: _slots_peluqueria_centro_laborable(),
            3: _slots_peluqueria_centro_laborable(),
            4: _slots_peluqueria_centro_laborable(),
            5: _slots_peluqueria_centro_laborable(),
            6: _slots_peluqueria_centro_sabado(),
        },
        hora_cierre_tarde="20:00",
    )
    _crear_reservas_demo(
        peluqueria=pelu2,
        clientes=clientes_pelu2,
        servicios=servicios_pelu2,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        fechas_cerradas=cierres_pelu2,
        slots_por_dia={
            1: _slots_barberia_norte_laborable(),
            2: _slots_barberia_norte_laborable(),
            3: _slots_barberia_norte_laborable(),
            4: _slots_barberia_norte_laborable(),
            5: _slots_barberia_norte_laborable(),
        },
        hora_cierre_tarde="19:00",
    )

    db.session.commit()


def _servicio(peluqueria, nombre, descripcion, precio, duracion_min):
    return Servicio(
        peluqueria=peluqueria,
        nombre=nombre,
        descripcion=descripcion,
        precio=Decimal(precio),
        duracion_min=duracion_min,
        activo=True,
    )


def _crear_clientes(peluqueria, total, prefijo_telefono):
    nombres = [
        "Ana", "María", "Lucía", "Paula", "Carmen", "Elena", "Sofía", "Nerea", "Laura",
        "Marta", "Sara", "Claudia", "Irene", "Alba", "Julia", "Noa", "Ainhoa", "Valeria",
        "Diego", "Pablo", "Javier", "Sergio", "Raúl", "Iván", "Álvaro", "Hugo", "Mario",
        "Carlos", "Daniel", "Adrián", "David", "Manuel", "Óscar", "Miguel", "Rubén",
    ]
    apellidos = [
        "García", "Martínez", "López", "Sánchez", "Pérez", "Gómez", "Fernández",
        "Ruiz", "Díaz", "Moreno", "Álvarez", "Romero", "Navarro", "Torres", "Ortega",
        "Castro", "Serrano", "Molina", "Iglesias", "Vega", "Cano", "Medina", "Gil",
    ]

    clientes = []
    for indice in range(1, total + 1):
        nombre = nombres[(indice - 1) % len(nombres)]
        apellido = apellidos[(indice * 3) % len(apellidos)]
        clientes.append(
            Cliente(
                peluqueria=peluqueria,
                nombre=f"{nombre} {apellido}",
                telefono=f"{prefijo_telefono}{indice:04d}",
            )
        )
    return clientes


def _crear_horarios(pelu1, pelu2):
    for dia in range(1, 6):
        _add_horario(pelu1, dia, "09:00", "14:00")
        _add_horario(pelu1, dia, "16:00", "20:00")
        _add_horario(pelu2, dia, "10:00", "14:00")
        _add_horario(pelu2, dia, "16:00", "19:00")
    _add_horario(pelu1, 6, "09:00", "14:00")


def _crear_dias_cerrados(peluqueria, fecha_inicio, fecha_fin, offsets, dias_validos):
    fechas_cerradas = set()
    for offset in offsets:
        fecha = _siguiente_dia_valido(fecha_inicio + timedelta(days=offset), fecha_fin, dias_validos)
        if fecha and fecha not in fechas_cerradas:
            fechas_cerradas.add(fecha)
            db.session.add(
                DiaCerrado(
                    peluqueria=peluqueria,
                    fecha=fecha,
                    motivo="Cierre de prueba",
                )
            )
    return fechas_cerradas


def _siguiente_dia_valido(fecha_base, fecha_fin, dias_validos):
    fecha = fecha_base
    while fecha <= fecha_fin:
        if fecha.weekday() + 1 in dias_validos:
            return fecha
        fecha += timedelta(days=1)
    return None


def _crear_reservas_demo(
    peluqueria,
    clientes,
    servicios,
    fecha_inicio,
    fecha_fin,
    fechas_cerradas,
    slots_por_dia,
    hora_cierre_tarde,
):
    fecha = fecha_inicio
    contador = 0

    while fecha <= fecha_fin:
        dia_semana = fecha.weekday() + 1
        slots = slots_por_dia.get(dia_semana, [])

        if fecha not in fechas_cerradas and slots:
            for posicion, hora_txt in enumerate(slots):
                servicio = _elegir_servicio(servicios, hora_txt, hora_cierre_tarde, contador + posicion)
                cliente = clientes[(contador * 7 + posicion * 5) % len(clientes)]

                db.session.add(
                    Reserva(
                        peluqueria=peluqueria,
                        cliente=cliente,
                        servicio=servicio,
                        fecha=fecha,
                        hora=time.fromisoformat(hora_txt),
                        estado=_estado_reserva(contador, posicion),
                        origen="whatsapp" if (contador + posicion) % 3 else "panel",
                    )
                )
                contador += 1

        fecha += timedelta(days=1)


def _elegir_servicio(servicios, hora_txt, hora_cierre_tarde, indice):
    inicio_min = _to_min(hora_txt)
    cierre_min = _to_min("14:00") if inicio_min < _to_min("15:00") else _to_min(hora_cierre_tarde)
    servicios_validos = [
        servicio for servicio in servicios
        if inicio_min + int(servicio.duracion_min) <= cierre_min
    ]
    return servicios_validos[indice % len(servicios_validos)]


def _estado_reserva(contador, posicion):
    # Dejamos algunas canceladas para que el panel muestre histórico realista.
    if (contador + posicion) % 13 == 0:
        return "cancelada"
    return "confirmada"


def _slots_peluqueria_centro_laborable():
    return [
        "09:00", "09:30", "10:00", "10:00", "10:30", "11:00", "11:30", "12:00",
        "12:30", "13:00", "16:00", "16:30", "17:00", "17:00", "17:30", "18:00",
        "18:30", "19:00",
    ]


def _slots_peluqueria_centro_sabado():
    return [
        "09:00", "09:30", "10:00", "10:00", "10:30", "11:00", "11:30", "12:00",
        "12:30", "13:00",
    ]


def _slots_barberia_norte_laborable():
    return [
        "10:00", "10:30", "11:00", "11:00", "11:30", "12:00", "12:30", "13:00",
        "16:00", "16:30", "17:00", "17:30", "18:00", "18:30",
    ]


def _rango_reservas_demo():
    hoy = today_local()
    fecha_inicio = hoy.replace(day=1)
    siguiente_mes = _sumar_meses(fecha_inicio, 1)
    ultimo_dia = calendar.monthrange(siguiente_mes.year, siguiente_mes.month)[1]
    fecha_fin = siguiente_mes.replace(day=min(30, ultimo_dia))
    return fecha_inicio, fecha_fin


def _sumar_meses(fecha, meses):
    mes = fecha.month - 1 + meses
    year = fecha.year + mes // 12
    month = mes % 12 + 1
    day = min(fecha.day, calendar.monthrange(year, month)[1])
    return fecha.replace(year=year, month=month, day=day)


def _to_min(hora_txt):
    hora = time.fromisoformat(hora_txt)
    return hora.hour * 60 + hora.minute


def _add_horario(peluqueria, dia, inicio, fin):
    db.session.add(
        HorarioApertura(
            peluqueria=peluqueria,
            dia_semana=dia,
            hora_inicio=time.fromisoformat(inicio),
            hora_fin=time.fromisoformat(fin),
            activo=True,
        )
    )
