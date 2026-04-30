import os

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, QRect
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class SplashScreen(QWidget):
    def __init__(self, on_finish=None) -> None:
        super().__init__()

        self.on_finish = on_finish
        self._finished = False

        self.setWindowTitle('Talkify')
        self.setFixedSize(760, 430)

        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.Tool, True)

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self._build_ui()
        self._play_intro()

        self.finish_timer = QTimer(self)
        self.finish_timer.setSingleShot(True)
        self.finish_timer.timeout.connect(self._finish)
        self.finish_timer.start(1800)

    def _trim_transparent_padding(self, pixmap: QPixmap) -> QPixmap:
        image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)

        width = image.width()
        height = image.height()

        min_x = width
        min_y = height
        max_x = -1
        max_y = -1

        for y in range(height):
            for x in range(width):
                alpha = image.pixelColor(x, y).alpha()

                if alpha > 10:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x == -1 or max_y == -1:
            return pixmap

        rect = QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        return pixmap.copy(rect)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)

        self.card = QFrame()
        self.card.setObjectName('splashCard')

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(0)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)

        logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo1.png')

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = self._trim_transparent_padding(pixmap)

            pixmap = pixmap.scaled(
                150,
                150,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

            logo.setPixmap(pixmap)

        self.title_label = QLabel('Talkify')
        self.title_label.setObjectName('splashTitle')
        self.title_label.setAlignment(Qt.AlignCenter)

        subtitle = QLabel('Client-server realtime desktop chat experience')
        subtitle.setObjectName('splashSubtitle')
        subtitle.setAlignment(Qt.AlignCenter)

        self.progress_label = QLabel('Loading interface...')
        self.progress_label.setObjectName('splashFooter')
        self.progress_label.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(logo)
        layout.addSpacing(4)
        layout.addWidget(self.title_label)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(22)
        layout.addWidget(self.progress_label)
        layout.addStretch()

        root.addWidget(self.card)

        self.dot_timer = QTimer(self)
        self.dot_timer.timeout.connect(self._animate_dots)
        self.dot_timer.start(350)

        self._dots = 0

    def _animate_dots(self) -> None:
        self._dots = (self._dots + 1) % 4
        self.progress_label.setText('Loading interface' + '.' * self._dots)

    def _play_intro(self) -> None:
        self.anim = QPropertyAnimation(self, b'windowOpacity')
        self.anim.setDuration(520)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def _finish(self) -> None:
        if self._finished:
            return

        self._finished = True

        if hasattr(self, 'finish_timer') and self.finish_timer.isActive():
            self.finish_timer.stop()

        if hasattr(self, 'dot_timer') and self.dot_timer.isActive():
            self.dot_timer.stop()

        callback = self.on_finish
        self.on_finish = None

        self.hide()

        if callback:
            callback()

        self.close()