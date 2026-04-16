import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QFrame, QScrollArea,
    QMessageBox, QInputDialog
)

from client.controllers.chat_controller import ChatController
from client.ui.widgets.message_bubble import MessageBubble
from client.ui.widgets.user_list_item import UserListItem
from client.ui.widgets.room_list_item import RoomListItem


class ChatWindow(QWidget):
    def __init__(self, network_client, username, initial_room="General"):
        super().__init__()
        self.network_client = network_client
        self.username = username
        self.current_room = initial_room
        self.target_mode = "public"
        self.target_name = None

        self.controller = ChatController(self, network_client)

        self.setWindowTitle(f"Talkify - {username}")
        self.resize(1400, 860)
        self.setMinimumSize(1160, 760)

        self.build_ui()
        self.connect_signals()

    def build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        sidebar = QFrame()
        sidebar.setObjectName("sidebarPanel")
        sidebar.setFixedWidth(320)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(14)

        branding_card = QFrame()
        branding_card.setObjectName("brandCard")
        branding_layout = QHBoxLayout(branding_card)
        branding_layout.setContentsMargins(14, 14, 14, 14)

        logo = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pixmap)

        brand_text_layout = QVBoxLayout()
        brand_title = QLabel("Talkify")
        brand_title.setObjectName("brandTitle")
        brand_subtitle = QLabel("Soft-light modern messenger")
        brand_subtitle.setObjectName("brandSubtitle")
        brand_text_layout.addWidget(brand_title)
        brand_text_layout.addWidget(brand_subtitle)

        branding_layout.addWidget(logo)
        branding_layout.addLayout(brand_text_layout)
        branding_layout.addStretch()

        quick_card = QFrame()
        quick_card.setObjectName("sectionCard")
        quick_layout = QVBoxLayout(quick_card)
        quick_layout.setContentsMargins(14, 14, 14, 14)
        quick_layout.setSpacing(10)

        section1 = QLabel("Quick Access")
        section1.setObjectName("sectionTitle")

        self.public_button = QPushButton("Public Chat")
        self.public_button.clicked.connect(self.activate_public_mode)

        self.join_room_button = QPushButton("Join New Room")
        self.join_room_button.clicked.connect(self.join_new_room)

        quick_layout.addWidget(section1)
        quick_layout.addWidget(self.public_button)
        quick_layout.addWidget(self.join_room_button)

        users_card = QFrame()
        users_card.setObjectName("sectionCard")
        users_layout = QVBoxLayout(users_card)
        users_layout.setContentsMargins(14, 14, 14, 14)

        users_title = QLabel("Connected Users")
        users_title.setObjectName("sectionTitle")

        self.user_list = QListWidget()
        self.user_list.itemClicked.connect(self.select_private_user)

        users_layout.addWidget(users_title)
        users_layout.addWidget(self.user_list)

        rooms_card = QFrame()
        rooms_card.setObjectName("sectionCard")
        rooms_layout = QVBoxLayout(rooms_card)
        rooms_layout.setContentsMargins(14, 14, 14, 14)

        rooms_title = QLabel("Rooms")
        rooms_title.setObjectName("sectionTitle")

        self.room_list = QListWidget()
        self.room_list.itemClicked.connect(self.select_room)

        rooms_layout.addWidget(rooms_title)
        rooms_layout.addWidget(self.room_list)

        sidebar_layout.addWidget(branding_card)
        sidebar_layout.addWidget(quick_card)
        sidebar_layout.addWidget(users_card, 1)
        sidebar_layout.addWidget(rooms_card, 1)

        main_panel = QFrame()
        main_panel.setObjectName("chatMainPanel")

        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        topbar = QFrame()
        topbar.setObjectName("chatTopbar")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(18, 16, 18, 16)

        header_layout = QVBoxLayout()
        self.chat_title = QLabel("Public Chat")
        self.chat_title.setObjectName("chatTitle")

        self.chat_subtitle = QLabel(f"Logged in as {self.username}")
        self.chat_subtitle.setObjectName("chatSubtitle")

        header_layout.addWidget(self.chat_title)
        header_layout.addWidget(self.chat_subtitle)

        status_chip = QLabel("Online")
        status_chip.setObjectName("statusChip")

        topbar_layout.addLayout(header_layout)
        topbar_layout.addStretch()
        topbar_layout.addWidget(status_chip)

        if self.username.lower() == "admin":
            self.kick_button = QPushButton("Kick User")
            self.kick_button.clicked.connect(self.kick_selected_user)

            self.ban_button = QPushButton("Ban User")
            self.ban_button.clicked.connect(self.ban_selected_user)

            topbar_layout.addWidget(self.kick_button)
            topbar_layout.addWidget(self.ban_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("chatScrollArea")

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)

        composer_card = QFrame()
        composer_card.setObjectName("composerCard")
        composer_layout = QVBoxLayout(composer_card)
        composer_layout.setContentsMargins(16, 16, 16, 16)
        composer_layout.setSpacing(10)

        self.context_label = QLabel("Sending to: Public Chat")
        self.context_label.setObjectName("contextLabel")

        input_row = QHBoxLayout()
        input_row.setSpacing(12)

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.setFixedHeight(92)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primaryButton")
        self.send_button.setFixedWidth(130)
        self.send_button.clicked.connect(self.send_message)

        input_row.addWidget(self.message_input, 1)
        input_row.addWidget(self.send_button)

        composer_layout.addWidget(self.context_label)
        composer_layout.addLayout(input_row)

        main_layout.addWidget(topbar)
        main_layout.addWidget(self.scroll_area, 1)
        main_layout.addWidget(composer_card)

        root.addWidget(sidebar)
        root.addWidget(main_panel, 1)

    def connect_signals(self):
        self.network_client.public_message_received.connect(self.on_public_message)
        self.network_client.private_message_received.connect(self.on_private_message)
        self.network_client.room_message_received.connect(self.on_room_message)
        self.network_client.join_notice_received.connect(self.on_notice)
        self.network_client.leave_notice_received.connect(self.on_notice)
        self.network_client.user_list_received.connect(self.update_user_list)
        self.network_client.room_list_received.connect(self.update_room_list)
        self.network_client.room_joined.connect(self.on_room_joined)
        self.network_client.error_received.connect(self.show_error)
        self.network_client.admin_response_received.connect(self.show_info)
        self.network_client.disconnected.connect(self.on_disconnected)

    def current_time(self):
        return datetime.now().strftime("%H:%M")

    def add_message_bubble(self, sender, message, own=False):
        bubble = MessageBubble(
            sender=sender,
            message=message,
            alignment="right" if own else "left",
            meta_text=self.current_time()
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def add_system_notice(self, text):
        notice = QLabel(text)
        notice.setObjectName("systemNotice")
        notice.setAlignment(Qt.AlignCenter)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, notice)

    def activate_public_mode(self):
        self.target_mode = "public"
        self.target_name = None
        self.chat_title.setText("Public Chat")
        self.context_label.setText("Sending to: Public Chat")

    def select_private_user(self, item):
        selected_user = item.data(Qt.UserRole)
        if not selected_user or selected_user == self.username:
            return

        self.target_mode = "private"
        self.target_name = selected_user
        self.chat_title.setText(f"Private Chat • {selected_user}")
        self.context_label.setText(f"Sending to: Private User ({selected_user})")

    def select_room(self, item):
        room_name = item.data(Qt.UserRole)
        if not room_name:
            return

        self.target_mode = "room"
        self.target_name = room_name
        self.current_room = room_name
        self.chat_title.setText(f"Room • {room_name}")
        self.context_label.setText(f"Sending to: Room ({room_name})")

    def join_new_room(self):
        room_name, ok = QInputDialog.getText(self, "Join Room", "Enter room name:")
        if ok and room_name.strip():
            self.network_client.join_room(room_name.strip())

    def send_message(self):
        message = self.message_input.toPlainText().strip()
        if not message:
            return

        self.controller.send_message(self.target_mode, self.target_name, message)

        if self.target_mode == "public":
            self.add_message_bubble("You", message, own=True)
        elif self.target_mode == "private":
            self.add_message_bubble(f"You → {self.target_name}", message, own=True)
        elif self.target_mode == "room":
            self.add_message_bubble(f"You @ {self.target_name}", message, own=True)

        self.message_input.clear()

    def on_public_message(self, packet):
        sender = packet.get("sender", "Unknown")
        if sender == self.username:
            return
        self.add_message_bubble(sender, packet.get("message", ""), own=False)

    def on_private_message(self, packet):
        sender = packet.get("sender", "Unknown")
        target = packet.get("target", "")
        if sender == self.username:
            return
        self.add_message_bubble(f"{sender} → {target}", packet.get("message", ""), own=False)

    def on_room_message(self, packet):
        sender = packet.get("sender", "Unknown")
        room = packet.get("room", "Room")
        if sender == self.username:
            return
        self.add_message_bubble(f"{sender} @ {room}", packet.get("message", ""), own=False)

    def on_notice(self, message):
        self.add_system_notice(message)

    def update_user_list(self, users):
        self.user_list.clear()
        for username in users:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, username)
            item.setSizeHint(self.user_list.sizeHintForIndex(self.user_list.model().index(0, 0)).expandedTo(item.sizeHint()))
            widget = UserListItem(username, is_self=(username == self.username))
            item.setSizeHint(widget.sizeHint())
            self.user_list.addItem(item)
            self.user_list.setItemWidget(item, widget)

    def update_room_list(self, rooms):
        self.room_list.clear()
        for room in rooms:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, room)
            widget = RoomListItem(room)
            item.setSizeHint(widget.sizeHint())
            self.room_list.addItem(item)
            self.room_list.setItemWidget(item, widget)

    def on_room_joined(self, message):
        self.add_system_notice(message)

    def show_error(self, message):
        QMessageBox.warning(self, "Talkify", message)

    def show_info(self, message):
        QMessageBox.information(self, "Talkify", message)

    def kick_selected_user(self):
        item = self.user_list.currentItem()
        if not item:
            self.show_error("Select a user first.")
            return

        target = item.data(Qt.UserRole)
        if target == self.username:
            self.show_error("You cannot kick yourself.")
            return

        self.network_client.kick_user(target)

    def ban_selected_user(self):
        item = self.user_list.currentItem()
        if not item:
            self.show_error("Select a user first.")
            return

        target = item.data(Qt.UserRole)
        if target == self.username:
            self.show_error("You cannot ban yourself.")
            return

        self.network_client.ban_user(target)

    def on_disconnected(self):
        QMessageBox.information(self, "Talkify", "Disconnected from server.")

    def closeEvent(self, event):
        self.network_client.disconnect()
        super().closeEvent(event)