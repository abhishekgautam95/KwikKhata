import unittest
import tempfile
import os
from unittest.mock import patch

from database import KhataDB
from models.message import IncomingMessage
from services.message_router import MessageRouter
from services.whatsapp_client import parse_incoming_messages


class TestWhatsAppIntegration(unittest.TestCase):
    def test_parse_incoming_text_message(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.123",
                                        "from": "919999999999",
                                        "timestamp": "12345",
                                        "type": "text",
                                        "text": {"body": "/all"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        messages = parse_incoming_messages(payload)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].type, "text")
        self.assertEqual(messages[0].text, "/all")

    @patch("services.message_router.send_text_message")
    def test_router_process_text(self, mock_send):
        mock_send.return_value = {"ok": True}
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        os.remove(path)
        try:
            db = KhataDB(path)
            db.add_transaction("Raju", 100)
            router = MessageRouter(db)
            msg = IncomingMessage(
                message_id="m-1",
                from_number="919999999999",
                type="text",
                text="/all",
            )
            replies = router.route([msg])
            self.assertEqual(len(replies), 1)
            self.assertIn("Pending", replies[0]["body"])
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
