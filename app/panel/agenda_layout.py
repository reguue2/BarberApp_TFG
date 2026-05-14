# Cálculos visuales de la agenda diaria.
#
# Aquí vive la lógica que hace que la agenda parezca un calendario:
#   - Detectar reservas que se solapan en el tiempo.
#   - Asignar columnas horizontales a esas reservas solapadas.
#   - Convertir minutos a píxeles usando el rango de reservas configurado.

from app.bot.time_utils import from_min


# Si la peluquería cambia el rango, la escala se adapta proporcionalmente
UNIT_HEIGHT_PX = 60
MIN_EVENT_HEIGHT_PX = 28


def reservations_overlap(start_a, dur_a, start_b, dur_b):
    """Devuelve True si los intervalos [start_a, start_a+dur_a) y
    [start_b, start_b+dur_b) se solapan en el tiempo.
    Tocarse en el borde (una termina cuando la otra empieza) NO cuenta.
    """
    return start_a < (start_b + dur_b) and start_b < (start_a + dur_a)


def assign_overlap_columns(items):
    """Asigna columnas horizontales a una lista de reservas que pueden solaparse."""
    if not items:
        return []

    # Trabajamos sobre una copia anotada con el índice original para poder
    # devolver el resultado en el mismo orden de entrada.
    indexed = [dict(item, _idx=i) for i, item in enumerate(items)]
    sorted_items = sorted(indexed, key=lambda it: (it["start_min"], -it["dur_min"]))

    # 1) Agrupar en clusters mediante un barrido por hora de inicio.
    clusters = []
    current = []
    current_end = -1
    for it in sorted_items:
        end = it["start_min"] + it["dur_min"]
        if current and it["start_min"] < current_end:
            current.append(it)
            current_end = max(current_end, end)
        else:
            if current:
                clusters.append(current)
            current = [it]
            current_end = end
    if current:
        clusters.append(current)

    # 2) Para cada cluster, reutilizamos columnas que ya han quedado libres.
    by_original_idx = {}
    for cluster in clusters:
        col_ends = []  # final (en minutos) de la última reserva de cada columna.
        assigned_pairs = []
        for it in cluster:
            chosen = None
            for col_i, col_end in enumerate(col_ends):
                if col_end <= it["start_min"]:
                    chosen = col_i
                    col_ends[col_i] = it["start_min"] + it["dur_min"]
                    break
            if chosen is None:
                col_ends.append(it["start_min"] + it["dur_min"])
                chosen = len(col_ends) - 1
            assigned_pairs.append((it, chosen))

        total_cols = len(col_ends)
        for it, col in assigned_pairs:
            result = {k: v for k, v in it.items() if k != "_idx"}
            result["col"] = col
            result["cols"] = total_cols
            by_original_idx[it["_idx"]] = result

    return [by_original_idx[i] for i in range(len(items))]


def build_tramo_layout(tramo_start_min, tramo_end_min, reservas, unit_min):
    """Construye los datos visuales de un tramo horario para el template."""
    
    safe_unit = unit_min if unit_min and unit_min > 0 else 30
    px_per_min = UNIT_HEIGHT_PX / safe_unit

    dentro_del_tramo = [
        {"start_min": r["start_min"], "dur_min": r["dur_min"], "payload": r["payload"]}
        for r in reservas
        if tramo_start_min <= r["start_min"] < tramo_end_min
    ]

    eventos = assign_overlap_columns(dentro_del_tramo)
    for ev in eventos:
        ev["top_px"] = int(round((ev["start_min"] - tramo_start_min) * px_per_min))
        ev["height_px"] = max(
            MIN_EVENT_HEIGHT_PX,
            int(round(ev["dur_min"] * px_per_min)),
        )
    duracion_tramo = max(0, tramo_end_min - tramo_start_min)
    n_unidades = max(1, duracion_tramo // safe_unit)
    gridlines = []
    for i in range(n_unidades + 1):
        minuto = tramo_start_min + i * safe_unit
        gridlines.append({
            "minute": minuto,
            "label": from_min(minuto),
            "is_hour": minuto % 60 == 0,
            "top_px": i * UNIT_HEIGHT_PX,
        })

    return {
        "start_min": tramo_start_min,
        "end_min": tramo_end_min,
        "start_label": from_min(tramo_start_min),
        "end_label": from_min(tramo_end_min),
        "height_px": int(round(duracion_tramo * px_per_min)),
        "gridlines": gridlines,
        "reservas": eventos,
    }
