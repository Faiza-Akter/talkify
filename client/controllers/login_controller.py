from client.ui.chat_window import ChatWindow


class LoginController:
    def __init__(self, login_window, network_client):
        self.login_window = login_window
        self.network_client = network_client
        self.chat_window = None

        self.network_client.login_success.connect(self.handle_login_success)
        self.network_client.login_failed.connect(self.handle_login_failed)

    def login(self, username):
        self.network_client.connect_to_server(username)

    def handle_login_success(self, packet):
        self.chat_window = ChatWindow(
            network_client=self.network_client,
            username=self.network_client.username,
            initial_room=packet.get("room", "General")
        )
        self.chat_window.show()
        self.login_window.close()

    def handle_login_failed(self, message):
        self.login_window.show_error(message)