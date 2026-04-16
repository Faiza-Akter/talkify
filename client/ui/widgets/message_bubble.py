from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget


class MessageBubble(QWidget):
    def __init__(self, sender, message, alignment="left", meta_text=""):
        super().__init__()

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 6, 12, 6)

        bubble = QFrame()
        bubble.setObjectName(
            "messageBubbleOwn" if alignment == "right" else "messageBubbleOther"
        )

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(6)

        sender_label = QLabel(sender)
        sender_label.setObjectName("messageSender")

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setObjectName("messageText")

        meta_label = QLabel(meta_text)
        meta_label.setAlignment(Qt.AlignRight)
        meta_label.setObjectName("messageMeta")

        bubble_layout.addWidget(sender_label)
        bubble_layout.addWidget(message_label)
        bubble_layout.addWidget(meta_label)

        bubble.setMaximumWidth(520)
        bubble.setMinimumWidth(120)

        if alignment == "right":
            root.addStretch()
            root.addWidget(bubble)
        else:
            root.addWidget(bubble)
            root.addStretch()