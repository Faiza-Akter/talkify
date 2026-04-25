import uuid
from datetime import datetime


class MessageStore:
    """
    In-memory message index used for:
    - unique message ids
    - delivery status tracking
    - reply lookup
    """

    def __init__(self):
        self.messages = {}

    def create_message(self, scope, sender, content, target=None, room=None, reply_to=None, sender_profile_picture=""):
        message_id = str(uuid.uuid4())
        payload = {
            "message_id": message_id,
            "scope": scope,
            "sender": sender,
            "target": target,
            "room": room,
            "content": content,
            "reply_to": reply_to,
            "status": "sent",
            "sender_profile_picture": sender_profile_picture,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "delivered_to": []
        }
        self.messages[message_id] = payload
        return payload

    def get_message(self, message_id):
        return self.messages.get(message_id)

    def mark_delivered(self, message_id, username):
        message = self.messages.get(message_id)
        if not message:
            return None

        if username not in message["delivered_to"]:
            message["delivered_to"].append(username)

        message["status"] = "delivered"
        return message

    
    def count_messages_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return sum(
            1
            for message in self.messages.values()
            if message.get("created_at", "").startswith(today)
        )
    
    def reset_messages(self):
        self.messages.clear()