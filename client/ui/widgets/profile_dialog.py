import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout,
)


class ProfileDialog(QDialog):
    def __init__(self, username: str, avatar_path: str = "", parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Profile Settings")
        self.setModal(True)
        self.setObjectName("profileDialog")
        self.setFixedSize(520, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("dialogHeroCard")

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 10, 20, 18)
        hero_layout.setSpacing(16)

        self.avatar_preview = QLabel(username[:1].upper())
        self.avatar_preview.setObjectName("profilePreviewAvatar")
        self.avatar_preview.setAlignment(Qt.AlignCenter)
        self.avatar_preview.setFixedSize(70, 70)

        if avatar_path:
            self._set_avatar_preview(avatar_path)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(5)

        heading = QLabel("Edit Profile")
        heading.setObjectName("dialogTitle")

        helper = QLabel("Personalize your display name and profile picture.")
        helper.setObjectName("dialogHint")
        helper.setWordWrap(True)

        hero_text.addWidget(heading)
        hero_text.addWidget(helper)

        hero_layout.addWidget(self.avatar_preview, alignment=Qt.AlignVCenter)
        hero_layout.addLayout(hero_text, 1)

        form_card = QFrame()
        form_card.setObjectName("dialogGlassCard")

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)

        name_label = QLabel("DISPLAY NAME")
        name_label.setObjectName("fieldLabel")

        self.name_input = QLineEdit(username)
        self.name_input.setObjectName("profileInput")
        self.name_input.setPlaceholderText("Enter your display name")
        self.name_input.setFixedHeight(46)

        avatar_label = QLabel("PROFILE PICTURE")
        avatar_label.setObjectName("fieldLabel")

        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(10)

        self.avatar_input = QLineEdit()
        self.avatar_input.setObjectName("profileInput")
        self.avatar_input.setPlaceholderText("No image selected")
        self.avatar_input.setFixedHeight(46)

        if avatar_path:
            self.avatar_input.setText(avatar_path)

        browse_button = QPushButton("Browse")
        browse_button.setObjectName("ghostToolButton")
        browse_button.setFixedSize(92, 38)
        browse_button.clicked.connect(self._browse_avatar)

        avatar_row.addWidget(self.avatar_input, 1)
        avatar_row.addWidget(browse_button)

        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addSpacing(6)
        form_layout.addWidget(avatar_label)
        form_layout.addLayout(avatar_row)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 2, 0, 0)
        actions.setSpacing(10)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("ghostToolButton")
        self.cancel_button.setFixedSize(88, 40)
        self.cancel_button.clicked.connect(self.reject)

        self.ok_button = QPushButton("Save Changes")
        self.ok_button.setObjectName("primaryButton")
        self.ok_button.setFixedSize(136, 38)
        self.ok_button.clicked.connect(self.accept)

        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.ok_button)
        actions.addStretch()

        root.addWidget(hero)
        root.addWidget(form_card)
        root.addStretch()
        root.addLayout(actions)

    def _browse_avatar(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Profile Picture",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )

        if file_path:
            self.avatar_input.setText(file_path)
            self._set_avatar_preview(file_path)

    def _set_avatar_preview(self, image_path: str) -> None:
        if not image_path or not os.path.exists(image_path):
            return

        pixmap = self._make_round_pixmap(image_path, 70)

        if not pixmap.isNull():
            self.avatar_preview.setText("")
            self.avatar_preview.setPixmap(pixmap)

    def _make_round_pixmap(self, image_path: str, size: int) -> QPixmap:
        original = QPixmap(image_path)

        if original.isNull():
            return QPixmap()

        scale = 2
        target = size * scale

        scaled = original.scaled(
            target,
            target,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        x = max(0, (scaled.width() - target) // 2)
        y = max(0, (scaled.height() - target) // 2)
        cropped = scaled.copy(x, y, target, target)

        rounded = QPixmap(target, target)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        path = QPainterPath()
        path.addEllipse(0, 0, target, target)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()

        rounded.setDevicePixelRatio(scale)
        return rounded