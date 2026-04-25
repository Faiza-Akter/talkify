from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class InfoCard(QFrame):
    def __init__(self, title, value):
        super().__init__()
        self.setObjectName("infoCard")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("infoCardTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("infoCardValue")
        self.value_label.setWordWrap(True)

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.value_label)

    def set_value(self, title, value):
        self.title_label.setText(title)
        self.value_label.setText(value)