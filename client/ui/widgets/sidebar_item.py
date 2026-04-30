import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class SidebarItem(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str,
        trailing: str = "",
        avatar_text: str = "",
        accent: bool = False,
        online: bool = False,
        avatar_path: str = "",
        unread_count: int = 0,
    ) -> None:
        super().__init__()

        # Hide immediately so this widget never flashes as a top-level window
        # before setItemWidget() parents it into the QListWidget viewport.
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        # Pass self as parent to every child widget so Qt never treats
        # them as independent top-level windows during construction.
        avatar = QFrame(self)
        avatar.setObjectName("sidebarAvatarAccent" if accent else "sidebarAvatar")
        avatar.setFixedSize(38, 38)

        avatar_layout = QVBoxLayout(avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)

        avatar_label = QLabel(avatar)
        avatar_label.setObjectName("sidebarAvatarText")
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_label.setFixedSize(38, 38)

        if avatar_path and os.path.exists(avatar_path):
            avatar_label.setPixmap(self._make_round_pixmap(avatar_path, 38))
        else:
            avatar_label.setText((avatar_text or title[:1]).upper())

        avatar_layout.addWidget(avatar_label)

        text_col = QWidget(self)
        text_layout = QVBoxLayout(text_col)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)

        safe_title = title if len(title) <= 20 else title[:17] + "..."
        title_label = QLabel(safe_title, self)
        title_label.setObjectName("sidebarItemTitle")

        safe_subtitle = subtitle if len(subtitle) <= 34 else subtitle[:31] + "..."
        subtitle_label = QLabel(safe_subtitle, self)
        subtitle_label.setObjectName("sidebarItemSubtitle")
        subtitle_label.setWordWrap(False)
        subtitle_label.setTextInteractionFlags(Qt.NoTextInteraction)

        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)

        trailing_col = QWidget(self)
        trailing_layout = QVBoxLayout(trailing_col)
        trailing_layout.setContentsMargins(0, 0, 0, 0)
        trailing_layout.setSpacing(2)

        trailing_label = QLabel(trailing, self)
        trailing_label.setObjectName("sidebarItemTrailing")
        trailing_label.setAlignment(Qt.AlignRight | Qt.AlignTop)

        unread_label = QLabel(str(unread_count) if unread_count else "", self)
        unread_label.setObjectName("unreadBadge")
        unread_label.setAlignment(Qt.AlignCenter)
        unread_label.setFixedSize(22, 22)
        unread_label.setVisible(unread_count > 0)

        status_label = QLabel("● Online" if online else "", self)
        status_label.setObjectName("sidebarOnlineDot")
        status_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)

        trailing_layout.addWidget(trailing_label)
        trailing_layout.addWidget(unread_label, alignment=Qt.AlignRight)
        trailing_layout.addWidget(status_label)
        trailing_layout.addStretch()

        layout.addWidget(avatar)
        layout.addWidget(text_col, 1)
        layout.addWidget(trailing_col)

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