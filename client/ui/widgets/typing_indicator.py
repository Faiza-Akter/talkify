from PySide6.QtWidgets import QLabel, QFrame, QHBoxLayout


class TypingIndicator(QFrame):
    def __init__(self):
        super().__init__()
        self.setVisible(False)
        self.setStyleSheet("background: rgba(157,78,221,0.12); border-radius: 16px; padding: 6px 12px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self.label = QLabel("")
        self.label.setStyleSheet("color: #C084FC; font-size: 12px;")
        layout.addWidget(self.label)

    def show_typing(self, user):
        self.label.setText(f"✎ {user} is typing...")
        self.setVisible(True)

    def hide_typing(self):
        self.setVisible(False)