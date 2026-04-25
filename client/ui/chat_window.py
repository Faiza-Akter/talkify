from __future__ import annotations

# =========================================================
# 01. IMPORTS
# =========================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import os
import uuid

from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QImage
from PySide6.QtCore import QRect
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
from client.ui.widgets.profile_dialog import ProfileDialog
from client.ui.widgets.room_dialog import RoomDialog
from client.ui.widgets.sidebar_item import SidebarItem


# =========================================================
# 02. CONVERSATION DATA MODEL
# Used for sidebar items: chats, rooms, and users.
# =========================================================

@dataclass
class ConversationMeta:
    key: str
    mode: str
    name: str
    subtitle: str
    trailing: str = ''
    online: bool = False
    accent: bool = False


# =========================================================
# 03. MAIN CHAT WINDOW CLASS
# =========================================================

class ChatWindow(QWidget):
    def __init__(
        self,
        network_client,
        username: str,
        initial_room: str = 'General',
        is_admin: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName('appRoot')

        # -------------------------------
        # User/session state
        # -------------------------------
        self.network_client = network_client
        self.username = username
        self.initial_room = initial_room
        self.is_admin = is_admin
        self.controller = ChatController(network_client)

        # -------------------------------
        # Current chat target state
        # target_mode can be: public, private, room
        # -------------------------------
        self.target_mode = 'public'
        self.target_name: Optional[str] = None

        # -------------------------------
        # UI state
        # -------------------------------
        self.reply_context: Optional[dict] = None
        self.current_filter = 'chats'
        self.local_display_name = username
        self.sidebar_visible = True

        # -------------------------------
        # Data collections
        # -------------------------------
        self.conversations: Dict[str, ConversationMeta] = {}
        self.online_users: list[str] = []
        self.user_profiles: Dict[str, dict] = {}
        self.available_rooms: list[str] = []
        self.message_widgets: Dict[str, QWidget] = {}

        # -------------------------------
        # Future-feature support
        # Typing signal timer
        # -------------------------------
        self.typing_timer = QTimer(self)
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self._send_stop_typing)

        self.sent_message_targets: Dict[str, dict] = {}

        # -------------------------------
        # Window setup
        # -------------------------------
        self.setWindowTitle(f'Talkify - {username}')
        self._resize_to_screen()

        # -------------------------------
        # Build and initialize UI
        # -------------------------------
        self._build_ui()
        self._connect_signals()
        self._seed_default_conversations()

        # Sync any packets that arrived before ChatWindow connected its signals.
        if hasattr(self.network_client, "latest_users") and self.network_client.latest_users:
            self._update_user_list(self.network_client.latest_users)

        if hasattr(self.network_client, "latest_rooms") and self.network_client.latest_rooms:
            self._update_room_list(self.network_client.latest_rooms)

        self._rebuild_sidebar()
        self._apply_target('public', None)

    # =====================================================
    # 04. WINDOW SIZE
    # =====================================================

    def _resize_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        width = min(1440, int(screen.width() * 0.96))
        height = min(860, int(screen.height() * 0.92))

        self.resize(width, height)
        self.setMinimumSize(1120, 700)

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
                if image.pixelColor(x, y).alpha() > 10:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x == -1 or max_y == -1:
            return pixmap

        rect = QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        return pixmap.copy(rect)

    # =====================================================
    # 05. MAIN UI BUILDER
    # This method only arranges the major page sections:
    # Sidebar + Main Panel
    # =====================================================

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        self._build_sidebar()
        self._build_main_panel()

        self.sidebar_restore_button = QToolButton()
        self.sidebar_restore_button.setText("☰")
        self.sidebar_restore_button.setObjectName("sidebarToggleButton")
        self.sidebar_restore_button.setFixedSize(38, 34)
        self.sidebar_restore_button.setToolTip("Show sidebar")
        self.sidebar_restore_button.clicked.connect(self._toggle_sidebar)
        self.sidebar_restore_button.hide()

        root.addWidget(self.sidebar_restore_button, alignment=Qt.AlignTop)
        root.addWidget(self.sidebar)
        root.addWidget(self.main_panel, 1)

    # =====================================================
    # 06. SIDEBAR SECTION
    # Left panel containing logo, search, tabs, list,
    # quick buttons, and current user card.
    # =====================================================

    def _build_sidebar(self) -> None:
        self.sidebar = QFrame()
        self.sidebar.setObjectName('sidebarPanel')
        self.sidebar.setFixedWidth(320)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 12, 18, 18)
        sidebar_layout.setSpacing(0)

        sidebar_top_row = QHBoxLayout()
        sidebar_top_row.setContentsMargins(0, 0, 0, 0)
        sidebar_top_row.setSpacing(8)

        brand_row = self._build_sidebar_brand()

        self.sidebar_toggle_button = QToolButton()
        self.sidebar_toggle_button.setText("☰")
        self.sidebar_toggle_button.setObjectName("sidebarToggleButton")
        self.sidebar_toggle_button.setFixedSize(38, 34)
        self.sidebar_toggle_button.setToolTip("Hide sidebar")
        self.sidebar_toggle_button.clicked.connect(self._toggle_sidebar)

        sidebar_top_row.addLayout(brand_row)
        sidebar_top_row.addStretch()
        sidebar_top_row.addWidget(self.sidebar_toggle_button, alignment=Qt.AlignTop)

        self.search_input = self._build_sidebar_search()
        tab_row = self._build_sidebar_tabs()

        self.section_label = QLabel('Recent Chats')
        self.section_label.setObjectName('sidebarSectionTitle')

        self.sidebar_list = QListWidget()
        self.sidebar_list.setObjectName('sidebarList')
        self.sidebar_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sidebar_list.setWordWrap(False)
        self.sidebar_list.itemClicked.connect(self._on_sidebar_item_clicked)


        quick_row = self._build_sidebar_quick_buttons()
        self.user_card = self._build_sidebar_user_card()

        sidebar_layout.addLayout(sidebar_top_row)

        # Space between logo/toggle row and search bar
        sidebar_layout.addSpacing(14)

        sidebar_layout.addWidget(self.search_input)

        # Space between search bar and Chats/Rooms/Users tabs
        sidebar_layout.addSpacing(14)

        sidebar_layout.addLayout(tab_row)

        # Space between tabs and Recent Chats label
        sidebar_layout.addSpacing(12)

        sidebar_layout.addWidget(self.section_label)

        # Space between Recent Chats label and chat list
        sidebar_layout.addSpacing(8)

        sidebar_layout.addWidget(self.sidebar_list, 1)

        # Space between chat list and Public/Join Room buttons
        sidebar_layout.addSpacing(14)

        sidebar_layout.addLayout(quick_row)

        # Space between quick buttons and bottom user card
        sidebar_layout.addSpacing(14)

        sidebar_layout.addWidget(self.user_card)
        

    # =====================================================
    # 06.1 SIDEBAR BRAND AREA
    # Talkify logo + app name + subtitle.
    # =====================================================

    def _build_sidebar_brand(self) -> QHBoxLayout:
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(0)

        logo = QLabel()
        logo.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        logo.setFixedSize(90, 70)

        logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = self._trim_transparent_padding(pixmap)
            pixmap = pixmap.scaled(
                55,
                55,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            logo.setPixmap(pixmap)

        brand_row.addWidget(logo, alignment=Qt.AlignLeft | Qt.AlignTop)

        return brand_row

    # =====================================================
    # 06.2 SIDEBAR SEARCH
    # Search chats, rooms, and users.
    # =====================================================

    def _build_sidebar_search(self) -> QLineEdit:
        search_input = QLineEdit()
        search_input.setObjectName('sidebarSearch')
        search_input.setPlaceholderText('Search chats, rooms or users')
        search_input.setFixedHeight(42)
        search_input.textChanged.connect(self._rebuild_sidebar)

        return search_input

    # =====================================================
    # 06.3 SIDEBAR TABS
    # Chats / Rooms / Users filter buttons.
    # =====================================================

    def _build_sidebar_tabs(self) -> QHBoxLayout:
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)

        self.chats_tab = self._make_tab_button('Chats', 'chats')
        self.rooms_tab = self._make_tab_button('Rooms', 'rooms')
        self.users_tab = self._make_tab_button('Users', 'users')

        tab_row.addWidget(self.chats_tab)
        tab_row.addWidget(self.rooms_tab)
        tab_row.addWidget(self.users_tab)

        return tab_row

    # =====================================================
    # 06.4 SIDEBAR QUICK BUTTONS
    # Public chat and room joining buttons.
    # =====================================================

    def _build_sidebar_quick_buttons(self) -> QHBoxLayout:
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)

        self.public_button = QPushButton('Public')
        self.public_button.clicked.connect(lambda: self._apply_target('public', None))

        self.join_room_button = QPushButton('Join Room')
        self.join_room_button.clicked.connect(self._open_room_dialog)

        quick_row.addWidget(self.public_button)
        quick_row.addWidget(self.join_room_button)

        return quick_row

    # =====================================================
    # 06.5 SIDEBAR USER CARD
    # Bottom card showing logged-in user and Edit button.
    # =====================================================

    def _build_sidebar_user_card(self) -> QFrame:
        user_card = QFrame()
        user_card.setObjectName('sidebarUserCard')

        user_card_layout = QHBoxLayout(user_card)
        user_card_layout.setContentsMargins(12, 12, 12, 12)
        user_card_layout.setSpacing(10)

        self.user_avatar = QLabel(self.local_display_name[:1].upper())


        self.user_avatar.setObjectName('bottomAvatar')

        self.user_avatar.setAlignment(Qt.AlignCenter)
        self.user_avatar.setFixedSize(42,42)

        user_texts = QVBoxLayout()
        user_texts.setSpacing(0)

        self.user_name_label = QLabel(self.local_display_name)
        self.user_name_label.setObjectName('bottomUserName')

        self.user_status_label = QLabel('you are online')
        self.user_status_label.setObjectName('bottomUserStatus')

        user_texts.addWidget(self.user_name_label)
        user_texts.addWidget(self.user_status_label)

        self.profile_button = QToolButton()
        self.profile_button.setText('Edit')
        self.profile_button.setObjectName('ghostToolButton')
        self.profile_button.clicked.connect(self._open_profile_dialog)

        user_card_layout.addWidget(self.user_avatar)
        user_card_layout.addLayout(user_texts)
        user_card_layout.addStretch()
        user_card_layout.addWidget(self.profile_button)

        return user_card
    # =====================================================
    # 07. MAIN PANEL
    # Right side containing header, reply bar,
    # messages area, and composer/footer.
    # =====================================================

    def _build_main_panel(self) -> None:
        self.main_panel = QFrame()
        self.main_panel.setObjectName('mainPanel')

        main_layout = QVBoxLayout(self.main_panel)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        header = self._build_chat_header()
        self.reply_bar = self._build_reply_bar()
        self.messages_scroll = self._build_messages_area()
        composer = self._build_composer()

        main_layout.addWidget(header)
        main_layout.addWidget(self.reply_bar)
        main_layout.addWidget(self.messages_scroll, 1)
        main_layout.addWidget(composer)

    # =====================================================
    # 08. CHAT HEADER
    # Top header showing:
    # - PUBLIC LOBBY / ROOM CHAT / DIRECT MESSAGE
    # - Chat title
    # - Chat subtitle
    # - Live badge
    # - Kick and Ban admin buttons
    # =====================================================

    def _build_chat_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName('chatHeader')

        header_layout = QHBoxLayout(header)

        # Compact header height
        header_layout.setContentsMargins(18, 8, 18, 8)
        header_layout.setSpacing(8)

        header_left = QVBoxLayout()
        header_left.setSpacing(1)

        self.target_badge = QLabel('PUBLIC LOBBY')
        self.target_badge.setObjectName('targetBadge')

        self.chat_title = QLabel('Public Chat')
        self.chat_title.setObjectName('chatTitle')

        self.chat_subtitle = QLabel('Everyone can see messages here')
        self.chat_subtitle.setObjectName('chatSubtitle')

        header_left.addWidget(self.target_badge)
        header_left.addWidget(self.chat_title)
        header_left.addWidget(self.chat_subtitle)

        self.header_status = QLabel('● Live')
        self.header_status.setObjectName('statusBadge')
        self.header_status.setAlignment(Qt.AlignCenter)

        # Same size as Kick and Ban buttons
        self.header_status.setFixedSize(76, 34)

        self.kick_button = QPushButton('Kick')
        self.kick_button.setObjectName('dangerButton')
        self.kick_button.setFixedSize(76, 34)
        self.kick_button.clicked.connect(self._kick_selected_target)
        self.kick_button.hide()

        self.ban_button = QPushButton('Ban')
        self.ban_button.setObjectName('dangerButton')
        self.ban_button.setFixedSize(76, 34)
        self.ban_button.clicked.connect(self._ban_selected_target)
        self.ban_button.hide()

        header_layout.addLayout(header_left)
        header_layout.addStretch()
        header_layout.addWidget(self.header_status)
        header_layout.addWidget(self.kick_button)
        header_layout.addWidget(self.ban_button)

        return header

    # =====================================================
    # 09. REPLY BAR
    # Appears above composer when user replies to a message.
    # =====================================================

    def _build_reply_bar(self) -> QFrame:
        reply_bar = QFrame()
        reply_bar.setObjectName('replyBar')

        reply_layout = QHBoxLayout(reply_bar)
        reply_layout.setContentsMargins(14, 10, 14, 10)
        reply_layout.setSpacing(10)

        self.reply_label = QLabel('')
        self.reply_label.setObjectName('replyBarText')

        self.cancel_reply_button = QPushButton('Cancel')
        self.cancel_reply_button.setObjectName('ghostToolButton')
        self.cancel_reply_button.clicked.connect(self._clear_reply)

        reply_layout.addWidget(self.reply_label)
        reply_layout.addStretch()
        reply_layout.addWidget(self.cancel_reply_button)

        reply_bar.hide()

        return reply_bar

    # =====================================================
    # 10. MESSAGES AREA
    # Scrollable area where message bubbles appear.
    # =====================================================

    def _build_messages_area(self) -> QScrollArea:
        messages_scroll = QScrollArea()
        messages_scroll.setObjectName('messagesScroll')
        messages_scroll.setWidgetResizable(True)

        self.messages_surface = QWidget()
        self.messages_surface.setObjectName('messagesSurface')

        self.messages_layout = QVBoxLayout(self.messages_surface)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(0)

        self.messages_layout.addStretch()

        messages_scroll.setWidget(self.messages_surface)

        return messages_scroll

    # =====================================================
    # 11. COMPOSER / FOOTER
    # Bottom panel with:
    # - Sending target label
    # - Theme/info label
    # - Typing status
    # - Message input
    # - Emoji button
    # - Send button
    # =====================================================

    def _build_composer(self) -> QFrame:
        composer = QFrame()
        composer.setObjectName('composerPanel')

        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(14, 8, 14, 8)
        composer_layout.setSpacing(4)

        context_row = QHBoxLayout()

        self.context_label = QLabel('Sending to: Public Chat')
        self.context_label.setObjectName('contextLabel')

        context_row.addWidget(self.context_label)
        context_row.addStretch()

        self.typing_label = QLabel('')
        self.typing_label.setObjectName('typingLabel')

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.message_input = QLineEdit()
        self.message_input.setObjectName('messageInput')
        self.message_input.setPlaceholderText('Type your message here...')
        self.message_input.textChanged.connect(self._on_input_changed)
        self.message_input.returnPressed.connect(self.send_message)

        self.emoji_picker = EmojiPicker()
        self.emoji_picker.emoji_selected.connect(self._insert_emoji)

        self.emoji_button = QToolButton()
        self.emoji_button.setText('😀')
        self.emoji_button.setObjectName('roundToolButton')
        self.emoji_button.setFixedSize(52, 52)
        self.emoji_button.clicked.connect(self._toggle_emoji_picker)

        self.send_button = QPushButton('Send')
        self.send_button.setObjectName('primaryButton')
        self.send_button.setFixedSize(112, 42)
        self.send_button.clicked.connect(self.send_message)

        input_row.addWidget(self.message_input, 1)
        input_row.addWidget(self.emoji_button)
        input_row.addWidget(self.send_button)

        composer_layout.addLayout(context_row)
        composer_layout.addLayout(input_row)

        return composer

    # =====================================================
    # 12. SIDEBAR TAB BUTTON CREATION
    # Creates Chats / Rooms / Users buttons.
    # =====================================================

    def _make_tab_button(self, text: str, filter_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setObjectName('filterButton')
        button.clicked.connect(lambda: self._set_filter(filter_name))

        if filter_name == self.current_filter:
            button.setChecked(True)

        return button

    # =====================================================
    # 13. SIDEBAR FILTER LOGIC
    # Changes sidebar list between chats, rooms, users.
    # =====================================================

    def _set_filter(self, filter_name: str) -> None:
        self.current_filter = filter_name

        for button, name in [
            (self.chats_tab, 'chats'),
            (self.rooms_tab, 'rooms'),
            (self.users_tab, 'users'),
        ]:
            button.setChecked(name == filter_name)

        self.section_label.setText(
            'Recent Chats'
            if filter_name == 'chats'
            else 'Available Rooms'
            if filter_name == 'rooms'
            else 'Online Users'
        )

        self._rebuild_sidebar()

    # =====================================================
    # 14. DEFAULT SIDEBAR CONVERSATIONS
    # Adds Public Chat and default General room.
    # =====================================================

    def _seed_default_conversations(self) -> None:
        self.conversations = {
            'public': ConversationMeta(
                key='public',
                mode='public',
                name='Public Chat',
                subtitle='Chat with everyone',
                trailing='Now',
                accent=True,
                online=True,
            ),
            f'room:{self.initial_room.lower()}': ConversationMeta(
                key=f'room:{self.initial_room.lower()}',
                mode='room',
                name=self.initial_room,
                subtitle='Default room',
                trailing='Room',
            ),
        }

        self.available_rooms = [self.initial_room]

    # =====================================================
    # 15. REBUILD SIDEBAR LIST
    # Updates chat/room/user list based on selected filter.
    # =====================================================

    def _rebuild_sidebar(self) -> None:
        query = self.search_input.text().strip().lower()
        self.sidebar_list.clear()

        if self.current_filter == 'chats':
            items = list(self.conversations.values())

        elif self.current_filter == 'rooms':
            items = [
                ConversationMeta(
                    key=f"user:{user.lower()}",
                    mode="private",
                    name=user,
                    subtitle="Direct message",
                    trailing="Online",
                    online=True,
                )
                for user in self.online_users
            ]

        else:
            items = [
                ConversationMeta(
                    key=f'user:{user.lower()}',
                    mode='private',
                    name=user,
                    subtitle='Direct message',
                    trailing='Online',
                    online=True,
                )
                for user in self.online_users
            ]

        for meta in items:
            haystack = f'{meta.name} {meta.subtitle}'.lower()

            if query and query not in haystack:
                continue

            item = QListWidgetItem()
            item.setData(Qt.UserRole, meta)

            profile = self.user_profiles.get(meta.name.lower(), {})
            avatar_path = profile.get("profile_picture", "")

            widget = SidebarItem(
                title=meta.name,
                subtitle=meta.subtitle,
                trailing="",
                avatar_text=meta.name[:1],
                accent=meta.accent,
                online=False,
                avatar_path=avatar_path,
            )

            item.setSizeHint(widget.sizeHint())
            item.setSizeHint(widget.minimumSizeHint())
            self.sidebar_list.addItem(item)
            self.sidebar_list.setItemWidget(item, widget)

    # =====================================================
    # 16. CONNECT NETWORK SIGNALS
    # Connects client/network events to UI handlers.
    # =====================================================

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
        self.network_client.message_deleted.connect(self._on_message_deleted)

        # Future-feature signals
        if hasattr(self.network_client, 'typing_received'):
            self.network_client.typing_received.connect(self._on_typing_received)

        if hasattr(self.network_client, 'message_status_received'):
            self.network_client.message_status_received.connect(self._on_message_status_received)

        if hasattr(self.network_client, 'profile_updated'):
            self.network_client.profile_updated.connect(self._on_profile_updated)

    def _on_message_deleted(self, packet: dict):
        message_id = packet.get("message_id")

        widget = self.message_widgets.pop(message_id, None)

        if widget:
            widget.setParent(None)
            widget.deleteLater()

    # =====================================================
    # 17. TARGET SELECTION
    # Triggered when a sidebar item is clicked.
    # =====================================================

    def _on_sidebar_item_clicked(self, item: QListWidgetItem) -> None:
        meta: ConversationMeta = item.data(Qt.UserRole)
        self._apply_target(meta.mode, None if meta.mode == 'public' else meta.name)

    def _apply_target(self, mode: str, target_name: Optional[str]) -> None:
        self.target_mode = mode
        self.target_name = target_name

        if mode == 'public':
            self.target_badge.setText('PUBLIC LOBBY')
            self.chat_title.setText('Public Chat')
            self.chat_subtitle.setText('Everyone can see messages here')
            self.context_label.setText('Sending to: Public Chat')

        elif mode == 'room':
            room = target_name or self.initial_room
            self.target_badge.setText('ROOM CHAT')
            self.chat_title.setText(room)
            self.chat_subtitle.setText('Room-based conversation')
            self.context_label.setText(f'Sending to: Room ({room})')

        else:
            person = target_name or 'Direct Message'
            self.target_badge.setText('DIRECT MESSAGE')
            self.chat_title.setText(person)
            self.chat_subtitle.setText(f'Private conversation with {person}')
            self.context_label.setText(f'Sending to: Direct Message ({person})')

        self._update_admin_visibility()

    def _toggle_sidebar(self) -> None:
        self.sidebar_visible = not self.sidebar_visible
        self.sidebar.setVisible(self.sidebar_visible)

        if self.sidebar_visible:
            self.sidebar_toggle_button.show()
            self.sidebar_restore_button.hide()
            self.sidebar_toggle_button.setToolTip("Hide sidebar")
        else:
            self.sidebar_toggle_button.hide()
            self.sidebar_restore_button.show()
            self.sidebar_restore_button.setToolTip("Show sidebar")

    # =====================================================
    # 18. ADMIN VISIBILITY
    # Shows Kick/Ban buttons only for admin users.
    # =====================================================

    def _update_admin_visibility(self) -> None:
        should_show = self.is_admin
        self.kick_button.setVisible(should_show)
        self.ban_button.setVisible(should_show)

    # =====================================================
    # 19. TYPING INDICATOR
    # Updates local typing text and sends typing status.
    # =====================================================

    def _on_input_changed(self, text: str) -> None:
        if text.strip():
            if self.target_mode == 'private' and self.target_name:
                self.typing_label.setText(f'You are drafting a DM to {self.target_name}...')

            elif self.target_mode == 'room' and self.target_name:
                self.typing_label.setText(f'Drafting message for room {self.target_name}...')

            else:
                self.typing_label.setText('Drafting public message...')

            self._send_typing_signal(is_typing=True)
            self.typing_timer.start(1200)

        else:
            self.typing_label.setText('')
            self._send_stop_typing()

    def _send_typing_signal(self, is_typing: bool) -> None:
        if not hasattr(self.network_client, 'send_typing'):
            return

        try:
            self.network_client.send_typing(
                target_mode=self.target_mode,
                target=self.target_name,
                room=self.target_name if self.target_mode == 'room' else None,
                is_typing=is_typing,
            )

        except Exception:
            pass

    def _send_stop_typing(self) -> None:
        self._send_typing_signal(is_typing=False)

    def _on_typing_received(self, packet: dict) -> None:
        sender = packet.get('sender', '')

        if not sender or sender == self.username:
            return

        is_typing = packet.get('is_typing', False)
        target_mode = packet.get('target_mode', 'public')

        should_show = False

        if target_mode == 'public' and self.target_mode == 'public':
            should_show = True

        elif (
            target_mode == 'private'
            and self.target_mode == 'private'
            and self.target_name == sender
        ):
            should_show = True

        elif (
            target_mode == 'room'
            and self.target_mode == 'room'
            and packet.get('room') == self.target_name
        ):
            should_show = True

        if should_show and is_typing:
            self.typing_label.setText(f'{sender} is typing...')

        elif should_show:
            self.typing_label.setText('')

    # =====================================================
    # 20. EMOJI PICKER
    # Opens emoji picker and inserts selected emoji.
    # =====================================================

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

    # =====================================================
    # 21. PROFILE AND ROOM DIALOGS
    # Opens profile edit and join room dialogs.
    # =====================================================

    def _open_profile_dialog(self) -> None:
        dialog = ProfileDialog(self.local_display_name, self)

        if dialog.exec():
            display_name = dialog.name_input.text().strip()
            avatar_path = dialog.avatar_input.text().strip()

            if display_name:
                self.local_display_name = display_name
                self.user_name_label.setText(display_name)
                self.user_avatar.setText(display_name[:1].upper())

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

        self.user_avatar.setFixedSize(size, size)
        self.user_avatar.setText("")
        self.user_avatar.setPixmap(rounded)

    def _open_room_dialog(self) -> None:
        dialog = RoomDialog(self)

        if dialog.exec():
            room_name = dialog.room_input.text().strip()

            if room_name:
                self.network_client.join_room(room_name)

    # =====================================================
    # 22. REPLY FEATURE
    # Shows, clears, and stores reply context.
    # =====================================================

    def _clear_reply(self) -> None:
        self.reply_context = None
        self.reply_bar.hide()

    def _show_reply_bar(self, reply_payload: dict) -> None:
        self.reply_context = reply_payload

        preview_text = reply_payload['message']

        if len(preview_text) > 80:
            preview_text = preview_text[:77] + '...'

        self.reply_label.setText(
            f"Replying to {reply_payload['sender']}: {preview_text}"
        )
        self.reply_bar.show()

    # =====================================================
    # 23. SEND MESSAGE
    # Sends message based on current target mode.
    # =====================================================

    def send_message(self) -> None:
        message = self.message_input.text().strip()

        if not message:
            return

        reply_payload = self.reply_context if self.reply_context else None

        try:
            if self.target_mode == 'public':
                self.network_client.send_public_message(
                    message,
                    reply_to=reply_payload,
                )

            elif self.target_mode == 'private' and self.target_name:
                self.network_client.send_private_message(
                    self.target_name,
                    message,
                    reply_to=reply_payload,
                )

            elif self.target_mode == 'room' and self.target_name:
                self.network_client.send_room_message(
                    self.target_name,
                    message,
                    reply_to=reply_payload,
                )

            else:
                self._show_error('Please select a valid chat target first.')
                return

            sender_text = (
                'You'
                if self.target_mode == 'public'
                else f'You → {self.target_name}'
                if self.target_mode == 'private'
                else f'You @ {self.target_name}'
            )


            self._update_conversation_preview(message)
            self.message_input.clear()
            self.typing_label.setText('')
            self._clear_reply()
            self._send_stop_typing()

        except Exception as error:
            self._show_error(f'Message send failed: {error}')

    # =====================================================
    # 24. ADD MESSAGE TO UI
    # Creates MessageBubble widget and inserts it in chat.
    # =====================================================

    def _add_message(
        self,
        sender: str,
        message: str,
        own: bool,
        status_text: str = '',
        reply_to=None,
        message_id: Optional[str] = None,
    ) -> None:
        if not message_id:
            message_id = uuid.uuid4().hex

        if isinstance(reply_to, str):
            reply_to_data = {
                'sender': 'Reply',
                'message': reply_to,
            } if reply_to else None

        elif isinstance(reply_to, dict):
            reply_to_data = reply_to

        else:
            reply_to_data = None

        message_data = {
            'message_id': message_id,
            'sender': sender,
            'message': message,
            'timestamp': datetime.now().strftime('%I:%M %p').lstrip('0'),
            'status': status_text,
            'reply_to': reply_to_data,
        }

        bubble = MessageBubble(message_data, own=own)
        bubble.reply_requested.connect(self._show_reply_bar)

        if hasattr(bubble, 'local_delete_requested'):
            bubble.local_delete_requested.connect(self._delete_message_for_everyone)

        self.message_widgets[message_id] = bubble
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)

        QTimer.singleShot(0, self._scroll_to_bottom)

    def _delete_local_message(self, message_id: str) -> None:
        widget = self.message_widgets.pop(message_id, None)

        if widget:
            widget.setParent(None)
            widget.deleteLater()

    def _scroll_to_bottom(self) -> None:
        bar = self.messages_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
    
    def _delete_message_for_everyone(self, message_id: str):

        widget = self.message_widgets.pop(message_id, None)

        if widget:
            widget.setParent(None)
            widget.deleteLater()

        # send request to server
        if hasattr(self.network_client, "delete_message"):
            self.network_client.delete_message(message_id)

    # =====================================================
    # 25. RECEIVED MESSAGE HANDLERS
    # Public, private, and room messages from server.
    # =====================================================

    def _on_public_message(self, packet: dict) -> None:
        sender = packet.get('sender', 'Unknown')
        message = packet.get('message', '')

        own = sender == self.username

        self._add_message(
            sender='You' if own else sender,
            message=message,
            own=own,
            status_text=packet.get('status', ''),
            reply_to=packet.get('reply_to'),
            message_id=packet.get('message_id'),
        )

        self._touch_private_meta(
            'public',
            'Public Chat',
            message,
            'Now',
            mode='public',
        )


    def _on_private_message(self, packet: dict) -> None:
        sender = packet.get('sender', 'Unknown')
        message = packet.get('message', '')

        own = sender == self.username

        self._add_message(
            sender='You' if own else sender,
            message=message,
            own=own,
            status_text=packet.get('status', ''),
            reply_to=packet.get('reply_to'),
            message_id=packet.get('message_id'),
        )

        self._touch_private_meta(
            f'user:{sender.lower()}',
            sender,
            message,
            'DM',
            mode='private',
        )


    def _on_room_message(self, packet: dict) -> None:
        sender = packet.get('sender', 'Unknown')
        room = packet.get('room', 'Room')
        message = packet.get('message', '')

        own = sender == self.username

        self._add_message(
            sender=f'You @ {room}' if own else f'{sender}  ·  {room}',
            message=message,
            own=own,
            status_text=packet.get('status', ''),
            reply_to=packet.get('reply_to'),
            message_id=packet.get('message_id'),
        )

        self._touch_private_meta(
            f'room:{room.lower()}',
            room,
            message,
            'Room',
            mode='room',
        )
    # =====================================================
    # 26. SYSTEM NOTICES
    # Join, leave, and room joined notices.
    # =====================================================

    def _on_notice(self, message: str) -> None:
        notice = QLabel(message)
        notice.setObjectName('systemNotice')
        notice.setAlignment(Qt.AlignCenter)

        self.messages_layout.insertWidget(self.messages_layout.count() - 1, notice)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _on_room_joined(self, message: str) -> None:
        self._on_notice(message)

    # =====================================================
    # 27. USER LIST AND ROOM LIST UPDATES
    # Updates sidebar users/rooms when server sends changes.
    # =====================================================

    def _update_user_list(self, users: list) -> None:
        normalized_users = []
        self.user_profiles = {}

        for user in users:
            if isinstance(user, dict):
                username = user.get("username", "")

                if username:
                    normalized_users.append(username)
                    self.user_profiles[username.lower()] = user

            elif isinstance(user, str):
                normalized_users.append(user)
                self.user_profiles[user.lower()] = {
                    "username": user,
                    "online": True,
                    "is_admin": False,
                    "profile_picture": "default_avatar.png",
                }

        self.online_users = normalized_users
        self.user_status_label.setText(
            f"you are online · {len(normalized_users)} users connected"
        )

        self._rebuild_sidebar()

    def _update_room_list(self, rooms: list[str]) -> None:
        self.available_rooms = rooms

        for room in rooms:
            self._touch_private_meta(
                f'room:{room.lower()}',
                room,
                'Room conversation',
                'Room',
                mode='room',
            )

        self._rebuild_sidebar()

    # =====================================================
    # 28. CONVERSATION PREVIEW / SIDEBAR META
    # Updates latest message preview in sidebar.
    # =====================================================

    def _touch_private_meta(
        self,
        key: str,
        name: str,
        subtitle: str,
        trailing: str,
        mode: str = 'private',
    ) -> None:
        self.conversations[key] = ConversationMeta(
            key=key,
            mode=mode,
            name=name,
            subtitle=subtitle,
            trailing=trailing,
            online=(mode == 'private'),
            accent=(mode == 'public'),
        )

        self._rebuild_sidebar()

    def _update_conversation_preview(self, message: str) -> None:
        if self.target_mode == 'private' and self.target_name:
            key = f'user:{self.target_name.lower()}'
            self._touch_private_meta(
                key,
                self.target_name,
                message,
                'Now',
                mode='private',
            )

        elif self.target_mode == 'room' and self.target_name:
            key = f'room:{self.target_name.lower()}'
            self._touch_private_meta(
                key,
                self.target_name,
                message,
                'Now',
                mode='room',
            )

        else:
            self.conversations['public'] = ConversationMeta(
                key='public',
                mode='public',
                name='Public Chat',
                subtitle=message,
                trailing='Now',
                online=True,
                accent=True,
            )
            self._rebuild_sidebar()

    # =====================================================
    # 29. MESSAGE STATUS UPDATE
    # Updates sent/delivered/seen symbol in message bubble.
    # =====================================================

    def _on_message_status_received(self, packet: dict) -> None:
        message_id = packet.get('message_id')
        status = packet.get('status')

        if not message_id or not status:
            return

        widget = self.message_widgets.get(message_id)

        if widget and hasattr(widget, 'update_status'):
            widget.update_status(status)

    # =====================================================
    # 30. PROFILE UPDATE HANDLER
    # Updates local display name if profile changes.
    # =====================================================

    def _on_profile_updated(self, packet: dict) -> None:
        updated_user = packet.get("username") or packet.get("sender")
        display_name = packet.get("display_name")
        profile_picture = packet.get("profile_picture", "")

        if not updated_user:
            return

        key = updated_user.lower()

        current_profile = self.user_profiles.get(key, {"username": updated_user})
        if profile_picture:
            current_profile["profile_picture"] = profile_picture
        if display_name:
            current_profile["display_name"] = display_name

        self.user_profiles[key] = current_profile

        if updated_user == self.username:
            if display_name:
                self.local_display_name = display_name
                self.user_name_label.setText(display_name)
                self.user_avatar.setText(display_name[:1].upper())

            if profile_picture:
                self._apply_profile_image(profile_picture)

        self._rebuild_sidebar()

    # =====================================================
    # 31. ADMIN ACTIONS
    # Kick and ban selected direct-message target.
    # =====================================================

    def _kick_selected_target(self) -> None:
        if self.target_mode != 'private' or not self.target_name:
            self._show_error('Select a direct message target first.')
            return

        if self.target_name == self.username:
            self._show_error('You cannot kick yourself.')
            return

        self.network_client.kick_user(self.target_name)

    def _ban_selected_target(self) -> None:
        if self.target_mode != 'private' or not self.target_name:
            self._show_error('Select a direct message target first.')
            return

        if self.target_name == self.username:
            self._show_error('You cannot ban yourself.')
            return

        self.network_client.ban_user(self.target_name)

    # =====================================================
    # 32. DIALOG HELPERS
    # Custom warning/info popup styling.
    # =====================================================

    def _show_error(self, message: str) -> None:
        self._show_custom_dialog('Talkify', message, QMessageBox.Warning)

    def _show_info(self, message: str) -> None:
        self._show_custom_dialog('Talkify', message, QMessageBox.Information)

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
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #86A8CF,
                    stop:1 #C38EB4
                );
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 18px;
                font-weight: 700;
                min-width: 72px;
            }

            QMessageBox QPushButton:hover {
                background: #86A8CF;
            }
        """)

        dialog.exec()

    # =====================================================
    # 33. DISCONNECT / CLOSE HANDLING
    # Runs when server disconnects or window closes.
    # =====================================================

    def _on_disconnected(self) -> None:
        self._show_info('Disconnected from server.')

    def closeEvent(self, event) -> None:
        self.network_client.disconnect()
        super().closeEvent(event)