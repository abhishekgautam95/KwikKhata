from __future__ import annotations

import re
from typing import Iterable

from config import settings
from database import KhataDB
from models.message import IncomingMessage
from services.ledger_agent import PendingIntentStore, process_user_text
from services.reminder_engine import send_customer_reminder
from services.stt_service import transcribe_audio_bytes
from services.vision_service import parse_bill_image
from services.whatsapp_client import download_media_bytes, fetch_media_url, send_text_message


class MessageRouter:
    def __init__(self, db: KhataDB):
        self.db = db
        self.pending_store = PendingIntentStore()
        self.processed_ids: set[str] = set()

    def _handle_text(self, msg: IncomingMessage) -> str:
        text = msg.text.strip()
        lower = text.lower()

        # Owner shortcut: "haan bhej de Raju"
        match = re.match(r"^(haan|ha|yes)\s+bhej\s+de\s+(.+)$", lower)
        if msg.from_number == settings.owner_whatsapp_number and match:
            customer_name = match.group(2).strip().title()
            if send_customer_reminder(customer_name):
                return f"✅ Reminder {customer_name} ko bhej diya."
            return f"❌ {customer_name} ka number phonebook me nahi mila."

        return process_user_text(self.db, self.pending_store, msg.from_number, text).text

    def _handle_audio(self, msg: IncomingMessage) -> str:
        media_url = fetch_media_url(msg.media_id)
        blob = download_media_bytes(media_url or "")
        if not blob:
            return "❌ Audio download nahi ho paya. Dobara bhejiye."
        transcript = transcribe_audio_bytes(blob, filename="voice.ogg")
        if not transcript:
            return "❌ Audio samajh nahi paya. Please text ya clearer voice note bhejiye."
        response = process_user_text(self.db, self.pending_store, msg.from_number, transcript)
        return f"🎙️ Transcript: {transcript}\n\n{response.text}"

    def _handle_image(self, msg: IncomingMessage) -> str:
        media_url = fetch_media_url(msg.media_id)
        blob = download_media_bytes(media_url or "")
        if not blob:
            return "❌ Image download nahi ho payi. Dobara bhejiye."

        parsed = parse_bill_image(blob, mime_type=msg.mime_type or "image/jpeg")
        if not parsed:
            return "❌ Bill parse nahi ho paya. Clear photo bhejiye ya manual entry karein."

        entries = parsed.get("entries") or []
        if not entries:
            notes = parsed.get("notes", "No valid entries found.")
            return f"⚠️ Parcha parse hua par entry clear nahi mili.\nNotes: {notes}"

        added = []
        for row in entries:
            name = str(row.get("customer_name", "")).strip().title()
            amount = float(row.get("amount", 0))
            if not name or amount == 0:
                continue
            old_balance = self.db.get_balance(name) or 0
            new_balance = self.db.add_transaction(name, amount)
            added.append(f"- {name}: ₹{int(old_balance)} -> ₹{int(new_balance)}")

        if not added:
            return "⚠️ Parsed entries valid nahi thi. Manual confirm required."
        return "✅ Parcha processed.\n" + "\n".join(added)

    def route(self, messages: Iterable[IncomingMessage]) -> list[dict]:
        replies: list[dict] = []
        for msg in messages:
            if msg.message_id and msg.message_id in self.processed_ids:
                continue
            if msg.message_id:
                self.processed_ids.add(msg.message_id)

            if msg.type == "text":
                body = self._handle_text(msg)
            elif msg.type == "audio":
                body = self._handle_audio(msg)
            elif msg.type == "image":
                body = self._handle_image(msg)
            else:
                body = "ℹ️ Sirf text, voice note, aur image currently supported hain."

            delivery = send_text_message(msg.from_number, body)
            replies.append({"to": msg.from_number, "body": body, "delivery": delivery})
        return replies
