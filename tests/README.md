# Plan de pruebas de BarberApp

Este directorio recoge las pruebas usadas para justificar el apartado de testing del TFG. La idea no es demostrar una cobertura perfecta, sino dejar una validación clara, sencilla de explicar y conectada con los requisitos principales del sistema.

## Cómo ejecutar las pruebas automáticas

Con Docker:

```bash
docker compose exec api pytest
```

En local:

```bash
python -m pytest
```

Los tests usan SQLite en memoria, por eso no necesitan una base MySQL real ni credenciales de WhatsApp/OpenAI.

## Tipos de pruebas

| Tipo | Carpeta | Qué valida |
| --- | --- | --- |
| Unitarias | `tests/unit/` | Reglas concretas: disponibilidad, teléfonos, reservas y cancelaciones. |
| Integración | `tests/integration/` | Flujo entre rutas, servicios, base de datos de prueba y webhook. |
| Manuales / externas | Tabla inferior | Uso real del panel y del bot con datos ficticios. |

## Casos automáticos principales

| Caso | Tipo | Resultado esperado |
| --- | --- | --- |
| Login correcto | Integración | El administrador entra al panel. |
| Acceso sin sesión | Integración | Redirige a `/login`. |
| Aislamiento multi-tenant | Integración | Una peluquería no ve reservas de otra. |
| Crear reserva desde panel | Integración | Se crea reserva confirmada con origen `panel`. |
| Crear reserva desde WhatsApp | Integración | El bot crea la reserva y aparece en el panel. |
| Día cerrado | Unitaria / integración | No se ofrecen horas ni se permite reservar. |
| Solapamiento de reservas | Unitaria / integración | No se supera la capacidad de profesionales activos. |
| Cancelación | Unitaria / integración | Solo se cancela la reserva del cliente correcto. |
| Webhook WhatsApp | Integración | Se responde usando la peluquería asociada al `phone_number_id`. |
| Teléfonos | Unitaria | Se guardan en formato local de 9 cifras. |
