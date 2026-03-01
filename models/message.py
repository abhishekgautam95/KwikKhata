from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MessageType = Literal["text", "audio", "image", "unknown"]


@dataclass
class IncomingMessage:
    message_id: str
    from_number: str
    type: MessageType
    text: str = ""
    media_id: str = ""
    mime_type: str = ""
    timestamp: str = ""


@dataclass
class ReplyMessage:
    to_number: str
    body: str
