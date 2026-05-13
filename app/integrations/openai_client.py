# Llamadas a OpenAI para fechas, nombres y dudas.

import json
from datetime import date

from flask import current_app

from app.utils.datetime_utils import today_local


class OpenAIClient:
    def __init__(self):
        self.api_key = current_app.config.get("OPENAI_API_KEY", "")
        self.model = current_app.config.get("OPENAI_MODEL", "gpt-4o-mini")

    def available(self) -> bool:
        return bool(self.api_key)

    def parse_date(self, text: str, today: date | None = None) -> date | None:
        today = today or today_local()
        instruction = (
            "Eres un parser de fechas para un bot de reservas de peluquería. "
            f"La fecha actual es {today.isoformat()} y la zona horaria es Europe/Madrid. "
            "El usuario escribe en español. Interpreta expresiones como hoy, mañana, pasado mañana, "
            "este viernes, el viernes, viernes que viene, el próximo lunes, la semana que viene, "
            "15/05, 15 de mayo, dentro de dos semanas o este finde. "
            "Si el usuario dice un día de la semana sin más, usa la próxima fecha futura de ese día. "
            "Si dice 'que viene' o 'próximo' y hay duda, elige la siguiente semana. "
            "Devuelve solo JSON válido con esta forma: {\"fecha\": \"YYYY-MM-DD\"}. "
            "Si no hay una fecha clara, devuelve {\"fecha\": null}."
        )
        data = self.parse_json(instruction, text)
        value = (data or {}).get("fecha")
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def extract_name(self, text: str) -> str | None:
        instruction = (
            "Extrae el nombre de una persona para una reserva de peluquería. "
            "Puede venir como nombre suelto o frases como me llamo Diego, soy Laura García, "
            "a nombre de Marta o ponlo a nombre de Carlos. "
            "Devuelve solo JSON válido con esta forma: {\"nombre\": \"Nombre Apellidos\"}. "
            "No inventes apellidos. Si no hay un nombre claro, devuelve {\"nombre\": null}."
        )
        data = self.parse_json(instruction, text)
        name = (data or {}).get("nombre")
        if not name:
            return None
        name = " ".join(str(name).strip().split())
        if len(name) < 2 or len(name) > 100:
            return None
        if any(ch.isdigit() for ch in name):
            return None
        return name

    def answer_faq(self, question: str, context: str) -> str | None:
        if not self.available():
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres el asistente de una peluquería. Responde en español, con tono natural y breve. "
                            "Usa solo la información del contexto. No inventes servicios, precios, horarios, "
                            "direcciones ni disponibilidad. Si falta un dato, dilo claramente y ofrece el teléfono. "
                            "No confirmes reservas desde una duda. Si el usuario quiere reservar, indícale que use "
                            "la opción Reservar del menú. Si quiere cancelar, indícale que use Cancelar. "
                            "No menciones que eres una IA."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Contexto de la peluquería:\n{context}\n\nPregunta del cliente:\n{question}",
                    },
                ],
                temperature=0.1,
                max_tokens=220,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return None

    def parse_json(self, instruction: str, text: str) -> dict | None:
        if not self.available():
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": text or ""},
                ],
                temperature=0,
                max_tokens=120,
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(raw)
        except Exception:
            return None
