import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from client.network_client import NetworkClient
from client.ui.login_window import LoginWindow
from client.ui.splash_screen import SplashScreen


def load_stylesheet():
    theme_path = os.path.join(
        os.path.dirname(__file__),
        "ui",
        "assets",
        "styles",
        "theme.qss"
    )

    if os.path.exists(theme_path):
        with open(theme_path, "r", encoding="utf-8") as file:
            return file.read()
    return ""


def run_client_app():
    app = QApplication(sys.argv)
    app.setApplicationName("Talkify")

    logo_path = os.path.join(
        os.path.dirname(__file__),
        "ui",
        "assets",
        "logo.png"
    )
    if os.path.exists(logo_path):
        app.setWindowIcon(QIcon(logo_path))

    app.setStyleSheet(load_stylesheet())

    network_client = NetworkClient()
    login_window = LoginWindow(network_client)

    def show_login():
        login_window.show()

    splash = SplashScreen(on_finish_callback=show_login)
    splash.show()

    sys.exit(app.exec())