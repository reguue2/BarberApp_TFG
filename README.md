# BarberApp

BarberApp es una plataforma multi-tenant para gestionar reservas de peluquerías. El sistema une dos partes en una misma aplicación: un panel web para el administrador de cada peluquería y un bot de WhatsApp para que los clientes puedan reservar, cancelar cita o consultar dudas.

La idea principal del proyecto es que **la base de datos es la fuente de verdad**. El bot no guarda reservas por su cuenta y el panel no trabaja con otra base distinta. Ambos pasan por la misma lógica de negocio, los mismos modelos y las mismas validaciones.

## Demo desplegada

La aplicación está desplegada en Render para se pueda probarla sin instalar nada:

```text
https://barberapp-tfg.onrender.com/
```

El despliegue usa una base de datos MySQL externa y contiene datos de ejemplo para dos peluquerías.

> Aviso importante: el despliegue está en un plan gratuito. Si la aplicación lleva un rato sin usarse, la primera petición puede tardar más de lo normal porque el servicio tiene que arrancar de nuevo.

### Usuarios de prueba del panel

| Peluquería | Email | Contraseña |
| --- | --- | --- |
| Peluquería Centro | `centro@example.com` | `admin123` |
| Peluquería Norte | `norte@example.com` | `admin123` |

### Números para probar el bot por WhatsApp

Estos números están asociados a los datos de ejemplo del despliegue:

| Peluquería | Número de WhatsApp |
| --- | --- |
| Peluquería Centro | `+34 924 09 06 11` |
| Peluquería Norte | `+34 960 62 82 59` |

Una prueba sencilla sería:

1. Entrar en el panel con uno de los usuarios demo.
2. Revisar los servicios, profesionales, disponibilidad y reservas existentes.
3. Escribir por WhatsApp al número de esa peluquería.
4. Seguir el flujo del bot para reservar o cancelar una cita.
5. Volver al panel y comprobar que la reserva aparece o cambia de estado.

## Qué permite hacer

- Iniciar sesión como administrador de una peluquería.
- Separar los datos por peluquería mediante `peluqueria_id`.
- Gestionar servicios con nombre, descripción, precio, duración y estado.
- Gestionar profesionales, usados para calcular la capacidad de reservas simultáneas.
- Configurar horario semanal y días cerrados.
- Crear y cancelar reservas desde el panel.
- Consultar clientes y su historial de reservas.
- Reservar y cancelar citas desde WhatsApp.
- Usar OpenAI como ayuda para interpretar mensajes naturales del cliente.

## Arquitectura resumida

```text
Administrador
  -> Panel web Flask/Jinja
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

Carpetas principales:

| Carpeta | Función |
| --- | --- |
| `app/models/` | Modelos SQLAlchemy de la base de datos. |
| `app/repositories/` | Consultas y operaciones directas contra la base de datos. |
| `app/services/` | Reglas de negocio: reservas, disponibilidad, cancelaciones, conversación, etc. |
| `app/panel/` | Rutas y plantillas del panel de administración. |
| `app/routes/` | Rutas generales, health check y webhook de WhatsApp. |
| `app/integrations/` | Integración con WhatsApp Cloud API y OpenAI. |
| `tests/` | Pruebas automáticas. |

## Tecnologías usadas

- Python 3.11
- Flask
- Flask-Login
- Flask-WTF
- SQLAlchemy
- MySQL 8
- PyMySQL
- Docker y Docker Compose
- WhatsApp Cloud API
- OpenAI API
- Pytest
- Gunicorn
- Render para el despliegue de la aplicación
- Aiven/MySQL como base de datos externa del despliegue

## Modelo de datos

El modelo se centra en las entidades necesarias para defender el sistema como una plataforma de reservas:

- `Peluqueria`
- `UsuarioAdmin`
- `Cliente`
- `Servicio`
- `Profesional`
- `HorarioApertura`
- `DiaCerrado`
- `Reserva`

Todas las entidades principales dependen de `peluqueria_id`. Esto evita que un administrador vea o modifique datos de otra peluquería.

## Ejecutar en local con Docker

La forma recomendada de probar el proyecto en local es Docker, porque levanta la aplicación y MySQL con una configuración parecida a la usada durante el desarrollo.

1. Copiar el fichero de variables:

```bash
cp .env.example .env
```

Después de copiarlo, hay que revisar el fichero `.env` y rellenar como mínimo estas dos variables:

```env
DATABASE_URL=mysql+pymysql://USUARIO:CONTRASEÑA@mysql:3306/BASEDEDATOS
SECRET_KEY=cambia-esto-por-un-secreto-largo-y-aleatorio
```

2. Levantar la aplicación:

```bash
docker compose up --build
```

3. Abrir el panel:

```text
http://localhost:5000
```

Servicios expuestos:

| Servicio | URL / puerto |
| --- | --- |
| Aplicación Flask | `http://localhost:5000` |
| MySQL local | `localhost:3307` |

Rutas útiles:

| Ruta | Uso |
| --- | --- |
| `/` | Redirige al login o al panel si ya hay sesión. |
| `/login` | Acceso al panel. |
| `/registro` | Crear una nueva peluquería desde el panel. |
| `/panel` | Dashboard del administrador. |
| `/health` | Comprobación rápida de que la aplicación está viva. |
| `/webhook/whatsapp` | Webhook usado por Meta/WhatsApp. |

## Datos demo en local

Si `AUTO_INIT_DB=true` y la base de datos está vacía, el proyecto crea datos de ejemplo automáticamente al arrancar.

| Peluquería | Email | Contraseña |
| --- | --- | --- |
| Peluquería Centro | `centro@example.com` | `admin123` |
| Barbería Norte | `norte@example.com` | `admin123` |

También se crean servicios, profesionales, clientes, horarios, días cerrados y reservas de ejemplo para poder probar el panel sin tener que rellenar todo a mano.

Para borrar la base de datos local y volver a crear los datos demo:

```bash
docker compose down -v
docker compose up --build
```

## Limitación del bot en local

En local se puede probar el panel, la base de datos y los tests, pero **no se puede usar el bot real de WhatsApp directamente contra `localhost`**.

El motivo es que WhatsApp Cloud API envía los mensajes a un webhook público configurado en Meta for Developers. Un `localhost` de tu ordenador no es accesible desde Meta. Además, para enviar y recibir mensajes reales hacen falta las credenciales de WhatsApp y un número configurado en la cuenta de Meta.

Para una prueba real del bot se debe usar el despliegue público:

```text
https://barberapp-tfg.onrender.com/webhook/whatsapp
```

## Variables de entorno

Variables principales:

```env
FLASK_ENV
SECRET_KEY
AUTO_INIT_DB
DATABASE_URL
APP_TZ
DEFAULT_MIN_ADVANCE_MIN
DEFAULT_MAX_DIAS_RESERVA
```

Qué significa cada una:

- `FLASK_ENV`: indica el entorno de ejecución. En local se usa `development`.
- `SECRET_KEY`: clave interna de Flask para sesiones y seguridad básica del panel. Debe ser larga y no compartirse.
- `AUTO_INIT_DB`: permite inicializar automáticamente la base de datos y cargar datos demo al arrancar el proyecto. Para la demo local se deja en `true`.
- `DATABASE_URL`: cadena de conexión a MySQL. En Docker, el host `mysql` es el nombre del servicio de base de datos definido en `docker-compose.yml`.
- `APP_TZ`: zona horaria usada por la aplicación para tratar fechas y horas. En este proyecto se usa `Europe/Madrid`.
- `DEFAULT_MIN_ADVANCE_MIN`: antelación mínima para permitir una reserva. Por ejemplo, `30` evita reservar una cita que empieza en menos de 30 minutos.
- `DEFAULT_MAX_DIAS_RESERVA`: límite máximo de días hacia el futuro en los que se permite reservar.

Variables de WhatsApp y OpenAI:

```env
WABA_TOKEN
WABA_VERIFY_TOKEN
WABA_APP_SECRET
GRAPH_API_VERSION
OPENAI_API_KEY
OPENAI_MODEL
```

Qué significa cada una:

- `WABA_TOKEN`: token de acceso de WhatsApp Cloud API. Es necesario para que la aplicación pueda enviar respuestas por WhatsApp.
- `WABA_VERIFY_TOKEN`: token propio usado para validar el webhook cuando se configura en Meta. Debe coincidir con el valor introducido en el panel de Meta.
- `WABA_APP_SECRET`: secreto de la aplicación de Meta. Se usa para validar que las peticiones entrantes vienen realmente de WhatsApp.
- `GRAPH_API_VERSION`: versión de la API Graph de Meta que usa la integración de WhatsApp.
- `OPENAI_API_KEY`: clave de OpenAI. Permite usar el modelo para interpretar algunos mensajes escritos en lenguaje natural.
- `OPENAI_MODEL`: modelo de OpenAI usado por el proyecto.

En Render, `DATABASE_URL` apunta a la base de datos MySQL externa. Las credenciales reales de despliegue se configuran desde el panel de Render, no dentro del código.

## Tests

El proyecto incluye alrededor de 30 pruebas automáticas entre unitarias e integración.

Ejecutar con Docker:

```bash
docker compose exec api pytest
```

Los tests usan SQLite en memoria. Esto hace que sean rápidos y que no dependan de MySQL, WhatsApp real ni OpenAI real.

Resumen de pruebas:

| Tipo | Ubicación | Qué validan |
| --- | --- | --- |
| Unitarias | `tests/unit/` | Reglas concretas: disponibilidad, teléfonos, reservas y cancelaciones. |
| Integración | `tests/integration/` | Rutas del panel, webhook, flujo conversacional y base de datos de prueba. |
