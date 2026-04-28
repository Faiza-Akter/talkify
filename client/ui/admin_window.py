from __future__ import annotations

from datetime import datetime
from typing import Optional
import os
import uuid
from PySide6.QtCore import QPoint, Qt, QTimer, QSize
from PySide6.QtGui import QGuiApplication, QPixmap, QPainter, QPainterPath
from client.ui.widgets.profile_dialog import ProfileDialog
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from client.controllers.chat_controller import ChatController
from client.ui.widgets.emoji_picker import EmojiPicker
from client.ui.widgets.message_bubble import MessageBubble
from client.ui.widgets.room_dialog import RoomDialog
from client.ui.widgets.sidebar_item import SidebarItem


class AdminWindow(QWidget):
    def __init__(self, network_client, username: str, initial_room: str = "General") -> None:
        super().__init__()
        self.setObjectName("appRoot")

        self.network_client = network_client
        self.username = username
        self.initial_room = initial_room
        self.controller = ChatController(network_client)

        self.target_mode = "public"
        self.target_name: Optional[str] = None
        self.reply_context: Optional[dict] = None

        self.online_users: list[str] = []
        self.user_profiles: dict[str, dict] = {}
        self.available_rooms: list[str] = [initial_room]
        self.banned_users: list[str] = []
        self.message_widgets: dict[str, QWidget] = {}

        self.typing_timer = QTimer(self)
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self._send_stop_typing)

        self.setWindowTitle(f"Talkify - Admin Panel")
        self._resize_to_screen()

        self._build_ui()
        self._connect_signals()

        if hasattr(self.network_client, "latest_users") and self.network_client.latest_users:
            self._update_user_list(self.network_client.latest_users)

        if hasattr(self.network_client, "latest_rooms") and self.network_client.latest_rooms:
            self._update_room_list(self.network_client.latest_rooms)

        if hasattr(self.network_client, "request_admin_data"):
            self.network_client.request_admin_data()

    def _resize_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        width = min(1480, int(screen.width() * 0.97))
        height = min(860, int(screen.height() * 0.92))
        self.resize(width, height)
        self.setMinimumSize(1200, 720)

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        self._build_sidebar()
        self._build_center_panel()
        self._build_admin_panel()

        self.sidebar_restore_button = QToolButton()
        self.sidebar_restore_button.setText("☰")
        self.sidebar_restore_button.setObjectName("sidebarToggleButton")
        self.sidebar_restore_button.setFixedSize(38, 34)
        self.sidebar_restore_button.setToolTip("Show sidebar")
        self.sidebar_restore_button.clicked.connect(self._toggle_sidebar)
        self.sidebar_restore_button.hide()

        root.addWidget(self.sidebar_restore_button, alignment=Qt.AlignTop)
        root.addWidget(self.sidebar)
        root.addWidget(self.center_panel, 1)
        root.addWidget(self.admin_panel)

    def _build_sidebar(self) -> None:
        self.sidebar = QFrame()
        self.sidebar.setObjectName("adminSidebarPanel")
        self.sidebar.setFixedWidth(300)

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(8)

        logo = QLabel()
        logo.setFixedSize(82, 82)
        logo.setAlignment(Qt.AlignCenter)

        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            logo.setPixmap(
                QPixmap(logo_path).scaled(
                    78,
                    78,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)

        subtitle = QLabel("ADMIN PANEL")
        subtitle.setObjectName("adminBrandSubtitle")

        brand_text.addStretch()
        brand_text.addWidget(subtitle)
        brand_text.addStretch()

        self.sidebar_toggle_button = QToolButton()
        self.sidebar_toggle_button.setText("☰")
        self.sidebar_toggle_button.setObjectName("sidebarToggleButton")
        self.sidebar_toggle_button.setFixedSize(38, 34)
        self.sidebar_toggle_button.setToolTip("Hide sidebar")
        self.sidebar_toggle_button.clicked.connect(self._toggle_sidebar)

        brand_row.addWidget(logo)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        brand_row.addWidget(self.sidebar_toggle_button, alignment=Qt.AlignTop)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("sidebarSearch")
        self.search_input.setPlaceholderText("Search chats, rooms or users")
        self.search_input.textChanged.connect(self._rebuild_sidebar_list)

        tabs = QHBoxLayout()
        tabs.setSpacing(8)

        self.chats_tab = self._make_tab("Chats", "chats")
        self.rooms_tab = self._make_tab("Rooms", "rooms")
        self.users_tab = self._make_tab("Users", "users")

        tabs.addWidget(self.chats_tab)
        tabs.addWidget(self.rooms_tab)
        tabs.addWidget(self.users_tab)

        self.current_filter = "chats"

        self.section_label = QLabel("Recent Chats")
        self.section_label.setObjectName("sidebarSectionTitle")

        self.sidebar_list = QListWidget()
        self.sidebar_list.setObjectName("sidebarList")
        self.sidebar_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sidebar_list.itemClicked.connect(self._on_sidebar_item_clicked)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)

        public_button = QPushButton("Public")
        public_button.clicked.connect(lambda: self._apply_target("public", None))

        room_button = QPushButton("Join Room")
        room_button.clicked.connect(self._open_room_dialog)

        quick_row.addWidget(public_button)
        quick_row.addWidget(room_button)

        user_card = QFrame()
        user_card.setObjectName("sidebarUserCard")

        user_layout = QHBoxLayout(user_card)
        user_layout.setContentsMargins(12, 12, 12, 12)
        user_layout.setSpacing(10)

        self.admin_avatar = QLabel(self.username[:1].upper())
        self.admin_avatar.setObjectName("bottomAvatar")
        self.admin_avatar.setAlignment(Qt.AlignCenter)
        self.admin_avatar.setFixedSize(52, 52)

        user_text = QVBoxLayout()
        user_text.setSpacing(0)

        self.admin_name_label = QLabel(self.username)
        self.admin_name_label.setObjectName("bottomUserName")

        role_label = QLabel("admin online")
        role_label.setObjectName("bottomUserStatus")

        user_text.addWidget(self.admin_name_label)
        user_text.addWidget(role_label)

        self.admin_profile_button = QToolButton()
        self.admin_profile_button.setText("Edit")
        self.admin_profile_button.setObjectName("ghostToolButton")
        self.admin_profile_button.clicked.connect(self._open_profile_dialog)

        user_layout.addWidget(self.admin_avatar)
        user_layout.addLayout(user_text)
        user_layout.addStretch()
        user_layout.addWidget(self.admin_profile_button)

        layout.addLayout(brand_row)
        layout.addWidget(self.search_input)
        layout.addLayout(tabs)
        layout.addWidget(self.section_label)
        layout.addWidget(self.sidebar_list, 1)
        layout.addLayout(quick_row)
        layout.addWidget(user_card)

        self._rebuild_sidebar_list()

    def _make_tab(self, text: str, filter_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setObjectName("filterButton")
        button.clicked.connect(lambda: self._set_filter(filter_name))
        if filter_name == "chats":
            button.setChecked(True)
        return button

    def _build_center_panel(self) -> None:
        self.center_panel = QFrame()
        self.center_panel.setObjectName("mainPanel")

        layout = QVBoxLayout(self.center_panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("chatHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 10, 18, 10)

        title_box = QVBoxLayout()
        self.target_badge = QLabel("PUBLIC LOBBY")
        self.target_badge.setObjectName("targetBadge")
        self.chat_title = QLabel("Public Chat")
        self.chat_title.setObjectName("chatTitle")
        self.chat_subtitle = QLabel("Everyone can see messages here")
        self.chat_subtitle.setObjectName("chatSubtitle")

        title_box.addWidget(self.target_badge)
        title_box.addWidget(self.chat_title)
        title_box.addWidget(self.chat_subtitle)

        self.header_status = QLabel("● Live")
        self.header_status.setObjectName("statusBadge")
        self.header_status.setAlignment(Qt.AlignCenter)
        self.header_status.setFixedSize(76, 34)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.header_status)

        self.reply_bar = QFrame()
        self.reply_bar.setObjectName("replyBar")
        reply_layout = QHBoxLayout(self.reply_bar)
        self.reply_label = QLabel("")
        self.reply_label.setObjectName("replyBarText")
        cancel = QPushButton("Cancel")
        cancel.setObjectName("ghostToolButton")
        cancel.clicked.connect(self._clear_reply)
        reply_layout.addWidget(self.reply_label)
        reply_layout.addStretch()
        reply_layout.addWidget(cancel)
        self.reply_bar.hide()

        self.messages_scroll = QScrollArea()
        self.messages_scroll.setObjectName("messagesScroll")
        self.messages_scroll.setWidgetResizable(True)

        self.messages_surface = QWidget()
        self.messages_surface.setObjectName("messagesSurface")
        self.messages_layout = QVBoxLayout(self.messages_surface)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(0)
        self.messages_layout.addStretch()

        self.messages_scroll.setWidget(self.messages_surface)

        composer = QFrame()
        composer.setObjectName("composerPanel")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(14, 8, 14, 8)
        composer_layout.setSpacing(6)

        top_row = QHBoxLayout()
        self.context_label = QLabel("Sending to: Public Chat")
        self.context_label.setObjectName("contextLabel")
        self.typing_label = QLabel("")
        self.typing_label.setObjectName("typingLabel")
        top_row.addWidget(self.context_label)
        top_row.addStretch()
        top_row.addWidget(self.typing_label)

        input_row = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText("Type your admin message here...")
        self.message_input.textChanged.connect(self._on_input_changed)
        self.message_input.returnPressed.connect(self.send_message)

        self.emoji_picker = EmojiPicker()
        self.emoji_picker.emoji_selected.connect(self._insert_emoji)

        emoji_button = QToolButton()
        emoji_button.setText("😀")
        emoji_button.setObjectName("roundToolButton")
        emoji_button.setFixedSize(52, 52)
        emoji_button.clicked.connect(self._toggle_emoji_picker)

        send_button = QPushButton("Send")
        send_button.setObjectName("primaryButton")
        send_button.setFixedSize(112, 42)
        send_button.clicked.connect(self.send_message)

        input_row.addWidget(self.message_input, 1)
        input_row.addWidget(emoji_button)
        input_row.addWidget(send_button)

        self.emoji_button = emoji_button

        composer_layout.addLayout(top_row)
        composer_layout.addLayout(input_row)

        layout.addWidget(header)
        layout.addWidget(self.reply_bar)
        layout.addWidget(self.messages_scroll, 1)
        layout.addWidget(composer)

    def _build_admin_panel(self) -> None:
        self.admin_panel = QFrame()
        self.admin_panel.setObjectName("adminRightPanel")
        self.admin_panel.setFixedWidth(330)

        layout = QVBoxLayout(self.admin_panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        users_card = self._make_admin_card("Online Users")
        users_layout = users_card.layout()
        self.admin_users_list = QListWidget()
        self.admin_users_list.setObjectName("adminMiniList")
        users_layout.addWidget(self.admin_users_list)

        banned_card = self._make_admin_card("Banned Users")
        banned_layout = banned_card.layout()
        self.banned_users_list = QListWidget()
        self.banned_users_list.setObjectName("adminMiniList")
        banned_layout.addWidget(self.banned_users_list)

        stats_card = self._make_admin_card("Server Stats")
        stats_layout = stats_card.layout()

        self.online_count_label = QLabel("Online Users: 0")
        self.online_count_label.setObjectName("adminStatLabel")
        self.room_count_label = QLabel("Active Rooms: 0")
        self.room_count_label.setObjectName("adminStatLabel")
        self.message_count_label = QLabel("Messages Today: 0")
        self.message_count_label.setObjectName("adminStatLabel")

        stats_layout.addWidget(self.online_count_label)
        stats_layout.addWidget(self.room_count_label)
        stats_layout.addWidget(self.message_count_label)

        layout.addWidget(users_card, 2)
        layout.addWidget(banned_card, 2)
        layout.addWidget(stats_card, 1)

    def _make_admin_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("adminToolCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        label = QLabel(title)
        label.setObjectName("adminPanelTitle")
        layout.addWidget(label)

        return card

    def _connect_signals(self) -> None:
        self.network_client.public_message_received.connect(self._on_public_message)
        self.network_client.private_message_received.connect(self._on_private_message)
        self.network_client.room_message_received.connect(self._on_room_message)
        self.network_client.join_notice_received.connect(self._on_notice)
        self.network_client.leave_notice_received.connect(self._on_notice)
        self.network_client.user_list_received.connect(self._update_user_list)
        self.network_client.room_list_received.connect(self._update_room_list)
        self.network_client.room_joined.connect(self._on_room_joined)
        self.network_client.admin_response_received.connect(self._show_info)
        self.network_client.error_received.connect(self._show_error)
        self.network_client.disconnected.connect(self._on_disconnected)

        if hasattr(self.network_client, "message_deleted"):
            self.network_client.message_deleted.connect(self._on_message_deleted)

        if hasattr(self.network_client, "admin_data_received"):
            self.network_client.admin_data_received.connect(self._on_admin_data_received)

        if hasattr(self.network_client, "typing_received"):
            self.network_client.typing_received.connect(self._on_typing_received)

    def _set_filter(self, filter_name: str) -> None:
        self.current_filter = filter_name
        self.chats_tab.setChecked(filter_name == "chats")
        self.rooms_tab.setChecked(filter_name == "rooms")
        self.users_tab.setChecked(filter_name == "users")

        self.section_label.setText(
            "Recent Chats" if filter_name == "chats"
            else "Available Rooms" if filter_name == "rooms"
            else "Online Users"
        )
        self._rebuild_sidebar_list()

    def _rebuild_sidebar_list(self) -> None:
        query = ""
        if hasattr(self, "search_input"):
            query = self.search_input.text().strip().lower()

        self.sidebar_list.clear()

        if self.current_filter == "chats":
            items = [
                ("public", "public", "Public Chat", "Chat with everyone"),
                (f"room:{self.initial_room.lower()}", "room", self.initial_room, "Room conversation"),
            ]
        elif self.current_filter == "rooms":
            items = [
                (f"room:{room.lower()}", "room", room, "Room conversation")
                for room in self.available_rooms
            ]
        else:
            items = [
                (f"user:{user.lower()}", "private", user, "Direct message")
                for user in self.online_users
            ]

        for key, mode, name, subtitle in items:
            if query and query not in f"{name} {subtitle}".lower():
                continue

            item = QListWidgetItem()
            item.setData(Qt.UserRole, {"mode": mode, "name": name})
            profile = self.user_profiles.get(name.lower(), {})
            avatar_path = profile.get("profile_picture", "")

            widget = SidebarItem(
                title=name,
                subtitle=subtitle,
                trailing="",
                avatar_text=name[:1],
                accent=(mode == "public"),
                online=False,
                avatar_path=avatar_path,
            )

            item.setSizeHint(widget.minimumSizeHint())
            self.sidebar_list.addItem(item)
            self.sidebar_list.setItemWidget(item, widget)

    def _on_sidebar_item_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        self._apply_target(data["mode"], None if data["mode"] == "public" else data["name"])

    def _apply_target(self, mode: str, target_name: Optional[str]) -> None:
        self.target_mode = mode
        self.target_name = target_name

        if mode == "public":
            self.target_badge.setText("PUBLIC LOBBY")
            self.chat_title.setText("Public Chat")
            self.chat_subtitle.setText("Everyone can see messages here")
            self.context_label.setText("Sending to: Public Chat")
        elif mode == "room":
            room = target_name or self.initial_room
            self.target_badge.setText("ROOM CHAT")
            self.chat_title.setText(room)
            self.chat_subtitle.setText("Room-based conversation")
            self.context_label.setText(f"Sending to: Room ({room})")
        else:
            person = target_name or "Direct Message"
            self.target_badge.setText("DIRECT MESSAGE")
            self.chat_title.setText(person)
            self.chat_subtitle.setText(f"Private conversation with {person}")
            self.context_label.setText(f"Sending to: Direct Message ({person})")

    def _toggle_sidebar(self) -> None:
        self.sidebar.setVisible(not self.sidebar.isVisible())

        if self.sidebar.isVisible():
            self.sidebar_toggle_button.show()
            self.sidebar_restore_button.hide()
        else:
            self.sidebar_toggle_button.hide()
            self.sidebar_restore_button.show()

    def _update_user_list(self, users: list) -> None:
        normalized = []
        self.user_profiles = {}

        for user in users:
            if isinstance(user, dict):
                username = user.get("username", "")
                if username:
                    normalized.append(username)
                    self.user_profiles[username.lower()] = user

            elif isinstance(user, str):
                normalized.append(user)
                self.user_profiles[user.lower()] = {
                    "username": user,
                    "online": True,
                    "is_admin": False,
                    "profile_picture": "default_avatar.png",
                }

        self.online_users = normalized
        self._rebuild_sidebar_list()
        self._rebuild_admin_users()
        self._update_stats()

    def _update_room_list(self, rooms: list[str]) -> None:
        self.available_rooms = rooms or [self.initial_room]
        self._rebuild_sidebar_list()
        self._update_stats()

    def _rebuild_admin_users(self) -> None:
        self.admin_users_list.clear()

        for username in self.online_users:
            item = QListWidgetItem()
            row = self._make_admin_user_row(username)

            item.setSizeHint(QSize(0, 48))
            self.admin_users_list.addItem(item)
            self.admin_users_list.setItemWidget(item, row)

    def _make_admin_user_row(self, username: str) -> QWidget:
        row = QWidget()
        row.setMinimumHeight(44)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(8)

        profile = self.user_profiles.get(username.lower(), {})
        avatar_path = profile.get("profile_picture", "")

        avatar = QLabel()
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignCenter)

        if avatar_path and os.path.exists(avatar_path):
            avatar.setPixmap(self._make_round_pixmap(avatar_path, 34))
        else:
            avatar.setText(username[:1].upper())

        name = QLabel(f"{username} (You)" if username == self.username else username)
        name.setObjectName("adminUserName")

        layout.addWidget(avatar)
        layout.addWidget(name, 1)

        if username == self.username:
            tag = QLabel("You")
            tag.setObjectName("adminSelfTag")
            tag.setAlignment(Qt.AlignCenter)
            tag.setFixedSize(125, 34)
            layout.addWidget(tag)
        else:
            kick = QPushButton("Kick")
            kick.setObjectName("adminKickButton")
            kick.setFixedSize(58, 30)
            kick.clicked.connect(lambda: self._kick_user(username))

            ban = QPushButton("Ban")
            ban.setObjectName("adminBanButton")
            ban.setFixedSize(58, 30)
            ban.clicked.connect(lambda: self._ban_user(username))

            layout.addWidget(kick)
            layout.addWidget(ban)

        return row

    def _on_admin_data_received(self, packet: dict) -> None:
        banned = packet.get("banned_users", [])
        self.banned_users = banned if isinstance(banned, list) else []

        self.banned_users_list.clear()

        seen_usernames = set()

        if not self.banned_users:
            self.banned_users_list.addItem("No banned users")
        else:
            for user in self.banned_users:
                if isinstance(user, dict):
                    username = user.get("username", "Unknown")
                    banned_at = user.get("banned_at", "")

                    username_key = username.lower().strip()
                    if username_key in seen_usernames:
                        continue

                    seen_usernames.add(username_key)

                    text = username
                    if banned_at:
                        text += f"  •  {banned_at}"
                else:
                    username = str(user)
                    username_key = username.lower().strip()

                    if username_key in seen_usernames:
                        continue

                    seen_usernames.add(username_key)
                    text = username

                self.banned_users_list.addItem(text)

        stats = packet.get("stats", {})
        self.message_count_label.setText(f"Messages Today: {stats.get('messages_today', 0)}")
        self._update_stats()

    def _update_stats(self) -> None:
        self.online_count_label.setText(f"Online Users: {len(self.online_users)}")
        self.room_count_label.setText(f"Active Rooms: {len(self.available_rooms)}")

    def _kick_user(self, username: str) -> None:
        if username == self.username:
            self._show_error("You cannot kick yourself.")
            return
        self.network_client.kick_user(username)

    def _ban_user(self, username: str) -> None:
        if username == self.username:
            self._show_error("You cannot ban yourself.")
            return
        self.network_client.ban_user(username)

        if hasattr(self.network_client, "request_admin_data"):
            QTimer.singleShot(300, self.network_client.request_admin_data)

    def send_message(self) -> None:
        message = self.message_input.text().strip()
        if not message:
            return

        reply_payload = self.reply_context if self.reply_context else None

        try:
            if self.target_mode == "public":
                self.network_client.send_public_message(message, reply_to=reply_payload)
            elif self.target_mode == "private" and self.target_name:
                self.network_client.send_private_message(self.target_name, message, reply_to=reply_payload)
            elif self.target_mode == "room" and self.target_name:
                self.network_client.send_room_message(self.target_name, message, reply_to=reply_payload)
            else:
                self._show_error("Please select a valid chat target first.")
                return

            self.message_input.clear()
            self._clear_reply()
            self._send_stop_typing()

        except Exception as error:
            self._show_error(f"Message send failed: {error}")

    def _add_message(self, sender: str, message: str, own: bool, status_text: str = "", reply_to=None, message_id=None) -> None:
        if not message_id:
            message_id = uuid.uuid4().hex

        message_data = {
            "message_id": message_id,
            "sender": sender,
            "message": message,
            "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0"),
            "status": status_text,
            "reply_to": reply_to if isinstance(reply_to, dict) else None,
        }

        bubble = MessageBubble(message_data, own=own)
        bubble.reply_requested.connect(self._show_reply_bar)

        if hasattr(bubble, "local_delete_requested"):
            bubble.local_delete_requested.connect(self._delete_message_for_everyone)

        self.message_widgets[message_id] = bubble
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _on_public_message(self, packet: dict) -> None:
        sender = packet.get("sender", "Unknown")
        message = packet.get("message", "")
        own = sender == self.username

        self._add_message(
            sender="Admin" if own else sender,
            message=message,
            own=own,
            status_text=packet.get("status", ""),
            reply_to=packet.get("reply_to"),
            message_id=packet.get("message_id"),
        )

        if hasattr(self.network_client, "request_admin_data"):
            self.network_client.request_admin_data()

    def _on_private_message(self, packet: dict) -> None:
        sender = packet.get("sender", "Unknown")
        message = packet.get("message", "")
        own = sender == self.username

        self._add_message(
            sender="Admin" if own else sender,
            message=message,
            own=own,
            status_text=packet.get("status", ""),
            reply_to=packet.get("reply_to"),
            message_id=packet.get("message_id"),
        )

        if hasattr(self.network_client, "request_admin_data"):
            self.network_client.request_admin_data()


    def _on_room_message(self, packet: dict) -> None:
        sender = packet.get("sender", "Unknown")
        room = packet.get("room", "Room")
        message = packet.get("message", "")
        own = sender == self.username

        self._add_message(
            sender=f"Admin @ {room}" if own else f"{sender} · {room}",
            message=message,
            own=own,
            status_text=packet.get("status", ""),
            reply_to=packet.get("reply_to"),
            message_id=packet.get("message_id"),
        )

        if hasattr(self.network_client, "request_admin_data"):
            self.network_client.request_admin_data()


    def _on_notice(self, message: str) -> None:
        notice = QLabel(message)
        notice.setObjectName("systemNotice")
        notice.setAlignment(Qt.AlignCenter)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, notice)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _on_room_joined(self, message: str) -> None:
        self._on_notice(message)

    def _show_reply_bar(self, reply_payload: dict) -> None:
        self.reply_context = reply_payload
        text = reply_payload.get("message", "")
        if len(text) > 80:
            text = text[:77] + "..."
        self.reply_label.setText(f"Replying to {reply_payload.get('sender', 'User')}: {text}")
        self.reply_bar.show()

    def _clear_reply(self) -> None:
        self.reply_context = None
        self.reply_bar.hide()

    def _delete_message_for_everyone(self, message_id: str) -> None:
        widget = self.message_widgets.pop(message_id, None)
        if widget:
            widget.setParent(None)
            widget.deleteLater()

        if hasattr(self.network_client, "delete_message"):
            self.network_client.delete_message(message_id)

    def _on_message_deleted(self, packet: dict) -> None:
        message_id = packet.get("message_id")
        widget = self.message_widgets.pop(message_id, None)
        if widget:
            widget.setParent(None)
            widget.deleteLater()

    def _on_input_changed(self, text: str) -> None:
        if text.strip():
            self._send_typing_signal(True)
            self.typing_timer.start(1200)
        else:
            self._send_stop_typing()

    def _send_typing_signal(self, is_typing: bool) -> None:
        if hasattr(self.network_client, "send_typing"):
            self.network_client.send_typing(
                target_mode=self.target_mode,
                target=self.target_name,
                room=self.target_name if self.target_mode == "room" else None,
                is_typing=is_typing,
            )

    def _send_stop_typing(self) -> None:
        self._send_typing_signal(False)

    def _on_typing_received(self, packet: dict) -> None:
        sender = packet.get("sender", "")
        if not sender or sender == self.username:
            return

        if packet.get("is_typing", False):
            self.typing_label.setText(f"{sender} is typing...")
        else:
            self.typing_label.setText("")

    def _toggle_emoji_picker(self) -> None:
        if self.emoji_picker.isVisible():
            self.emoji_picker.hide()
            return

        global_pos = self.emoji_button.mapToGlobal(
            QPoint(0, -self.emoji_picker.sizeHint().height())
        )
        self.emoji_picker.move(global_pos)
        self.emoji_picker.show()

    def _insert_emoji(self, emoji: str) -> None:
        self.message_input.insert(emoji)
        self.emoji_picker.hide()
        self.message_input.setFocus()

    def _open_room_dialog(self) -> None:
        dialog = RoomDialog(self)
        if dialog.exec():
            room_name = dialog.room_input.text().strip()
            if room_name:
                self.network_client.join_room(room_name)

    def _open_profile_dialog(self) -> None:
        dialog = ProfileDialog(self.username, self)

        if dialog.exec():
            display_name = dialog.name_input.text().strip()
            avatar_path = dialog.avatar_input.text().strip()

            if display_name:
                self.username = display_name
                self.admin_name_label.setText(display_name)
                self.admin_avatar.setText(display_name[:1].upper())

            if avatar_path:
                self._apply_profile_image(avatar_path)

                if hasattr(self.network_client, "update_profile_picture"):
                    self.network_client.update_profile_picture(avatar_path)


    def _apply_profile_image(self, avatar_path: str) -> None:
        if not os.path.exists(avatar_path):
            self._show_error("Profile image path does not exist.")
            return

        size = 52
        original = QPixmap(avatar_path)

        if original.isNull():
            self._show_error("Could not load profile image.")
            return

        scaled = original.scaled(
            size,
            size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        x = (scaled.width() - size) // 2
        y = (scaled.height() - size) // 2
        cropped = scaled.copy(x, y, size, size)

        rounded = QPixmap(size, size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addEllipse(0, 0, size, size)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()

        self.admin_avatar.setText("")
        self.admin_avatar.setPixmap(rounded)


    def _make_round_pixmap(self, image_path: str, size: int) -> QPixmap:
        original = QPixmap(image_path)

        if original.isNull():
            return QPixmap()

        scaled = original.scaled(
            size,
            size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        x = (scaled.width() - size) // 2
        y = (scaled.height() - size) // 2
        cropped = scaled.copy(x, y, size, size)

        rounded = QPixmap(size, size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addEllipse(0, 0, size, size)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()

        return rounded

    def _open_profile_dialog(self) -> None:
        dialog = ProfileDialog(self.username, self)

        if dialog.exec():
            display_name = dialog.name_input.text().strip()
            avatar_path = dialog.avatar_input.text().strip()

            if display_name:
                self.username = display_name
                self.admin_name_label.setText(display_name)
                self.admin_avatar.setText(display_name[:1].upper())

            if avatar_path:
                self._apply_profile_image(avatar_path)

                if hasattr(self.network_client, "update_profile_picture"):
                    self.network_client.update_profile_picture(avatar_path)


    def _apply_profile_image(self, avatar_path: str) -> None:
        if not os.path.exists(avatar_path):
            self._show_error("Profile image path does not exist.")
            return

        size = 52
        original = QPixmap(avatar_path)

        if original.isNull():
            self._show_error("Could not load profile image.")
            return

        scaled = original.scaled(
            size,
            size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        x = (scaled.width() - size) // 2
        y = (scaled.height() - size) // 2
        cropped = scaled.copy(x, y, size, size)

        rounded = QPixmap(size, size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addEllipse(0, 0, size, size)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()

        self.admin_avatar.setText("")
        self.admin_avatar.setPixmap(rounded)

    def _scroll_to_bottom(self) -> None:
        bar = self.messages_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _show_error(self, message: str) -> None:
        self._show_custom_dialog("Talkify Admin", message, QMessageBox.Warning)

    def _show_info(self, message: str) -> None:
        self._show_custom_dialog("Talkify Admin", message, QMessageBox.Information)

    def _show_custom_dialog(self, title: str, message: str, icon) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.setIcon(icon)
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: #1E2A3A;
                color: #EAF1FF;
            }
            QMessageBox QLabel {
                color: #EAF1FF;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }
            QMessageBox QPushButton {
                background: #86A8CF;
                color: white;
                border-radius: 8px;
                padding: 7px 18px;
                font-weight: 700;
            }
        """)
        dialog.exec()

    def _on_disconnected(self) -> None:
        self._show_info("Disconnected from server.")

    def closeEvent(self, event) -> None:
        self.network_client.disconnect()
        super().closeEvent(event)