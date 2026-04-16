from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame


class UserListItem(QWidget):
    def __init__(self, username, is_self=False):
        super().__init__()

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        avatar = QFrame()
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(38, 38)

        initials = QLabel(username[:1].upper())
        initials.setObjectName("userAvatarText")
        initials.setAlignment(Qt.AlignCenter)

        avatar_layout = QVBoxLayout(avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.addWidget(initials)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        name_label = QLabel(username)
        name_label.setObjectName("userItemTitle")

        status_label = QLabel("You" if is_self else "Online")
        status_label.setObjectName("userItemSubtitle")

        text_layout.addWidget(name_label)
        text_layout.addWidget(status_label)

        root.addWidget(avatar)
        root.addLayout(text_layout)
        root.addStretch()