# BarberApp

BarberApp es una plataforma multi-tenant para gestionar reservas de peluquerías. El proyecto combina un panel web para el administrador de cada peluquería y un bot de WhatsApp para que los clientes puedan reservar o cancelar citas.

La idea principal es sencilla: **MySQL es la fuente de verdad**. El panel y el bot usan los mismos modelos, repositorios y servicios de negocio. Así, una reserva se valida igual si nace desde el panel o desde WhatsApp.

## Funcionalidades principales

- Registro y login de administrador de peluquería.
- Aislamiento multi-tenant por `peluqueria_id`.
- Gestión de clientes.
- Gestión de servicios con precio, duración y estado activo/inactivo.
- Gestión de profesionales, usados como capacidad de reservas simultáneas.
- Configuración de horario semanal y días cerrados.
- Creación y cancelación de reservas desde el panel.
- Reserva y cancelación desde WhatsApp Cloud API.
- Uso de OpenAI como apoyo para interpretar fechas, nombres y dudas. OpenAI no decide si una reserva se guarda o no; eso lo valida la lógica de negocio contra MySQL.

## Arquitectura

```text
Administrador
  -> Panel Flask/Jinja
  -> Rutas del panel
  -> Servicios de aplicación
  -> Repositorios
  -> MySQL

Cliente
  -> WhatsApp Cloud API
  -> Webhook Flask
  -> Servicio conversacional
  -> Servicios de aplicación
  -> Repositorios
  -> MySQL
```

Piezas principales:

- `app/models/`: modelos SQLAlchemy.
- `app/repositories/`: consultas y operaciones de acceso a datos.
- `app/services/`: lógica de negocio reutilizada por panel y bot.
- `app/panel/`: rutas, plantillas y estáticos del panel web.
- `app/routes/whatsapp_routes.py`: webhook de WhatsApp.
- `app/integrations/`: clientes externos de WhatsApp y OpenAI.
- `tests/`: pruebas unitarias, integración y plan de pruebas manuales.

La creación de reservas pasa por `BookingService`, que comprueba servicio activo, cliente, teléfono, horario, días cerrados, capacidad y solapamientos.

## Requisitos

- Docker y Docker Compose para la ejecución recomendada en local.
- Python 3.11 si se ejecuta sin Docker.
- MySQL 8.0.

## Variables de entorno

Copia el ejemplo y rellena los valores necesarios:

```bash
cp .env.example .env
```

Variables principales para local:

```env
SECRET_KEY=change-me
DATABASE_URL=
AUTO_INIT_DB=true
APP_TZ=Europe/Madrid
DEFAULT_MIN_ADVANCE_MIN=30
DEFAULT_MAX_DIAS_RESERVA=60
```

Variables para WhatsApp y OpenAI:

```env
WABA_TOKEN=
WABA_VERIFY_TOKEN=
WABA_APP_SECRET=
GRAPH_API_VERSION=v23.0
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

## Ejecución con Docker

```bash
docker compose up --build
```

Servicios expuestos:

- Panel/API Flask: `http://localhost:5000`
- MySQL: `localhost:3307`

Rutas útiles:

- `/login`: acceso al panel.
- `/panel`: dashboard del administrador.
- `/webhook/whatsapp`: webhook de WhatsApp.
- `/health`: health check.

Para reiniciar completamente la base de datos local:

```bash
docker compose down -v
docker compose up --build
```

## Datos demo

Si `AUTO_INIT_DB=true` y la base de datos está vacía, se crean datos de ejemplo:

| Peluquería | Email | Contraseña |
| --- | --- | --- |
| Peluquería Centro | `centro@example.com` | `admin123` |
| Barbería Norte | `norte@example.com` | `admin123` |

Estos usuarios son solo para pruebas locales.

## Base de datos

El proyecto usa SQLAlchemy y crea las tablas con `db.create_all()` durante el arranque cuando `AUTO_INIT_DB=true`.

Entidades principales:

- `Peluqueria`
- `UsuarioAdmin`
- `Cliente`
- `Servicio`
- `Profesional`
- `HorarioApertura`
- `DiaCerrado`
- `Reserva`

## Tests

Hay tres niveles:

| Nivel | Ubicación | Objetivo |
| --- | --- | --- |
| Unitario | `tests/unit/` | Comprobar reglas concretas (lógica): disponibilidad, teléfonos, reservas y cancelaciones. |
| Integración | `tests/integration/` | Comprobar que panel, servicios, webhook y base de datos de prueba trabajan juntos. |
| Manual / externo | `tests/README.md` | Registrar pruebas reales del panel y del bot con datos ficticios. |

Ejecutar con Docker:

```bash
docker compose exec api pytest
```

Ejecutar en local:

```bash
python -m pytest
```

Las pruebas automáticas usan SQLite en memoria. No necesitan MySQL real, WhatsApp real ni OpenAI real.

Casos principales cubiertos:

- Login y protección de rutas privadas.
- Aislamiento multi-tenant.
- Creación de reservas desde panel.
- Creación de reservas desde WhatsApp.
- Cancelaciones.
- Días cerrados.
- Solapamientos y capacidad según profesionales activos.
- Normalización de teléfonos.
- Webhook de WhatsApp.