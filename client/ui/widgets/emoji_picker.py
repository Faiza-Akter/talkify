from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton, QWidget


class EmojiPicker(QWidget):
    emoji_selected = Signal(str)

    def __init__(self, reaction_only: bool = False, parent=None) -> None:
        super().__init__(parent)

        self.reaction_only = reaction_only

      
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.hide()
        self.setObjectName('reactionPicker' if reaction_only else 'emojiPicker')

        if reaction_only:
            emojis = ['👍', '❤️', '😂', '😮', '😢', '🙏']
            layout = QHBoxLayout(self)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(6)
        else:
            emojis = [
                '😊', '😂', '😍', '🥰', '😎', '😌',
                '😮', '😢', '👍', '👎', '👏', '🙏',
                '❤️', '💜', '✨', '🔥', '✅', '🎉',
                '🌟', '💬', '👋', '🤝', '🙌', '😉',
            ]

            layout = QGridLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(7)

        for index, emoji in enumerate(emojis):
            button = QPushButton(emoji)
            button.setObjectName('reactionEmojiButton' if reaction_only else 'emojiButton')

            size = 36 if reaction_only else 34
            button.setFixedSize(size, size)

            button.setStyleSheet("""
                QPushButton {
                    border-radius: 12px;
                }
            """)

            button.clicked.connect(lambda checked=False, e=emoji: self.emoji_selected.emit(e))

            if reaction_only:
                layout.addWidget(button)
            else:
                layout.addWidget(button, index // 6, index % 6)

    def show_near(self, anchor, above: bool = True) -> None:
        self.adjustSize()
        hint = self.sizeHint()

        anchor_center = anchor.mapToGlobal(anchor.rect().center())
        screen = QGuiApplication.screenAt(anchor_center) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None

        if above:
            point = anchor.mapToGlobal(anchor.rect().topRight())
            x = point.x() - hint.width()
            y = point.y() - hint.height() - 8
        else:
            point = anchor.mapToGlobal(anchor.rect().bottomRight())
            x = point.x() - hint.width()
            y = point.y() + 8

        if geo is not None:
            margin = 10
            x = max(geo.left() + margin, min(x, geo.right() - hint.width() - margin))
            y = max(geo.top() + margin, min(y, geo.bottom() - hint.height() - margin))

        self.move(x, y)
        self.show()
        self.raise_()