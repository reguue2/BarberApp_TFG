# Extrae texto, botones y listas del payload de WhatsApp.

from dataclasses import dataclass


@dataclass
class IncomingWhatsAppMessage:
    wamid: str
    from_phone: str
    phone_number_id: str
    text: str
    origin: str
    timestamp: str | None = None


class WhatsAppPayloadParser:
    @staticmethod
    def parse(payload: dict) -> list[IncomingWhatsAppMessage]:
        messages = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id")
                if value.get("statuses"):
                    continue
                for msg in value.get("messages", []) or []:
                    parsed = WhatsAppPayloadParser._parse_message(msg, phone_number_id)
                    if parsed:
                        messages.append(parsed)
        return messages

    @staticmethod
    def _parse_message(msg: dict, phone_number_id: str | None):
        wamid = msg.get("id")
        from_phone = msg.get("from")
        msg_type = msg.get("type")
        text = None
        origin = "text"

        if msg_type == "text":
            text = (msg.get("text") or {}).get("body")
            origin = "text"
        elif msg_type == "interactive":
            interactive = msg.get("interactive") or {}
            if interactive.get("type") == "button_reply":
                text = (interactive.get("button_reply") or {}).get("id")
                origin = "button"
            elif interactive.get("type") == "list_reply":
                text = (interactive.get("list_reply") or {}).get("id")
                origin = "list"
        elif msg_type == "button":
            text = (msg.get("button") or {}).get("payload") or (msg.get("button") or {}).get("text")
            origin = "button"

        if not wamid or not from_phone or not phone_number_id or not text:
            return None
        return IncomingWhatsAppMessage(
            wamid=wamid,
            from_phone=from_phone,
            phone_number_id=phone_number_id,
            text=text,
            origin=origin,
            timestamp=msg.get("timestamp"),
        )
