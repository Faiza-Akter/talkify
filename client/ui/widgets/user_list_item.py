from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame


class UserListItem(QWidget):
    def __init__(self, username, subtitle="Online", highlight=False):
        super().__init__()

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(10)

        avatar = QFrame()
        avatar.setObjectName("userAvatarHighlight" if highlight else "userAvatar")
        avatar.setFixedSize(36, 36)

        avatar_text = QLabel(username[:1].upper())
        avatar_text.setAlignment(Qt.AlignCenter)
        avatar_text.setObjectName("userAvatarText")

        avatar_layout = QVBoxLayout(avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.addWidget(avatar_text)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        title = QLabel(username)
        title.setObjectName("userItemTitle")

        sub = QLabel(subtitle)
        sub.setObjectName("userItemSubtitle")

        text_layout.addWidget(title)
        text_layout.addWidget(sub)

        root.addWidget(avatar)
        root.addLayout(text_layout)
        root.addStretch()