import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame


class SplashScreen(QWidget):
    def __init__(self, on_finish_callback=None):
        super().__init__()
        self.on_finish_callback = on_finish_callback

        self.setWindowTitle("Talkify")
        self.setFixedSize(760, 460)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.build_ui()

        QTimer.singleShot(1800, self.finish_splash)

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("splashCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(16)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)

        logo_path = os.path.join(
            os.path.dirname(__file__),
            "assets",
            "logo.png"
        )
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(
                140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo.setPixmap(pixmap)

        title = QLabel("Talkify")
        title.setObjectName("splashTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Elegant real-time communication for your network project")
        subtitle.setObjectName("splashSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        footer = QLabel("Loading interface...")
        footer.setObjectName("splashFooter")
        footer.setAlignment(Qt.AlignCenter)

        card_layout.addStretch()
        card_layout.addWidget(logo)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(12)
        card_layout.addWidget(footer)
        card_layout.addStretch()

        root.addWidget(card)

    def finish_splash(self):
        self.close()
        if self.on_finish_callback:
            self.on_finish_callback()