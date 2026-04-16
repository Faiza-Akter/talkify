from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame


class RoomListItem(QWidget):
    def __init__(self, room_name):
        super().__init__()

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        icon_frame = QFrame()
        icon_frame.setObjectName("roomAvatar")
        icon_frame.setFixedSize(38, 38)

        icon_label = QLabel("#")
        icon_label.setObjectName("roomAvatarText")
        icon_label.setAlignment(Qt.AlignCenter)

        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = QLabel(room_name)
        title.setObjectName("roomItemTitle")

        subtitle = QLabel("Shared room")
        subtitle.setObjectName("roomItemSubtitle")

        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)

        root.addWidget(icon_frame)
        root.addLayout(text_layout)
        root.addStretch()