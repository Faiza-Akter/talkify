import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap, QIcon, QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
)

from client.controllers.login_controller import LoginController


class LoginWindow(QWidget):
    def __init__(self, network_client) -> None:
        super().__init__()
        self.setObjectName("appRoot")

        self.network_client = network_client
        self.controller = LoginController(self, network_client)

        self.setWindowTitle("Talkify — Sign In")
        self._resize_to_screen()
        self._build_ui()

    def _resize_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        width = min(1300, int(screen.width() * 0.92))
        height = min(760, int(screen.height() * 0.90))
        self.resize(width, height)
        self.setMinimumSize(1080, 640)

    def _make_sharp_pixmap(self, image_path: str, size: int) -> QPixmap:
        if not os.path.exists(image_path):
            return QPixmap()

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return QPixmap()

        scale = 2
        target = size * scale

        sharp = pixmap.scaled(
            target,
            target,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        sharp.setDevicePixelRatio(scale)

        return sharp

    def _add_glow(self, widget, radius=22, color="#86A8CF", x=0, y=4):
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(radius)
        effect.setColor(QColor(color))
        effect.setOffset(x, y)
        widget.setGraphicsEffect(effect)

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)

        shell = QFrame()
        shell.setObjectName("loginShell")

        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        icons_dir = os.path.join(assets_dir, "icons")
        logo_path = os.path.join(assets_dir, "logo.png")

        # =====================================================
        # LEFT HERO PANEL
        # =====================================================

        hero = QFrame()
        hero.setObjectName("loginHero")

        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(48, 34, 48, 34)
        hero_layout.setSpacing(0)

        badge_row = QHBoxLayout()
        badge = QLabel("✦  TALKIFY  ·  CLIENT-SERVER MESSAGING")
        badge.setObjectName("loginBadge")

        badge_row.addWidget(badge)
        badge_row.addStretch()

        hero_logo = QLabel()
        hero_logo.setObjectName("heroLogoLabel")
        hero_logo.setAlignment(Qt.AlignCenter)

        # Increase this height if the logo gets cut.
        hero_logo.setFixedHeight(255)

        if os.path.exists(logo_path):
            hero_logo.setPixmap(self._make_sharp_pixmap(logo_path, 420))

        self._add_glow(hero_logo, radius=75, color="#C38EB4", x=0, y=0)

        hero_title = QLabel("Desktop Chat Network.")
        hero_title.setObjectName("loginHeroTitle")
        hero_title.setWordWrap(False)

        hero_accent_bar = QFrame()
        hero_accent_bar.setObjectName("heroAccentBar")
        hero_accent_bar.setFixedHeight(3)

        hero_text = QLabel(
            "Talkify brings users together through real-time public chat, private "
            "messaging, secure rooms, and admin moderation in one polished desktop "
            "communication system."
        )
        hero_text.setObjectName("loginHeroText")
        hero_text.setWordWrap(True)

        feature_showcase = QFrame()
        feature_showcase.setObjectName("featureGlassCard")

        showcase_layout = QHBoxLayout(feature_showcase)
        showcase_layout.setContentsMargins(16, 10, 16, 10)
        showcase_layout.setSpacing(0)

        showcase_items = [
            ("server.png", "Server"),
            ("database.png", "Database"),
            ("messageicon.png", "Messaging"),
            ("code.png", "Python"),
        ]

        for index, (icon_name, text) in enumerate(showcase_items):
            item = QFrame()
            item.setObjectName("loginShowcaseItem")

            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(8, 4, 8, 4)
            item_layout.setSpacing(5)
            item_layout.setAlignment(Qt.AlignCenter)

            icon = QLabel()
            icon.setObjectName("loginShowcaseIcon")
            icon.setAlignment(Qt.AlignCenter)
            icon.setFixedSize(54, 54)

            icon_path = os.path.join(icons_dir, icon_name)

            if not os.path.exists(icon_path):
                icon_path = os.path.join(assets_dir, icon_name)

            if os.path.exists(icon_path):
                pixmap = self._make_sharp_pixmap(icon_path, 44)

                if not pixmap.isNull():
                    icon.setPixmap(pixmap)

            title_lbl = QLabel(text)
            title_lbl.setObjectName("loginShowcaseText")
            title_lbl.setAlignment(Qt.AlignCenter)

            item_layout.addWidget(icon, alignment=Qt.AlignCenter)
            item_layout.addWidget(title_lbl, alignment=Qt.AlignCenter)

            showcase_layout.addWidget(item)

            if index < len(showcase_items) - 1:
                divider = QFrame()
                divider.setObjectName("loginShowcaseDivider")
                divider.setFixedWidth(1)
                showcase_layout.addWidget(divider)

        # =====================================================
        # LEFT HERO LAYOUT ASSEMBLY
        # This block controls vertical position.
        # =====================================================

        hero_layout.addLayout(badge_row)

        # Lower number = logo and text move more upward.
        hero_layout.addSpacing(12)

        hero_layout.addWidget(hero_logo, alignment=Qt.AlignHCenter)

        # Lower number = title moves closer to logo.
        hero_layout.addSpacing(-18)

        hero_layout.addWidget(hero_title)
        hero_layout.addSpacing(6)
        hero_layout.addWidget(hero_accent_bar)
        hero_layout.addSpacing(8)
        hero_layout.addWidget(hero_text)
        hero_layout.addSpacing(10)
        hero_layout.addWidget(feature_showcase)

        hero_layout.addStretch(1)

        # =====================================================
        # RIGHT FORM PANEL
        # =====================================================

        form_panel = QFrame()
        form_panel.setObjectName("loginFormPanel")

        form_layout = QVBoxLayout(form_panel)
        form_layout.setContentsMargins(52, 44, 52, 44)
        form_layout.setSpacing(0)

        heading_wrap = QWidget()
        heading_wrap.setObjectName("headingWrap")

        heading_vbox = QVBoxLayout(heading_wrap)
        heading_vbox.setContentsMargins(0, 0, 0, 0)
        heading_vbox.setSpacing(6)

        heading = QLabel("Welcome back.")
        heading.setObjectName("loginHeading")
        heading.setAlignment(Qt.AlignLeft)

        subtitle = QLabel("Enter your username to jump straight into the conversation.")
        subtitle.setObjectName("loginSubheading")
        subtitle.setAlignment(Qt.AlignLeft)
        subtitle.setWordWrap(True)

        heading_vbox.addWidget(heading)
        heading_vbox.addWidget(subtitle)

        form_card = QFrame()
        form_card.setObjectName("loginCard")
        self._add_glow(form_card, radius=40, color="#86A8CF", x=0, y=8)

        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(28, 24, 28, 24)
        form_card_layout.setSpacing(14)

        field_label_row = QHBoxLayout()
        field_label_row.setSpacing(8)

        user_icon = QLabel()
        user_icon.setObjectName("formLabelIcon")
        user_icon.setFixedSize(20, 20)
        user_icon.setAlignment(Qt.AlignCenter)

        user_icon_path = os.path.join(icons_dir, "user.svg")

        if os.path.exists(user_icon_path):
            user_icon.setPixmap(QIcon(user_icon_path).pixmap(18, 18))

        field_label = QLabel("USERNAME")
        field_label.setObjectName("formLabel")

        field_label_row.addWidget(user_icon)
        field_label_row.addWidget(field_label)
        field_label_row.addStretch()

        input_shell = QFrame()
        input_shell.setObjectName("inputShell")

        input_shell_layout = QHBoxLayout(input_shell)
        input_shell_layout.setContentsMargins(16, 0, 12, 0)
        input_shell_layout.setSpacing(0)

        at_label = QLabel("@")
        at_label.setObjectName("inputPrefix")

        self.username_input = QLineEdit()
        self.username_input.setObjectName("usernameInput")
        self.username_input.setPlaceholderText("Admin  or  YourName")
        self.username_input.returnPressed.connect(self.on_login_clicked)

        input_shell_layout.addWidget(at_label)
        input_shell_layout.addWidget(self.username_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("formError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.login_button = QPushButton("Connect to Talkify  →")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setFixedHeight(50)
        self.login_button.clicked.connect(self.on_login_clicked)

        self._add_glow(self.login_button, radius=30, color="#C38EB4", x=0, y=6)

        helper = QLabel("Access public rooms, private DMs, secure rooms, and admin tools.")
        helper.setObjectName("helperText")
        helper.setWordWrap(False)
        helper.setAlignment(Qt.AlignCenter)

        feature_grid = QFrame()
        feature_grid.setObjectName("tinyFeatureGrid")

        feature_grid_layout = QHBoxLayout(feature_grid)
        feature_grid_layout.setContentsMargins(0, 0, 0, 0)
        feature_grid_layout.setSpacing(8)

        feature_items = [
            ("Public Chat", "globe.svg"),
            ("Private Chat", "lock-keyhole.svg"),
            ("Rooms", "door-open.svg"),
            ("Admin Control", "shield.svg"),
        ]

        for text, icon_name in feature_items:
            feature_card = QFrame()
            feature_card.setObjectName("tinyFeatureCard")

            feature_card_layout = QHBoxLayout(feature_card)
            feature_card_layout.setContentsMargins(10, 7, 10, 7)
            feature_card_layout.setSpacing(6)

            icon_lbl = QLabel()
            icon_lbl.setObjectName("tinyFeatureIcon")
            icon_lbl.setFixedSize(18, 18)
            icon_lbl.setAlignment(Qt.AlignCenter)

            icon_path = os.path.join(icons_dir, icon_name)

            if os.path.exists(icon_path):
                icon_lbl.setPixmap(QIcon(icon_path).pixmap(16, 16))

            label = QLabel(text)
            label.setObjectName("tinyFeatureText")

            feature_card_layout.addWidget(icon_lbl)
            feature_card_layout.addWidget(label)

            feature_grid_layout.addWidget(feature_card)

        feature_grid_layout.addStretch()

        form_card_layout.addLayout(field_label_row)
        form_card_layout.addWidget(input_shell)
        form_card_layout.addWidget(self.error_label)
        form_card_layout.addWidget(self.login_button)
        form_card_layout.addSpacing(4)
        form_card_layout.addWidget(helper)
        form_card_layout.addSpacing(8)
        form_card_layout.addWidget(feature_grid)

        form_layout.addStretch(2)
        form_layout.addWidget(heading_wrap)
        form_layout.addSpacing(28)
        form_layout.addWidget(form_card)
        form_layout.addStretch(3)

        shell_layout.addWidget(hero, 55)
        shell_layout.addWidget(form_panel, 45)

        root.addWidget(shell)

    def on_login_clicked(self) -> None:
        username = self.username_input.text().strip()

        if not username:
            self.show_error("Username cannot be empty.")
            return

        self.error_label.hide()
        self.login_button.setText("Connecting…")
        self.login_button.setEnabled(False)
        self.controller.login(username)

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()
        self.login_button.setText("Connect to Talkify  →")
        self.login_button.setEnabled(True)