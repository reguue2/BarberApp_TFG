# Lee la configuración desde variables de entorno.

import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///chatbot_tfg.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APP_TZ = os.getenv("APP_TZ", "Europe/Madrid")
    DEFAULT_MIN_ADVANCE_MIN = int(os.getenv("DEFAULT_MIN_ADVANCE_MIN", "30"))
    DEFAULT_MAX_DIAS_RESERVA = int(os.getenv("DEFAULT_MAX_DIAS_RESERVA", "60"))

    WABA_TOKEN = os.getenv("WABA_TOKEN", "")
    WABA_VERIFY_TOKEN = os.getenv("WABA_VERIFY_TOKEN", "")
    WABA_APP_SECRET = os.getenv("WABA_APP_SECRET", "")
    GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v23.0")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    AUTO_INIT_DB = os.getenv("AUTO_INIT_DB", "true").lower() == "true"