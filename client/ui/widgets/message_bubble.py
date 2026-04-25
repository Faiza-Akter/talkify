from PySide6.QtCore import Qt, Signal, QPropertyAnimation
from PySide6.QtWidgets import QMenu
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
    QGraphicsOpacityEffect,
)


class MessageBubble(QWidget):
    reply_requested = Signal(dict)
    local_delete_requested = Signal(str)

    def __init__(self, message_data, own=False):
        super().__init__()
        self.message_data = message_data
        self.own = own

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 2, 8, 2)
        root.setSpacing(4)

        container = QFrame()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(6)

        # Reply arrow button
        # Important: do NOT hide/show it, otherwise the bubble will shrink/jump.
        # We keep it in the layout and only change opacity.
        self.reply_btn = QLabel("↩")
        self.reply_btn.setObjectName("replyHoverIcon")
        self.reply_btn.setFixedSize(24, 24)
        self.reply_btn.setAlignment(Qt.AlignCenter)
        self.reply_btn.setToolTip("Reply")
        self.reply_btn.mousePressEvent = lambda event: self.reply_requested.emit(
            self.message_data
        )

        self.opacity_effect = QGraphicsOpacityEffect(self.reply_btn)
        self.reply_btn.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)

        self.reply_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.reply_anim.setDuration(140)

        self.bubble = QFrame()
        self.bubble.setObjectName("messageBubbleOwn" if own else "messageBubbleOther")

        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(12, 5, 12, 5)
        bubble_layout.setSpacing(2)

        sender_label = QLabel("You" if own else message_data.get("sender", "Unknown"))
        sender_label.setObjectName("messageSenderOwn" if own else "messageSenderOther")

        reply_to = message_data.get("reply_to")
        if reply_to:
            reply_box = QFrame()
            reply_box.setObjectName("replyPreviewBox")

            reply_layout = QVBoxLayout(reply_box)
            reply_layout.setContentsMargins(8, 4, 8, 4)
            reply_layout.setSpacing(1)

            reply_sender = QLabel(reply_to.get("sender", "Reply"))
            reply_sender.setObjectName("replySenderLabel")

            reply_text = QLabel(reply_to.get("message", ""))
            reply_text.setObjectName("replyTextLabel")
            reply_text.setWordWrap(True)

            reply_layout.addWidget(reply_sender)
            reply_layout.addWidget(reply_text)
            bubble_layout.addWidget(reply_box)

        text_label = QLabel(message_data.get("message", ""))
        text_label.setObjectName("messageText")
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(4)

        time_label = QLabel(message_data.get("timestamp", ""))
        time_label.setObjectName("messageMeta")

        status_text = self._status_to_symbol(message_data.get("status", ""))
        status_label = QLabel(status_text)
        status_label.setObjectName("messageStatus")

        meta_row.addStretch()
        meta_row.addWidget(time_label)

        if own and message_data.get("status"):
            meta_row.addSpacing(6)
            meta_row.addWidget(status_label)

        bubble_layout.addWidget(sender_label)
        bubble_layout.addWidget(text_label)
        bubble_layout.addLayout(meta_row)

        self.bubble.setMaximumWidth(520)
        self.bubble.setMinimumWidth(130)
        self.bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        text_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        if own:
            container_layout.addStretch()
            container_layout.addWidget(self.reply_btn, alignment=Qt.AlignVCenter)
            container_layout.addWidget(self.bubble, alignment=Qt.AlignTop)
        else:
            container_layout.addWidget(self.bubble, alignment=Qt.AlignTop)
            container_layout.addWidget(self.reply_btn, alignment=Qt.AlignVCenter)
            container_layout.addStretch()

        root.addWidget(container)

        self.status_label = status_label if own else None


    def contextMenuEvent(self, event):
        if not self.own:
            return  
        menu = QMenu(self)

        delete_action = menu.addAction("Delete for everyone")

        action = menu.exec(event.globalPos())

        if action == delete_action:
            message_id = self.message_data.get("message_id")
            if message_id:
                self.local_delete_requested.emit(message_id)

    def _status_to_symbol(self, status):
        status = str(status).lower().strip()

        if status in ["sent", "send"]:
            return "✓✓"

        if status in ["delivered", "received"]:
            return "✓✓"

        if status in ["seen", "read"]:
            return "✓✓"

        return status

    def update_status(self, status):
        if self.status_label:
            self.status_label.setText(self._status_to_symbol(status))

    def _animate_reply_icon(self, end_value):
        self.reply_anim.stop()
        self.reply_anim.setStartValue(self.opacity_effect.opacity())
        self.reply_anim.setEndValue(end_value)
        self.reply_anim.start()

    def enterEvent(self, event):
        self._animate_reply_icon(1)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_reply_icon(0)
        super().leaveEvent(event)