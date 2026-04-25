import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.controllers.login_controller import LoginController


class LoginWindow(QWidget):
    def __init__(self, network_client) -> None:
        super().__init__()
        self.setObjectName("appRoot")

        self.network_client = network_client
        self.controller = LoginController(self, network_client)

        self.setWindowTitle("Talkify - Sign In")
        self._resize_to_screen()
        self._build_ui()

    def _resize_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        width = min(1260, int(screen.width() * 0.92))
        height = min(740, int(screen.height() * 0.90))
        self.resize(width, height)
        self.setMinimumSize(1080, 640)

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)

        shell = QFrame()
        shell.setObjectName("loginShell")

        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # LEFT HERO SECTION
        hero = QFrame()
        hero.setObjectName("loginHero")

        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(36, 34, 36, 34)
        hero_layout.setSpacing(18)

        badge_row = QHBoxLayout()
        badge = QLabel("TALKIFY  •  CLIENT-SERVER CHAT SYSTEM")
        badge.setObjectName("loginBadge")
        badge_row.addWidget(badge)
        badge_row.addStretch()

        hero_logo = QLabel()
        hero_logo.setAlignment(Qt.AlignCenter)

        # Prevents the logo from being cut
        hero_logo.setFixedHeight(250)

        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

        if os.path.exists(logo_path):
            hero_pixmap = QPixmap(logo_path).scaled(
                215,
                215,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            hero_logo.setPixmap(hero_pixmap)

        hero_title = QLabel("Modern desktop messaging with client-server architecture.")
        hero_title.setObjectName("loginHeroTitle")
        hero_title.setWordWrap(True)

        hero_text = QLabel(
            "Talkify demonstrates multi-client communication, public and private messaging, "
            "room-based chat, and admin moderation using Python, PySide6, and MySQL."
        )
        hero_text.setObjectName("loginHeroText")
        hero_text.setWordWrap(True)

        pills = QFrame()
        pills.setObjectName("featureGlassCard")

        pills_layout = QVBoxLayout(pills)
        pills_layout.setContentsMargins(16, 16, 16, 16)
        pills_layout.setSpacing(8)

        for item_text in [
            "Threaded TCP server for multiple clients",
            "JSON-based public, private, and room messaging",
            "MySQL-backed admin and banned-user checks",
        ]:
            pill = QLabel("• " + item_text)
            pill.setObjectName("featurePillText")
            pills_layout.addWidget(pill)

        hero_layout.addLayout(badge_row)

        # Logo area in the upper-middle section
        hero_layout.addSpacing(6)
        hero_layout.addWidget(hero_logo, alignment=Qt.AlignCenter)
        hero_layout.addSpacing(18)

        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(hero_text)
        hero_layout.addWidget(pills)

        # RIGHT LOGIN FORM SECTION
        form_panel = QFrame()
        form_panel.setObjectName("loginFormPanel")

        form_layout = QVBoxLayout(form_panel)
        form_layout.setContentsMargins(44, 34, 44, 34)
        form_layout.setSpacing(16)

        brand_row = QHBoxLayout()
        brand_row.addStretch()

        small_logo = QLabel()
        small_logo.setAlignment(Qt.AlignCenter)

        if os.path.exists(logo_path):
            small_pixmap = QPixmap(logo_path).scaled(
                48,
                48,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            small_logo.setPixmap(small_pixmap)


        heading = QLabel("Join Talkify")
        heading.setObjectName("loginHeading")
        heading.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Enter a username to connect to the Talkify server.")
        subtitle.setObjectName("loginSubheading")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        form_card = QFrame()
        form_card.setObjectName("loginCard")

        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(22, 22, 22, 22)
        form_card_layout.setSpacing(12)

        field_label = QLabel("Username")
        field_label.setObjectName("formLabel")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. Admin or Faiza123")
        self.username_input.returnPressed.connect(self.on_login_clicked)

        self.error_label = QLabel("")
        self.error_label.setObjectName("formError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.login_button = QPushButton("Connect to Server")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setFixedHeight(46)
        self.login_button.clicked.connect(self.on_login_clicked)

        helper = QLabel(
            "Duplicate usernames and banned users are validated by the server "
            "before access is granted."
        )
        helper.setObjectName("helperText")
        helper.setWordWrap(True)

        feature_grid = QFrame()
        feature_grid.setObjectName("tinyFeatureGrid")

        feature_grid_layout = QHBoxLayout(feature_grid)
        feature_grid_layout.setContentsMargins(12, 10, 12, 10)
        feature_grid_layout.setSpacing(14)

        for text in ["Public Chat", "Private Chat", "Rooms", "Admin Control"]:
            label = QLabel(text)
            label.setObjectName("tinyFeatureText")
            feature_grid_layout.addWidget(label)

        form_card_layout.addWidget(field_label)
        form_card_layout.addWidget(self.username_input)
        form_card_layout.addWidget(self.error_label)
        form_card_layout.addWidget(self.login_button)
        form_card_layout.addWidget(helper)
        form_card_layout.addWidget(feature_grid)

        form_layout.addLayout(brand_row)
        form_layout.addStretch()
        form_layout.addWidget(heading)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(6)
        form_layout.addWidget(form_card)
        form_layout.addStretch()

        shell_layout.addWidget(hero, 11)
        shell_layout.addWidget(form_panel, 10)

        root.addWidget(shell)

    def on_login_clicked(self) -> None:
        username = self.username_input.text().strip()

        if not username:
            self.show_error("Username cannot be empty.")
            return

        self.error_label.hide()
        self.login_button.setText("Connecting...")
        self.login_button.setEnabled(False)
        self.controller.login(username)

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()
        self.login_button.setText("Start Messaging")
        self.login_button.setEnabled(True)