from client.ui.chat_window import ChatWindow


class LoginController:
    def __init__(self, login_window, network_client) -> None:
        self.login_window = login_window
        self.network_client = network_client
        self.chat_window = None

        self.network_client.login_success.connect(self._handle_login_success)
        self.network_client.login_failed.connect(self._handle_login_failed)

    def login(self, username: str) -> None:
        self.network_client.connect_to_server(username)

    def _handle_login_success(self, packet: dict) -> None:
        self.chat_window = ChatWindow(
            network_client=self.network_client,
            username=self.network_client.username or 'User',
            initial_room=packet.get('room', 'General'),
            is_admin=packet.get("is_admin", False)
        )
        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()
        self.login_window.close()

    def _handle_login_failed(self, message: str) -> None:
        self.login_window.show_error(message)
