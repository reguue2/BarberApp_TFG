# Pruebas de BarberApp

## Cómo ejecutar las pruebas

Con Docker, desde la raíz del proyecto:

```bash
docker compose exec api pytest
```

Los tests automáticos usan SQLite en memoria. Por eso no necesitan:

- MySQL real.
- WhatsApp real.
- OpenAI real.
- Un despliegue activo en Render.

## Organización

```text
tests/
  unit/
    test_availability_service.py
    test_parsers_and_payload.py
    test_reservation_and_cancellation.py
  integration/
    test_conversation_flow.py
    test_panel.py
    test_whatsapp_webhook.py
  conftest.py
```

`conftest.py` crea una aplicación Flask de prueba, una base de datos temporal y datos mínimos para comprobar dos peluquerías distintas. Así se puede validar también el aislamiento multi-tenant.

## Pruebas unitarias

Las pruebas unitarias se centran en reglas pequeñas de negocio. No prueban la interfaz, sino la lógica que debe funcionar siempre.

| Archivo | Qué comprueba |
| --- | --- |
| `test_availability_service.py` | Horarios disponibles, días cerrados, capacidad y profesionales activos. |
| `test_parsers_and_payload.py` | Normalización de teléfonos, comandos básicos y extracción de mensajes de WhatsApp. |
| `test_reservation_and_cancellation.py` | Creación de reservas, cliente asociado, solapamientos y cancelaciones. |

Casos relevantes:

- Devuelve horas libres dentro del horario configurado.
- No ofrece horas si el día está cerrado.
- No permite superar la capacidad marcada por los profesionales activos.
- Si no hay profesionales activos, no se ofrecen huecos.
- Normaliza teléfonos españoles a 9 cifras.
- Rechaza teléfonos inválidos.
- Cancela solo reservas del cliente correcto.

## Pruebas de integración

Las pruebas de integración validan que varias piezas funcionen juntas: rutas Flask, sesión de usuario, servicios, base de datos temporal y webhook.

| Archivo | Qué comprueba |
| --- | --- |
| `test_panel.py` | Login, rutas protegidas, panel, reservas, servicios, profesionales, clientes y multi-tenant. |
| `test_conversation_flow.py` | Flujo conversacional del bot: reserva, cliente existente, listas y cancelación. |
| `test_whatsapp_webhook.py` | Recepción del webhook, peluquería asociada al número e idempotencia. |

Casos relevantes:

- El login correcto entra al panel.
- Sin sesión se redirige a `/login`.
- Un administrador no ve reservas de otra peluquería.
- Se puede crear una reserva desde el panel.
- No se puede crear una reserva en un día cerrado.
- No se puede reservar una hora llena.
- Una reserva creada desde WhatsApp aparece en el panel.

## Qué no prueban los tests automáticos

Los tests automáticos no prueban llamadas reales a Meta ni a OpenAI. Eso se deja fuera a propósito porque dependería de credenciales, red externa, estado de las APIs y configuración de cada cuenta.

Lo que sí se prueba es la parte que debe ser estable en el proyecto:

- La lógica de reservas.
- La disponibilidad.
- La separación por peluquería.
- El flujo interno del bot.
- La recepción simulada del webhook.
- Las rutas principales del panel.
