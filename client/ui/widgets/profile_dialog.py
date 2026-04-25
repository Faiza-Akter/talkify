from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class ProfileDialog(QDialog):
    def __init__(self, username: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profile Settings")
        self.setModal(True)
        self.setObjectName("profileDialog")
        self.resize(420, 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        heading = QLabel("Profile customization")
        heading.setObjectName("dialogTitle")

        name_label = QLabel("Display name")
        self.name_input = QLineEdit(username)

        avatar_label = QLabel("Profile picture")

        avatar_row = QHBoxLayout()
        self.avatar_input = QLineEdit()
        self.avatar_input.setPlaceholderText("Choose an image from your device")

        browse_button = QPushButton("Browse")
        browse_button.setObjectName("ghostToolButton")
        browse_button.clicked.connect(self._browse_avatar)

        avatar_row.addWidget(self.avatar_input, 1)
        avatar_row.addWidget(browse_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(heading)
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(avatar_label)
        layout.addLayout(avatar_row)
        layout.addStretch()
        layout.addWidget(buttons)

    def _browse_avatar(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Profile Picture",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )

        if file_path:
            self.avatar_input.setText(file_path)