from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame


class ChatListItem(QWidget):
    def __init__(self, title, subtitle, trailing="", active=False):
        super().__init__()

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        avatar = QFrame()
        avatar.setObjectName("chatAvatarActive" if active else "chatAvatar")
        avatar.setFixedSize(42, 42)

        avatar_text = QLabel(title[:1].upper())
        avatar_text.setAlignment(Qt.AlignCenter)
        avatar_text.setObjectName("chatAvatarText")

        avatar_layout = QVBoxLayout(avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.addWidget(avatar_text)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("chatItemTitle")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("chatItemSubtitle")
        subtitle_label.setWordWrap(False)

        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)

        trailing_label = QLabel(trailing)
        trailing_label.setObjectName("chatItemTrailing")
        trailing_label.setAlignment(Qt.AlignTop | Qt.AlignRight)

        root.addWidget(avatar)
        root.addLayout(text_layout, 1)
        root.addWidget(trailing_label)