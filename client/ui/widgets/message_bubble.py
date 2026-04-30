from __future__ import annotations

import os
import re

try:
    import shiboken6
except Exception:
    shiboken6 = None

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFontMetrics, QPainter, QPainterPath, QPixmap, QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy, QToolButton

from client.ui.widgets.emoji_picker import EmojiPicker


class MessageBubble(QWidget):
    reply_requested = Signal(dict)
    local_delete_requested = Signal(str)
    reaction_requested = Signal(str, str)

    MIN_PRIVATE_WIDTH = 140
    MIN_GROUP_WIDTH = 140
    MAX_BUBBLE_WIDTH = 430
    LONG_TEXT_WIDTH = 360
    REACTION_BADGE_HEIGHT = 24

    def __init__(self, message_data, own=False, avatar_path="", show_sender=True, compact_private=False):
        super().__init__()
        self.message_data = message_data
        self.own = own
        self.show_sender = show_sender
        self.compact_private = compact_private
        self.deleted = bool(message_data.get("deleted", False))
        self.reactions = dict(message_data.get("reactions", {}))

        # local UI tracking only; true per-client sync needs chat_window/server changes
        self.my_reaction = message_data.get("my_reaction", "")

        # Must exist for both own and other messages.
        self.reaction_picker = None

        self._is_destroyed = False
        self.destroyed.connect(self._mark_destroyed)

        self.setObjectName("messageRowOwn" if own else "messageRowOther")
        self.setMouseTracking(True)

        self.root_layout = QHBoxLayout(self)
        top_gap = 10 if show_sender else 1
        bottom_gap = 2

        self.root_layout.setContentsMargins(8, top_gap, 8, bottom_gap)
        self.root_layout.setSpacing(6)

        # FIX:
        # Do not create an unused avatar QLabel for own/private-compact messages.
        # Unused parentless avatar widgets can briefly appear as floating windows.
        self.avatar_label = None

        if not own and not compact_private:
            self.avatar_label = QLabel()
            self.avatar_label.setObjectName("messageAvatar")
            self.avatar_label.setAlignment(Qt.AlignCenter)
            self.avatar_label.setFixedSize(34, 34)
            self._set_avatar(avatar_path, message_data.get("sender", "?"))

        self.actions = QFrame()
        self.actions.setObjectName("messageActionsRail")
        self.actions.setFixedWidth(98 if own else 92)
        self.actions.setMouseTracking(True)

        actions_layout = QHBoxLayout(self.actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)

        self.reply_btn = self._make_action_button("reply.svg", "Reply")
        self.reply_btn.clicked.connect(lambda: self.reply_requested.emit(self.message_data))

        self.react_btn = self._make_action_button("smile-plus.svg", "React")
        self.react_btn.clicked.connect(self._show_reaction_picker)

        self.delete_btn = self._make_action_button("trash.svg", "Delete for everyone")
        self.delete_btn.clicked.connect(self._request_delete)

        actions_layout.addWidget(self.reply_btn)
        actions_layout.addWidget(self.react_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()

        self.bubble_column = QWidget()
        self.bubble_column.setObjectName("messageBubbleColumn")
        self.bubble_column.setMouseTracking(True)

        self.bubble_column_layout = QVBoxLayout(self.bubble_column)
        self.bubble_column_layout.setContentsMargins(0, 0, 0, 0)
        self.bubble_column_layout.setSpacing(0)

        self.bubble = QFrame()
        self.bubble.setObjectName("messageBubbleOwn" if own else "messageBubbleOther")
        self.bubble.setMouseTracking(True)

        self.bubble_layout = QVBoxLayout(self.bubble)
        self.bubble_layout.setContentsMargins(9, 3, 9, 3)
        self.bubble_layout.setSpacing(1)

        self.sender_label = QLabel("You" if own else message_data.get("sender", "Unknown"))
        self.sender_label.setObjectName("messageSenderOwn" if own else "messageSenderOther")
        self.sender_label.setVisible((show_sender and not compact_private) and not self.deleted)

        reply_to = message_data.get("reply_to")
        self.reply_box = None

        if reply_to and not self.deleted:
            self.reply_box = QFrame()
            self.reply_box.setObjectName("replyPreviewBox")

            reply_layout = QVBoxLayout(self.reply_box)
            reply_layout.setContentsMargins(7, 3, 7, 3)
            reply_layout.setSpacing(2)

            reply_sender = QLabel(reply_to.get("sender", "Reply"))
            reply_sender.setObjectName("replySenderLabel")

            reply_text = QLabel(self._break_long_words(reply_to.get("message", ""), chunk=34))
            reply_text.setObjectName("replyTextLabel")
            reply_text.setWordWrap(True)

            reply_layout.addWidget(reply_sender)
            reply_layout.addWidget(reply_text)

        self.text_label = QLabel(self._display_text(wrap=True))
        self.text_label.setObjectName("messageTextDeleted" if self.deleted else "messageText")
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(2)

        self.time_label = QLabel(message_data.get("timestamp", ""))
        self.time_label.setObjectName("messageMeta")

        self.status_label = QLabel(self._status_to_symbol(message_data.get("status", "")))
        self.status_label.setObjectName("messageStatus")

        meta_row.addStretch()
        meta_row.addWidget(self.time_label)

        if own and message_data.get("status") and not self.deleted:
            meta_row.addWidget(self.status_label)

        if self.sender_label.isVisible():
            self.bubble_layout.addWidget(self.sender_label)
            self.bubble_layout.addSpacing(1)

        if self.reply_box:
            self.bubble_layout.addWidget(self.reply_box)
            self.bubble_layout.addSpacing(3)

        self.bubble_layout.addWidget(self.text_label)
        self.bubble_layout.addLayout(meta_row)

        self.bubble_column_layout.addWidget(self.bubble)

        self.reactions_label = QLabel("", self.bubble_column)
        self.reactions_label.setObjectName("messageReactions")
        self.reactions_label.setAlignment(Qt.AlignCenter)
        self.reactions_label.hide()
        self.reactions_label.raise_()

        self._apply_content_width()
        self.bubble.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.text_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self._refresh_reactions()
        self._set_actions_visible(False)

        if own:
            self.root_layout.addStretch()
            self.root_layout.addWidget(self.actions, alignment=Qt.AlignVCenter)
            self.root_layout.addWidget(self.bubble_column, alignment=Qt.AlignTop)
        else:
            if not compact_private:
                if show_sender and self.avatar_label is not None:
                    self.root_layout.addWidget(self.avatar_label, alignment=Qt.AlignTop)
                elif self.avatar_label is not None:
                    self.avatar_label.setText("")
                    self.avatar_label.setPixmap(QPixmap())
                    self.avatar_label.setStyleSheet("background: transparent; border: none;")
                    self.root_layout.addWidget(self.avatar_label, alignment=Qt.AlignTop)

            self.root_layout.addWidget(self.bubble_column, alignment=Qt.AlignTop)
            self.root_layout.addWidget(self.actions, alignment=Qt.AlignVCenter)
            self.root_layout.addStretch()

    def _mark_destroyed(self, *_args):
        self._is_destroyed = True

    def _is_valid_widget(self, widget) -> bool:
        if widget is None or self._is_destroyed:
            return False

        if shiboken6 is not None:
            try:
                return shiboken6.isValid(widget)
            except RuntimeError:
                return False

        return True

    def _make_reaction_picker(self):
        try:
            return EmojiPicker(reaction_only=True, parent=self)
        except TypeError:
            return EmojiPicker(parent=self)

    def _break_long_words(self, text: str, chunk: int = 18) -> str:
        if not text:
            return ""

        def add_soft_breaks(match):
            token = match.group(0)
            return "\u200b".join(token)

        return re.sub(r"\S{%d,}" % chunk, add_soft_breaks, str(text))

    def _apply_content_width(self):
        font_metrics = QFontMetrics(self.text_label.font())
        sender_metrics = QFontMetrics(self.sender_label.font())

        text = self._display_text(wrap=False) or " "
        lines = text.splitlines() or [text]

        content_width = max(font_metrics.horizontalAdvance(line) for line in lines)
        sender_width = sender_metrics.horizontalAdvance(self.sender_label.text()) if self.sender_label.isVisible() else 0

        reply_width = 0
        reply_to = self.message_data.get("reply_to")

        if isinstance(reply_to, dict):
            reply_width = max(
                190,
                font_metrics.horizontalAdvance(reply_to.get("sender", "")) + 34,
                font_metrics.horizontalAdvance(reply_to.get("message", "")[:45]) + 34,
            )

        meta_width = font_metrics.horizontalAdvance(self.time_label.text()) + (28 if self.own else 8)
        minimum = self.MIN_PRIVATE_WIDTH if self.compact_private else self.MIN_GROUP_WIDTH

        desired = max(
            minimum,
            min(content_width + 38, self.MAX_BUBBLE_WIDTH),
            sender_width + 34,
            min(reply_width + 38, self.LONG_TEXT_WIDTH),
            meta_width + 18,
        )

        if len(text) > 42 or content_width > self.LONG_TEXT_WIDTH:
            desired = max(desired, self.LONG_TEXT_WIDTH)

        desired = min(self.MAX_BUBBLE_WIDTH, desired)

        self.bubble.setFixedWidth(desired)
        self.bubble_column.setFixedWidth(desired + 8)
        self.text_label.setMaximumWidth(max(120, desired - 30))

        if self.reply_box:
            self.reply_box.setFixedWidth(max(170, desired - 24))

    def _make_action_button(self, icon_name, tooltip):
        button = QToolButton()
        button.setToolTip(tooltip)

        # Keep the same object name so existing logic still works,
        # but override the visual style here so only the icon is visible.
        button.setObjectName("messageActionButton")
        button.setFixedSize(28, 28)
        button.setCursor(Qt.PointingHandCursor)

        icon_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "assets",
            "icons",
            icon_name,
        )

        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(18, 18))
        button.setText("")

        button.setStyleSheet("""
            QToolButton#messageActionButton {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }

            QToolButton#messageActionButton:hover {
                background: transparent;
                border: none;
            }

            QToolButton#messageActionButton:pressed {
                background: transparent;
                border: none;
            }
        """)

        return button

    def _set_actions_visible(self, visible: bool):
        can_use = visible and not self.deleted
        self.reply_btn.setVisible(can_use)
        self.react_btn.setVisible(can_use)
        self.delete_btn.setVisible(can_use and self.own)

    def _set_avatar(self, avatar_path: str, sender: str):
        if self.avatar_label is None:
            return

        if avatar_path and os.path.exists(avatar_path):
            pixmap = self._make_round_pixmap(avatar_path, 34)

            if not pixmap.isNull():
                self.avatar_label.setPixmap(pixmap)
                return

        self.avatar_label.setText((sender or "?")[:1].upper())

    def _make_round_pixmap(self, image_path: str, size: int) -> QPixmap:
        original = QPixmap(image_path)

        if original.isNull():
            return QPixmap()

        scale = 2
        target = size * scale

        scaled = original.scaled(
            target,
            target,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        x = max(0, (scaled.width() - target) // 2)
        y = max(0, (scaled.height() - target) // 2)
        cropped = scaled.copy(x, y, target, target)

        rounded = QPixmap(target, target)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        path = QPainterPath()
        path.addEllipse(0, 0, target, target)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()

        rounded.setDevicePixelRatio(scale)
        return rounded

    def _display_text(self, wrap: bool = False):
        text = "This message was deleted" if self.deleted else self.message_data.get("message", "")
        return self._break_long_words(text) if wrap else text

    def _request_delete(self):
        message_id = self.message_data.get("message_id")

        if message_id:
            self.local_delete_requested.emit(message_id)

    def _show_reaction_picker(self):
        if self.deleted:
            return

        if self.reaction_picker is None:
            self.reaction_picker = self._make_reaction_picker()
            self.reaction_picker.emoji_selected.connect(self._pick_reaction)

        if hasattr(self.reaction_picker, "show_near"):
            self.reaction_picker.show_near(self.react_btn, above=True)
        else:
            pos = self.react_btn.mapToGlobal(self.react_btn.rect().bottomLeft())
            self.reaction_picker.move(pos)
            self.reaction_picker.show()

    def _pick_reaction(self, emoji):
        if self.reaction_picker is not None:
            self.reaction_picker.hide()

        message_id = self.message_data.get("message_id")
        if not message_id:
            return

        if self.my_reaction == emoji:
            emitted_emoji = ""
            self._remove_local_reaction(emoji)
            self.my_reaction = ""
        else:
            if self.my_reaction:
                self._remove_local_reaction(self.my_reaction)

            self.my_reaction = emoji
            self.reactions[emoji] = self.reactions.get(emoji, 0) + 1
            emitted_emoji = emoji

        self.message_data["my_reaction"] = self.my_reaction
        self.message_data["reactions"] = dict(self.reactions)
        self._refresh_reactions()

        self.reaction_requested.emit(message_id, emitted_emoji)

    def _remove_local_reaction(self, emoji: str):
        if not emoji:
            return

        current = self.reactions.get(emoji, 0)

        if current <= 1:
            self.reactions.pop(emoji, None)
        else:
            self.reactions[emoji] = current - 1

    def apply_reaction(self, emoji: str, count: int | None = None):
        if self.deleted:
            return

        # Empty emoji means remove/undo local reaction.
        if not emoji:
            if self.my_reaction:
                self._remove_local_reaction(self.my_reaction)
                self.my_reaction = ""
                self.message_data["my_reaction"] = ""
                self.message_data["reactions"] = dict(self.reactions)
                self._refresh_reactions()
            return

        if count is None:
            self.reactions[emoji] = self.reactions.get(emoji, 0) + 1
        else:
            if count <= 0:
                self.reactions.pop(emoji, None)
            else:
                self.reactions[emoji] = count

        self.message_data["reactions"] = dict(self.reactions)
        self._refresh_reactions()

    def _refresh_reactions(self):
        if not self._is_valid_widget(getattr(self, "reactions_label", None)):
            return

        parts = [(emoji, count) for emoji, count in self.reactions.items() if count]

        if not parts or self.deleted:
            try:
                self.reactions_label.clear()
                self.reactions_label.hide()
            except RuntimeError:
                pass

            self.bubble_column_layout.setContentsMargins(0, 0, 0, 0)
            return

        emojis = "".join(emoji for emoji, _ in parts[:4])
        total = sum(count for _, count in parts)

        if total <= 1 and len(parts) == 1:
            text = emojis
        else:
            text = f"{emojis} {total}"

        self.reactions_label.setText(text)
        self.reactions_label.show()
        self.reactions_label.raise_()

        # Keeps enough room under bubble so badge does not cut
        self.bubble_column_layout.setContentsMargins(0, 0, 0, 12)

        self._position_reactions()

    def _position_reactions(self):
        if not self._is_valid_widget(getattr(self, "reactions_label", None)):
            return

        try:
            if not self.reactions_label.isVisible():
                return

            parts = [(emoji, count) for emoji, count in self.reactions.items() if count]
            unique_count = len(parts)
            total = sum(count for _, count in parts)

            # Better compact sizing
            if unique_count == 1 and total == 1:
                badge_width = 28
                badge_height = 26
            elif unique_count == 1:
                badge_width = 52
                badge_height = 26
            elif unique_count == 2:
                badge_width = 68
                badge_height = 26
            elif unique_count == 3:
                badge_width = 82
                badge_height = 26
            else:
                badge_width = 96
                badge_height = 26

            self.reactions_label.setFixedSize(badge_width, badge_height)

            x = 14
            y = self.bubble.height() - (badge_height // 2)

            self.reactions_label.move(x, y)
            self.reactions_label.raise_()

        except RuntimeError:
            return

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_reactions()

    def showEvent(self, event):
        super().showEvent(event)
        self._position_reactions()

    def mark_deleted(self):
        self.deleted = True
        self.message_data["deleted"] = True
        self.message_data["message"] = "This message was deleted"

        self.text_label.setText("This message was deleted")
        self.text_label.setObjectName("messageTextDeleted")
        self.text_label.style().unpolish(self.text_label)
        self.text_label.style().polish(self.text_label)

        self.sender_label.setVisible(False)

        if self.reply_box:
            self.reply_box.hide()

        self.reactions.clear()
        self.my_reaction = ""
        self.message_data["reactions"] = {}
        self.message_data["my_reaction"] = ""

        self._refresh_reactions()
        self._set_actions_visible(False)
        self._apply_content_width()

    def _status_to_symbol(self, status):
        status = str(status).lower().strip()

        if status in ["sent", "send", "delivered", "received", "seen", "read"]:
            return "✓✓"

        return status

    def update_status(self, status):
        if self.status_label:
            self.message_data["status"] = status
            self.status_label.setText(self._status_to_symbol(status))

    def enterEvent(self, event):
        self._set_actions_visible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_actions_visible(False)
        super().leaveEvent(event)