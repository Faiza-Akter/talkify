from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class ProfileDialog(QDialog):
    def __init__(self, username: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Profile Settings')
        self.setModal(True)
        self.setObjectName('profileDialog')
        self.resize(360, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        heading = QLabel('Local profile customization')
        heading.setObjectName('dialogTitle')

        name_label = QLabel('Display name')
        self.name_input = QLineEdit(username)

        avatar_label = QLabel('Profile image path (optional)')
        self.avatar_input = QLineEdit()
        self.avatar_input.setPlaceholderText('Keep empty to use initial avatar')

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(heading)
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(avatar_label)
        layout.addWidget(self.avatar_input)
        layout.addStretch()
        layout.addWidget(buttons)
