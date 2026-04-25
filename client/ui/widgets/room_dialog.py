from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class RoomDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Join Room')
        self.setModal(True)
        self.setObjectName('roomDialog')
        self.resize(340, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel('Enter a room name to join or create')
        title.setObjectName('dialogTitle')

        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText('e.g. project-room')

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(self.room_input)
        layout.addStretch()
        layout.addWidget(buttons)
