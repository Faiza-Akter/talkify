from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget


class EmojiPicker(QWidget):
    emoji_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlag(self.windowFlags() | self.windowFlags().Popup)
        self.setObjectName('emojiPicker')

        emojis = ['😊', '😂', '😍', '🔥', '👍', '✅', '🎉', '😌', '❤️', '✨', '😎', '👋🏽']
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        for index, emoji in enumerate(emojis):
            button = QPushButton(emoji)
            button.setObjectName('emojiButton')
            button.setFixedSize(38, 38)
            button.clicked.connect(lambda checked=False, e=emoji: self.emoji_selected.emit(e))
            layout.addWidget(button, index // 4, index % 4)
