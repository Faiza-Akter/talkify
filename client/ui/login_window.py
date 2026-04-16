import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QFrame
)

from client.controllers.login_controller import LoginController


class LoginWindow(QWidget):
    def __init__(self, network_client):
        super().__init__()
        self.network_client = network_client
        self.controller = LoginController(self, network_client)

        self.setWindowTitle("Talkify - Login")
        self.resize(1120, 700)
        self.setMinimumSize(980, 620)

        self.build_ui()

    def build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(24)

        left_panel = QFrame()
        left_panel.setObjectName("authHeroPanel")

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(42, 42, 42, 42)
        left_layout.setSpacing(20)

        badge = QLabel("TALKIFY • MODERN CHAT SYSTEM")
        badge.setObjectName("authBadge")

        headline = QLabel("Professional communication, designed with elegance.")
        headline.setWordWrap(True)
        headline.setObjectName("authHeadline")

        subtitle = QLabel(
            "Talkify blends real-time messaging, rooms, private chat, and admin "
            "controls inside a premium soft-light interface tailored for a standout "
            "Computer Network project."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("authSubtitle")

        stat_row = QHBoxLayout()
        stat_row.setSpacing(14)

        for title, value in [
            ("Protocol", "TCP + JSON"),
            ("GUI", "PySide6"),
            ("Style", "Pastel Light")
        ]:
            card = QFrame()
            card.setObjectName("miniStatCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)

            label1 = QLabel(title)
            label1.setObjectName("miniStatTitle")
            label2 = QLabel(value)
            label2.setObjectName("miniStatValue")

            card_layout.addWidget(label1)
            card_layout.addWidget(label2)
            stat_row.addWidget(card)

        palette_card = QFrame()
        palette_card.setObjectName("palettePreviewCard")
        palette_layout = QHBoxLayout(palette_card)
        palette_layout.setContentsMargins(18, 18, 18, 18)
        palette_layout.setSpacing(12)

        for color in ["#0B1F3A", "#C38EB4", "#E1CBD7", "#86A8CF", "#26425A"]:
            swatch = QFrame()
            swatch.setFixedSize(42, 42)
            swatch.setStyleSheet(
                f"background-color: {color}; border-radius: 21px; border: 2px solid white;"
            )
            palette_layout.addWidget(swatch)

        palette_layout.addStretch()

        left_layout.addWidget(badge)
        left_layout.addStretch()
        left_layout.addWidget(headline)
        left_layout.addWidget(subtitle)
        left_layout.addLayout(stat_row)
        left_layout.addWidget(palette_card)
        left_layout.addStretch()

        right_panel = QFrame()
        right_panel.setObjectName("authCard")
        right_panel.setFixedWidth(390)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(36, 36, 36, 36)
        right_layout.setSpacing(16)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)

        logo_path = os.path.join(
            os.path.dirname(__file__),
            "assets",
            "logo.png"
        )
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(
                150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)

        title = QLabel("Welcome back")
        title.setObjectName("authTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle2 = QLabel("Enter your username to continue into Talkify.")
        subtitle2.setObjectName("authFormSubtitle")
        subtitle2.setAlignment(Qt.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.error_label = QLabel("")
        self.error_label.setObjectName("authError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.login_button = QPushButton("Join Talkify")
        self.login_button.setObjectName("primaryButton")
        self.login_button.clicked.connect(self.on_login_clicked)

        footer_note = QLabel("Designed with your custom Talkify color palette")
        footer_note.setObjectName("authFooterNote")
        footer_note.setAlignment(Qt.AlignCenter)

        right_layout.addWidget(logo_label)
        right_layout.addSpacing(6)
        right_layout.addWidget(title)
        right_layout.addWidget(subtitle2)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.username_input)
        right_layout.addWidget(self.error_label)
        right_layout.addSpacing(6)
        right_layout.addWidget(self.login_button)
        right_layout.addStretch()
        right_layout.addWidget(footer_note)

        root.addWidget(left_panel, 1)
        root.addWidget(right_panel, 0, Qt.AlignCenter)

    def on_login_clicked(self):
        username = self.username_input.text().strip()
        if not username:
            self.show_error("Username cannot be empty.")
            return

        self.error_label.hide()
        self.login_button.setText("Connecting...")
        self.login_button.setEnabled(False)

        self.controller.login(username)

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()
        self.login_button.setText("Join Talkify")
        self.login_button.setEnabled(True)