class ChatController:
    def __init__(self, network_client) -> None:
        self.network_client = network_client

    def send_message(self, mode: str, target_name: str | None, message: str) -> None:
        text = message.strip()
        if not text:
            return

        if mode == 'public':
            self.network_client.send_public_message(text)
        elif mode == 'private' and target_name:
            self.network_client.send_private_message(target_name, text)
        elif mode == 'room' and target_name:
            self.network_client.send_room_message(target_name, text)
