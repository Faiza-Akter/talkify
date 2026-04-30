import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from client.network_client import NetworkClient
from client.ui.login_window import LoginWindow
from client.ui.splash_screen import SplashScreen


def _load_stylesheet() -> str:
    theme_path = os.path.join(
        os.path.dirname(__file__),
        'ui',
        'assets',
        'styles',
        'theme.qss',
    )

    if not os.path.exists(theme_path):
        return ''

    with open(theme_path, 'r', encoding='utf-8') as file:
        return file.read()


def _set_window_icon(app: QApplication) -> None:
    logo_path = os.path.join(os.path.dirname(__file__), 'ui', 'assets', 'logo.png')

    if os.path.exists(logo_path):
        app.setWindowIcon(QIcon(logo_path))


def run_client_app() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName('Talkify')
    _set_window_icon(app)
    app.setStyleSheet(_load_stylesheet())

    network_client = NetworkClient()
    login_window = LoginWindow(network_client)

    splash_holder = {
        'splash': None,
    }

    def show_login() -> None:
        splash = splash_holder.get('splash')

        if splash is not None:
            splash_holder['splash'] = None
            splash.hide()
            splash.deleteLater()

        login_window.show()
        login_window.raise_()
        login_window.activateWindow()

    splash_holder['splash'] = SplashScreen(on_finish=show_login)
    splash_holder['splash'].show()

    sys.exit(app.exec())