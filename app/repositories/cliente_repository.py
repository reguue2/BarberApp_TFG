# Consultas y altas de clientes.

from sqlalchemy import func, or_

from app.extensions import db
from app.models import Cliente, Reserva
from app.utils.phone_numbers import normalize_phone


class ClienteRepository:
    @staticmethod
    def get_by_phone(peluqueria_id: int, telefono: str):
        telefono_normalizado = normalize_phone(telefono)
        if not telefono_normalizado:
            return None

        candidatos = {telefono_normalizado}
        if len(telefono_normalizado) == 9:
            # Compatibilidad con clientes guardados antes con prefijo español.
            candidatos.add(f"34{telefono_normalizado}")

        return Cliente.query.filter(
            Cliente.peluqueria_id == peluqueria_id,
            Cliente.telefono.in_(candidatos),
        ).first()

    @staticmethod
    def get_by_id(peluqueria_id: int, cliente_id: int):
        return Cliente.query.filter_by(id=cliente_id, peluqueria_id=peluqueria_id).first()

    @staticmethod
    def create(peluqueria_id: int, telefono: str, nombre: str):
        cliente = Cliente(
            peluqueria_id=peluqueria_id,
            telefono=telefono,
            nombre=nombre.strip(),
        )
        db.session.add(cliente)
        return cliente

    @staticmethod
    def get_or_create(peluqueria_id: int, telefono: str, nombre: str):
        cliente = ClienteRepository.get_by_phone(peluqueria_id, telefono)
        if cliente:
            return cliente, False
        return ClienteRepository.create(peluqueria_id, telefono, nombre), True


    @staticmethod
    def search_for_reservation(peluqueria_id: int, search: str, field: str | None = None, limit: int = 8):
        """Busca clientes para el autocompletado del modal de reservas.

        field permite priorizar el patrón según el input usado: nombre o teléfono.
        No devuelve todos los clientes si el patrón está vacío o es demasiado corto.
        """
        raw_search = (search or "").strip()
        if len(raw_search) < 2:
            return []

        field = field if field in {"nombre", "telefono"} else None
        query = Cliente.query.filter(Cliente.peluqueria_id == peluqueria_id)

        filters = []
        if field in {None, "nombre"}:
            filters.append(Cliente.nombre.ilike(f"%{raw_search}%"))

        if field in {None, "telefono"}:
            filters.append(Cliente.telefono.ilike(f"%{raw_search}%"))
            phone_term = normalize_phone(raw_search)
            if phone_term:
                filters.append(Cliente.telefono.ilike(f"%{phone_term}%"))
                if len(phone_term) == 9:
                    filters.append(Cliente.telefono.ilike(f"%34{phone_term}%"))

        if not filters:
            return []

        return (
            query.filter(or_(*filters))
            .order_by(Cliente.nombre.asc(), Cliente.telefono.asc())
            .limit(limit)
            .all()
        )

    # ---- Solo panel ----

    @staticmethod
    def list_with_stats(peluqueria_id: int, search: str | None = None):
        """Lista clientes de la peluquería con número de reservas y última reserva."""
        last_date_subq = (
            db.session.query(
                Reserva.cliente_id,
                func.max(Reserva.fecha).label("ultima_fecha"),
            )
            .filter(Reserva.peluqueria_id == peluqueria_id)
            .group_by(Reserva.cliente_id)
            .subquery()
        )
        count_subq = (
            db.session.query(
                Reserva.cliente_id,
                func.count(Reserva.id).label("total_reservas"),
            )
            .filter(Reserva.peluqueria_id == peluqueria_id)
            .group_by(Reserva.cliente_id)
            .subquery()
        )

        query = (
            db.session.query(
                Cliente,
                func.coalesce(count_subq.c.total_reservas, 0).label("total_reservas"),
                last_date_subq.c.ultima_fecha,
            )
            .outerjoin(count_subq, count_subq.c.cliente_id == Cliente.id)
            .outerjoin(last_date_subq, last_date_subq.c.cliente_id == Cliente.id)
            .filter(Cliente.peluqueria_id == peluqueria_id)
        )

        if search:
            raw_search = search.strip()
            term = f"%{raw_search}%"
            phone_term = normalize_phone(raw_search)
            filters = [Cliente.nombre.ilike(term), Cliente.telefono.ilike(term)]
            if phone_term:
                filters.append(Cliente.telefono.ilike(f"%{phone_term}%"))
                if len(phone_term) == 9:
                    filters.append(Cliente.telefono.ilike(f"%34{phone_term}%"))
            query = query.filter(or_(*filters))

        return query.order_by(Cliente.nombre.asc()).all()
