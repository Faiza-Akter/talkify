class ChatController:
    def __init__(self, chat_window, network_client):
        self.chat_window = chat_window
        self.network_client = network_client

    def send_message(self, target_mode, target_name, message):
        if not message.strip():
            return

        if target_mode == "public":
            self.network_client.send_public_message(message)
        elif target_mode == "private":
            self.network_client.send_private_message(target_name, message)
        elif target_mode == "room":
            self.network_client.send_room_message(target_name, message)