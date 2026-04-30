from __future__ import annotations

# =========================================================
# 01. IMPORTS
# =========================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import os
import uuid

from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QImage, QIcon
from PySide6.QtCore import QRect
from PySide6.QtCore import QPoint, Qt, QTimer, QSize
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
    QSizePolicy,
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
    unread_count: int = 0


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
        self.room_members: Dict[str, list[str]] = {}
        self.message_widgets: Dict[str, QWidget] = {}
        self.message_history: Dict[str, list[dict]] = {}
        self.message_to_conversation: Dict[str, str] = {}
        self.last_message_group = None

        # -------------------------------
        # Future-feature support
        # Typing signal timer
        # -------------------------------
        self.typing_timer = QTimer(self)
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self._send_stop_typing)

        self.sent_message_targets: Dict[str, dict] = {}
        self.restricted_conversations: set[str] = set()

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

        restore_icon = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'icons',
            'panel-right-open.svg'
        )

        self.sidebar_restore_button = QToolButton()
        self.sidebar_restore_button.setIcon(QIcon(restore_icon))
        self.sidebar_restore_button.setIconSize(QSize(24, 24))
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
        self.sidebar.setFixedWidth(330)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 12, 14, 14)
        sidebar_layout.setSpacing(0)

        sidebar_top_row = QHBoxLayout()
        sidebar_top_row.setContentsMargins(0, 0, 0, 0)
        sidebar_top_row.setSpacing(8)

        brand_row = self._build_sidebar_brand()

        hide_icon = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'icons',
            'panel-left-open.svg'
        )

        self.sidebar_toggle_button = QToolButton()
        self.sidebar_toggle_button.setIcon(QIcon(hide_icon))
        self.sidebar_toggle_button.setIconSize(QSize(24, 24))
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
        sidebar_layout.addSpacing(6)
        sidebar_layout.addWidget(self.search_input)
        sidebar_layout.addSpacing(8)
        sidebar_layout.addLayout(tab_row)
        sidebar_layout.addSpacing(6)
        sidebar_layout.addWidget(self.section_label)
        sidebar_layout.addSpacing(4)
        sidebar_layout.addWidget(self.sidebar_list, 3)
        sidebar_layout.addSpacing(14)
        sidebar_layout.addLayout(quick_row)
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
        logo.setFixedSize(130, 64)

        logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'sidebarlogo.png')

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = self._trim_transparent_padding(pixmap)
            pixmap = pixmap.scaled(
                120,
                58,
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

        search_icon = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'icons',
            'search.svg'
        )
        search_input.addAction(QIcon(search_icon), QLineEdit.LeadingPosition)

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

        public_icon = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'icons',
            'globe.svg'
        )

        join_icon = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'icons',
            'circle-plus.svg'
        )

        self.public_button = QPushButton('  Public')
        self.public_button.setIcon(QIcon(public_icon))
        self.public_button.setIconSize(QSize(18, 18))
        self.public_button.clicked.connect(lambda: self._apply_target('public', None))

        self.join_room_button = QPushButton('  Join Room')
        self.join_room_button.setIcon(QIcon(join_icon))
        self.join_room_button.setIconSize(QSize(18, 18))
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
        self.user_status_label.setFixedWidth(210)
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

        # FIX:
        # reply_bar must exist because _clear_reply() and _show_reply_bar()
        # still reference self.reply_bar.
        self.reply_bar = self._build_reply_bar()

        self.messages_scroll = self._build_messages_area()
        composer = self._build_composer()

        main_layout.addWidget(header)
        main_layout.addWidget(self.reply_bar)
        self.reply_bar.hide()

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
        header.setFixedHeight(76)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 10)
        header_layout.setSpacing(11)

        self.header_avatar = QLabel('P')
        self.header_avatar.setObjectName('headerAvatar')
        self.header_avatar.setAlignment(Qt.AlignCenter)
        self.header_avatar.setFixedSize(44, 44)

        header_left = QVBoxLayout()
        header_left.setSpacing(1)

        self.target_badge = QLabel('')
        self.target_badge.hide()

        self.chat_title = QLabel('Public Chat')
        self.chat_title.setObjectName('chatTitle')

        self.chat_subtitle = QLabel('Everyone can see messages here')
        self.chat_subtitle.setObjectName('chatSubtitle')
        self.chat_subtitle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        header_left.addWidget(self.chat_title)
        header_left.addWidget(self.chat_subtitle)

        self.header_status = QLabel('')
        self.header_status.hide()

        self.kick_button = QPushButton('Kick')
        self.kick_button.setObjectName('dangerButton')
        self.kick_button.setFixedSize(70, 30)
        self.kick_button.clicked.connect(self._kick_selected_target)
        self.kick_button.hide()

        self.ban_button = QPushButton('Ban')
        self.ban_button.setObjectName('dangerButton')
        self.ban_button.setFixedSize(70, 30)
        self.ban_button.clicked.connect(self._ban_selected_target)
        self.ban_button.hide()

        header_layout.addWidget(self.header_avatar, alignment=Qt.AlignVCenter)
        header_layout.addLayout(header_left, 1)
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

        self.empty_state = QFrame()
        self.empty_state.setObjectName('emptyStateCard')

        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(3)
        empty_layout.setAlignment(Qt.AlignCenter)

        empty_icon = QLabel()
        empty_icon.setObjectName('emptyStateIcon')
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setFixedSize(260, 145)

        logo_path = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'logo3.png'
        )

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)

            if not pixmap.isNull():
                # Removes invisible transparent boundary around PNG
                pixmap = self._trim_transparent_padding(pixmap)

                pixmap = pixmap.scaled(
                    210,
                    125,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )

                empty_icon.setPixmap(pixmap)
            else:
                empty_icon.setText('💬')
        else:
            empty_icon.setText('💬')

        self.empty_title = QLabel('No messages yet')
        self.empty_title.setObjectName('emptyStateTitle')
        self.empty_title.setAlignment(Qt.AlignCenter)

        self.empty_subtitle = QLabel('Start the conversation with a friendly message.')
        self.empty_subtitle.setObjectName('emptyStateSubtitle')
        self.empty_subtitle.setAlignment(Qt.AlignCenter)
        self.empty_subtitle.setWordWrap(True)
        self.empty_subtitle.setFixedWidth(320)

        empty_layout.addWidget(empty_icon, alignment=Qt.AlignCenter)
        empty_layout.addSpacing(-8)
        empty_layout.addWidget(self.empty_title, alignment=Qt.AlignCenter)
        empty_layout.addWidget(self.empty_subtitle, alignment=Qt.AlignCenter)

        self.empty_state.hide()

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
        composer_layout.setContentsMargins(10, 8, 10, 8)
        composer_layout.setSpacing(6)

        # Inline reply frame — parented to composer immediately
        self.inline_reply_frame = QFrame(composer)
        self.inline_reply_frame.setObjectName('inlineReplyFrame')
        inline_layout = QHBoxLayout(self.inline_reply_frame)
        inline_layout.setContentsMargins(10, 6, 8, 6)
        inline_layout.setSpacing(8)

        accent = QFrame(self.inline_reply_frame)
        accent.setObjectName('inlineReplyAccent')
        accent.setFixedWidth(3)

        reply_texts = QVBoxLayout()
        reply_texts.setSpacing(1)

        self.inline_reply_sender = QLabel('', self.inline_reply_frame)
        self.inline_reply_sender.setObjectName('inlineReplySender')

        self.inline_reply_message = QLabel('', self.inline_reply_frame)
        self.inline_reply_message.setObjectName('inlineReplyMessage')
        self.inline_reply_message.setWordWrap(False)

        reply_texts.addWidget(self.inline_reply_sender)
        reply_texts.addWidget(self.inline_reply_message)

        self.cancel_reply_button = QToolButton(self.inline_reply_frame)
        self.cancel_reply_button.setText('×')
        self.cancel_reply_button.setObjectName('inlineReplyClose')
        self.cancel_reply_button.setFixedSize(24, 24)
        self.cancel_reply_button.clicked.connect(self._clear_reply)

        inline_layout.addWidget(accent)
        inline_layout.addLayout(reply_texts, 1)
        inline_layout.addWidget(self.cancel_reply_button)
        self.inline_reply_frame.hide()

        # Typing label — parented to composer immediately
        self.typing_label = QLabel('', composer)
        self.typing_label.setObjectName('typingLabel')
        self.typing_label.hide()
        self.typing_label.setFixedHeight(0)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        # Message input shell — parented to composer immediately
        self.message_input_shell = QFrame(composer)
        self.message_input_shell.setObjectName('messageInputShell')
        shell_layout = QHBoxLayout(self.message_input_shell)
        shell_layout.setContentsMargins(12, 0, 6, 0)
        shell_layout.setSpacing(6)
        shell_layout.setAlignment(Qt.AlignVCenter)

        self.message_input = QLineEdit(self.message_input_shell)
        self.message_input.setObjectName('messageInput')
        self.message_input.setPlaceholderText('Type your message...')
        self.message_input.textChanged.connect(self._on_input_changed)
        self.message_input.returnPressed.connect(self.send_message)

        self.emoji_picker = None

        self.emoji_button = QToolButton(self.message_input_shell)
        self.emoji_button.setText('')
        self.emoji_button.setIcon(QIcon('client/ui/assets/icons/laugh.svg'))
        self.emoji_button.setIconSize(QSize(32, 32))
        self.emoji_button.setObjectName('emojiInsideButton')
        self.emoji_button.setStyleSheet("background: transparent; border: none;")
        self.emoji_button.setFixedSize(42, 42)
        self.emoji_button.clicked.connect(self._toggle_emoji_picker)

        shell_layout.addWidget(self.message_input, 1)
        shell_layout.addWidget(self.emoji_button, 0, Qt.AlignVCenter)

        self.send_button = QPushButton('', composer)
        self.send_button.setIcon(QIcon('client/ui/assets/icons/send.svg'))
        self.send_button.setIconSize(QSize(32, 32))
        self.send_button.setObjectName('primaryButton')
        self.send_button.setFixedSize(50, 42)
        self.send_button.clicked.connect(self.send_message)

        input_row.addWidget(self.message_input_shell, 1)
        input_row.addWidget(self.send_button)

        composer_layout.addWidget(self.inline_reply_frame)
        composer_layout.addWidget(self.typing_label)
        composer_layout.addLayout(input_row)

        return composer

    # =====================================================
    # 12. SIDEBAR TAB BUTTON CREATION
    # Creates Chats / Rooms / Users buttons.
    # =====================================================

    def _make_tab_button(self, text: str, filter_name: str) -> QPushButton:
        button = QPushButton(f'  {text}')
        button.setCheckable(True)
        button.setObjectName('filterButton')

        icon_map = {
            'chats': 'message-circle.svg',
            'rooms': 'door-open.svg',
            'users': 'users.svg',
        }

        icon_file = icon_map.get(filter_name)

        if icon_file:
            icon_path = os.path.join(
                os.path.dirname(__file__),
                'assets',
                'icons',
                icon_file
            )
            button.setIcon(QIcon(icon_path))
            button.setIconSize(QSize(18, 18))

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

        old_block_state = self.sidebar_list.blockSignals(True)

        try:
            while self.sidebar_list.count():
                item = self.sidebar_list.takeItem(0)
                if item is None:
                    continue

                widget = self.sidebar_list.itemWidget(item)
                if widget is not None:
                    self.sidebar_list.removeItemWidget(item)
                    widget.hide()
                    widget.deleteLater()

                del item

            if self.current_filter == 'chats':
                items = list(self.conversations.values())

            elif self.current_filter == 'rooms':
                room_names = {room.lower() for room in self.available_rooms}
                items = [
                    meta
                    for meta in self.conversations.values()
                    if meta.mode == 'room' and meta.name.lower() in room_names
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
                profile = self.user_profiles.get(meta.name.lower(), {})
                display_name = profile.get("display_name", meta.name)
                avatar_path = profile.get("profile_picture", "")

                haystack = f'{display_name} {meta.name} {meta.subtitle}'.lower()

                if query and query not in haystack:
                    continue

                widget = SidebarItem(
                    title=display_name,
                    subtitle=meta.subtitle,
                    trailing="",
                    avatar_text=display_name[:1],
                    accent=meta.accent,
                    online=False,
                    avatar_path=avatar_path,
                    unread_count=meta.unread_count,
                )

                widget.hide()

                item = QListWidgetItem()
                item.setData(Qt.UserRole, meta)
                item.setSizeHint(widget.minimumSizeHint())

                self.sidebar_list.addItem(item)

                self.sidebar_list.setItemWidget(item, widget)

        finally:
            self.sidebar_list.blockSignals(old_block_state)

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
        if hasattr(self.network_client, 'message_reaction_received'):
            self.network_client.message_reaction_received.connect(self._on_message_reaction)

        # Future-feature signals
        if hasattr(self.network_client, 'typing_received'):
            self.network_client.typing_received.connect(self._on_typing_received)

        if hasattr(self.network_client, 'message_status_received'):
            self.network_client.message_status_received.connect(self._on_message_status_received)

        if hasattr(self.network_client, 'profile_updated'):
            self.network_client.profile_updated.connect(self._on_profile_updated)

        if hasattr(self.network_client, 'moderation_notice_received'):
            self.network_client.moderation_notice_received.connect(self._on_moderation_notice)

        if hasattr(self.network_client, 'moderation_restriction_received'):
            self.network_client.moderation_restriction_received.connect(self._on_moderation_restriction)

    def _on_message_deleted(self, packet: dict):
        message_id = packet.get("message_id")
        record = self._find_message_data(message_id) if message_id else None
        if record:
            record["deleted"] = True
            record["message"] = "This message was deleted"
            record["reactions"] = {}
        widget = self.message_widgets.get(message_id)
        if widget and hasattr(widget, "mark_deleted"):
            widget.mark_deleted()

    def _on_message_reaction(self, packet: dict):
        message_id = packet.get("message_id")
        emoji = packet.get("emoji")
        count = packet.get("count")
        record = self._find_message_data(message_id) if message_id else None
        if record and emoji:
            reactions = record.setdefault("reactions", {})
            reactions[emoji] = count if count is not None else reactions.get(emoji, 0) + 1
        widget = self.message_widgets.get(message_id)
        if widget and hasattr(widget, "apply_reaction"):
            widget.apply_reaction(emoji, count)

    # =====================================================
    # 17. TARGET SELECTION
    # Triggered when a sidebar item is clicked.
    # =====================================================

    def _on_sidebar_item_clicked(self, item: QListWidgetItem) -> None:
        meta: ConversationMeta = item.data(Qt.UserRole)
        meta.unread_count = 0
        self._apply_target(meta.mode, None if meta.mode == 'public' else meta.name)
        self._rebuild_sidebar()

    def _set_header_avatar(self, text: str, avatar_path: str = '') -> None:
        if avatar_path and os.path.exists(avatar_path):
            pixmap = self._make_round_pixmap(avatar_path, 44)
            if not pixmap.isNull():
                self.header_avatar.setText('')
                self.header_avatar.setPixmap(pixmap)
                return
        self.header_avatar.setPixmap(QPixmap())
        self.header_avatar.setText((text or '?')[:1].upper())

    def _make_round_pixmap(self, image_path: str, size: int) -> QPixmap:
        original = QPixmap(image_path)
        if original.isNull():
            return QPixmap()

        # Render at 2x and assign devicePixelRatio so small avatars look
        # sharper on normal and high-DPI displays.
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

    def _apply_target(self, mode: str, target_name: Optional[str]) -> None:
        self.target_mode = mode
        self.target_name = target_name

        if mode == 'public':
            self.chat_title.setText('Public Chat')
            self.chat_subtitle.setText('Everyone can see messages here')
            self._set_header_avatar('P', '')

        elif mode == 'room':
            room = target_name or self.initial_room
            members = self.room_members.get(room.lower(), [])
            member_text = ', '.join(members[:6])
            if len(members) > 6:
                member_text += f', +{len(members) - 6}'
            self.chat_title.setText(room)
            self.chat_subtitle.setText(member_text or 'No room members yet')
            self._set_header_avatar((room or 'R')[:1].upper(), '')

        else:
            person = target_name or 'Direct Message'
            profile = self.user_profiles.get(person.lower(), {})
            self.chat_title.setText(person)
            self.chat_subtitle.setText(f'Private conversation with {person}')
            self._set_header_avatar(person[:1].upper(), profile.get('profile_picture', ''))

        self._update_admin_visibility()
        self._render_current_conversation()

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
        # Keep typing signals for other clients, but never show drafting/typing
        # text above the composer. The user requested a clean input area.
        self.typing_label.clear()
        self.typing_label.hide()
        if text.strip():
            self._send_typing_signal(is_typing=True)
            self.typing_timer.start(1200)
        else:
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
        # Intentionally hidden. Typing packets are still handled by the network
        # layer, but this UI no longer displays typing/drafting text.
        self.typing_label.clear()
        self.typing_label.hide()

    # =====================================================
    # 20. EMOJI PICKER
    # Opens emoji picker and inserts selected emoji.
    # =====================================================

    def _toggle_emoji_picker(self) -> None:
        if self.emoji_picker is None:
            self.emoji_picker = EmojiPicker(parent=self)
            self.emoji_picker.emoji_selected.connect(self._insert_emoji)

        if self.emoji_picker.isVisible():
            self.emoji_picker.hide()
            return

        if hasattr(self.emoji_picker, 'show_near'):
            self.emoji_picker.show_near(self.emoji_button, above=True)
        else:
            global_pos = self.emoji_button.mapToGlobal(
                QPoint(0, -self.emoji_picker.sizeHint().height())
            )
            self.emoji_picker.move(global_pos)
            self.emoji_picker.show()

    def _insert_emoji(self, emoji: str) -> None:
        self.message_input.insert(emoji)

        if self.emoji_picker is not None:
            self.emoji_picker.hide()

        self.message_input.setFocus()

    # =====================================================
    # 21. PROFILE AND ROOM DIALOGS
    # Opens profile edit and join room dialogs.
    # =====================================================

    def _open_profile_dialog(self) -> None:
        current_profile = self.user_profiles.get(self.username.lower(), {})
        current_avatar = current_profile.get("profile_picture", "")

        dialog = ProfileDialog(
            self.local_display_name,
            avatar_path=current_avatar,
            parent=self,
        )

        if not dialog.exec():
            return

        display_name = dialog.name_input.text().strip().rstrip("\\").strip()
        avatar_path = dialog.avatar_input.text().strip()

        if not display_name:
            display_name = self.local_display_name

        self.local_display_name = display_name
        self.user_name_label.setText(display_name)

        profile = self.user_profiles.setdefault(self.username.lower(), {})
        profile["username"] = self.username
        profile["display_name"] = display_name

        if avatar_path:
            profile["profile_picture"] = avatar_path
            self._apply_profile_image(avatar_path)

            if hasattr(self.network_client, "update_profile_picture"):
                self.network_client.update_profile_picture(avatar_path)
        else:
            self.user_avatar.setPixmap(QPixmap())
            self.user_avatar.setText(display_name[:1].upper())

        if hasattr(self.network_client, "update_profile"):
            self.network_client.update_profile(display_name, avatar_path)

        self._rebuild_sidebar()


    def _apply_profile_image(self, avatar_path: str) -> None:
        if not avatar_path or not os.path.exists(avatar_path):
            self.user_avatar.setPixmap(QPixmap())
            self.user_avatar.setText(self.local_display_name[:1].upper())
            return

        size = 46
        rounded = self._make_round_pixmap(avatar_path, size)

        if rounded.isNull():
            self.user_avatar.setPixmap(QPixmap())
            self.user_avatar.setText(self.local_display_name[:1].upper())
            return

        self.user_avatar.setFixedSize(size, size)
        self.user_avatar.setText("")
        self.user_avatar.setPixmap(rounded)

        if (
            hasattr(self, "header_avatar")
            and self.target_mode == "private"
            and self.target_name == self.username
        ):
            self._set_header_avatar(self.local_display_name, avatar_path)

    def _open_room_dialog(self) -> None:
        dialog = RoomDialog(self, users=[u for u in self.online_users if u != self.username])

        if dialog.exec():
            if getattr(dialog, "selected_mode", "join") == "create":
                room_name = dialog.create_room_input.text().strip()
                password = dialog.create_password_input.text().strip()
                members = dialog.get_selected_users()
                if room_name:
                    if hasattr(self.network_client, "create_room"):
                        self.network_client.create_room(room_name, password=password, members=members)
                    else:
                        self.network_client.join_room(room_name)
                    self._touch_private_meta(f"room:{room_name.lower()}", room_name, "Room conversation", "Room", mode="room")
                    self._apply_target("room", room_name)
            else:
                room_name = dialog.room_input.text().strip()
                password = dialog.password_input.text().strip()
                if room_name:
                    self.network_client.join_room(room_name, password=password)
                    self._touch_private_meta(f"room:{room_name.lower()}", room_name, "Room conversation", "Room", mode="room")
                    self._apply_target("room", room_name)

    # =====================================================
    # 22. REPLY FEATURE
    # Shows, clears, and stores reply context.
    # =====================================================

    def _clear_reply(self) -> None:
        self.reply_context = None

        if hasattr(self, "reply_bar"):
            self.reply_bar.hide()

        if hasattr(self, "inline_reply_frame"):
            self.inline_reply_frame.hide()

    def _show_reply_bar(self, reply_payload: dict) -> None:
        self.reply_context = reply_payload

        preview_text = reply_payload['message']

        if len(preview_text) > 80:
            preview_text = preview_text[:77] + '...'

        if hasattr(self, "inline_reply_sender"):
            self.inline_reply_sender.setText(f"Replying to {reply_payload['sender']}")
            self.inline_reply_message.setText(preview_text)
            self.inline_reply_frame.show()
        else:
            self.reply_label.setText(f"Replying to {reply_payload['sender']}: {preview_text}")
            self.reply_bar.show()

    # =====================================================
    # 23. SEND MESSAGE
    # Sends message based on current target mode.
    # =====================================================

    def send_message(self) -> None:
        message = self.message_input.text().strip()

        if not message:
            return

        if not getattr(self.network_client, "connected", False):
            self._show_moderation_dialog(
                "You are no longer connected to this chat and cannot send messages."
            )
            return

        current_key = self._current_conversation_key()
        if current_key in self.restricted_conversations:
            self._show_moderation_dialog(
                "You have been removed from this chat and cannot send messages here anymore."
            )
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


            local_id = f"local_{uuid.uuid4().hex}"
            self._add_message(
                sender='You',
                message=message,
                own=True,
                status_text='sent',
                reply_to=reply_payload,
                message_id=local_id,
                sender_profile_picture='',
                reactions={},
                conversation_key=self._current_conversation_key(),
            )
            pending_record = self._find_message_data(local_id)
            if pending_record:
                pending_record['pending'] = True

            self._update_conversation_preview(message)
            self.message_input.clear()
            self.typing_label.clear()
            self.typing_label.hide()
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
        sender_profile_picture: str = "",
        reactions: Optional[dict] = None,
        conversation_key: Optional[str] = None,
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

        key = conversation_key or self._current_conversation_key()

        # If this is the server echo of a message we already displayed
        # optimistically, update that local record instead of creating a duplicate.
        if own and message_id and not str(message_id).startswith('local_'):
            for existing in reversed(self.message_history.get(key, [])):
                if (
                    existing.get('kind') == 'message'
                    and existing.get('pending')
                    and existing.get('own')
                    and existing.get('message') == message
                ):
                    old_id = existing.get('message_id')
                    if old_id:
                        self.message_to_conversation.pop(old_id, None)
                    existing['message_id'] = message_id
                    existing['status'] = status_text
                    existing['reply_to'] = reply_to_data
                    existing['reactions'] = reactions or existing.get('reactions', {})
                    existing['pending'] = False
                    self.message_to_conversation[message_id] = key
                    if key == self._current_conversation_key():
                        self._render_current_conversation(scroll_to_bottom=True)
                    return

        record = {
            'kind': 'message',
            'conversation_key': key,
            'message_id': message_id,
            'sender': sender,
            'message': message,
            'timestamp': datetime.now().strftime('%I:%M %p').lstrip('0'),
            'status': status_text,
            'reply_to': reply_to_data,
            'reactions': reactions or {},
            'own': own,
            'avatar_path': sender_profile_picture,
            'conversation_mode': 'private' if key.startswith('user:') else 'room' if key.startswith('room:') else 'public',
            'deleted': False,
            'pending': str(message_id).startswith('local_'),
        }

        if message_id not in self.message_to_conversation:
            self.message_history.setdefault(key, []).append(record)
            self.message_to_conversation[message_id] = key
        else:
            stored = self._find_message_data(message_id)
            if stored:
                stored.update(record)

        if key == self._current_conversation_key():
            self._render_current_conversation(scroll_to_bottom=True)

    def _current_conversation_key(self, mode: Optional[str] = None, target_name: Optional[str] = None) -> str:
        mode = mode or self.target_mode
        target_name = self.target_name if target_name is None else target_name
        if mode == 'public':
            return 'public'
        if mode == 'room':
            return f"room:{(target_name or self.initial_room).lower()}"
        return f"user:{(target_name or '').lower()}"

    def _clear_messages_layout(self) -> None:
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            widget = item.widget()

            if widget is None:
                continue

            if widget is getattr(self, 'empty_state', None):
                widget.hide()
                continue

            widget.hide()
            widget.deleteLater()

    def _make_notice_label(self, text: str) -> QLabel:
        notice = QLabel(text)
        notice.setObjectName('systemNotice')
        notice.setAlignment(Qt.AlignCenter)
        return notice

    def _build_message_widget(self, record: dict, show_sender: bool) -> MessageBubble:
        is_private = record.get('conversation_mode') == 'private'
        bubble = MessageBubble(
            record,
            own=bool(record.get('own')),
            avatar_path='' if is_private else record.get('avatar_path', ''),
            show_sender=False if is_private else show_sender,
            compact_private=is_private,
        )
        bubble.reply_requested.connect(self._show_reply_bar)
        if hasattr(bubble, 'reaction_requested'):
            bubble.reaction_requested.connect(self._react_to_message)
        if hasattr(bubble, 'local_delete_requested'):
            bubble.local_delete_requested.connect(self._delete_message_for_everyone)
        return bubble

    def _render_current_conversation(self, scroll_to_bottom: bool = False) -> None:
        if not hasattr(self, 'messages_layout'):
            return

        key = self._current_conversation_key()
        records = self.message_history.get(key, [])
        self.message_widgets = {}
        self._clear_messages_layout()

        if not records:
            self._refresh_empty_state()
            self.messages_layout.addStretch(1)
            self.messages_layout.addWidget(self.empty_state, alignment=Qt.AlignCenter)
            self.messages_layout.addStretch(1)
            self.empty_state.show()
            return

        self.empty_state.hide()
        previous_group = None
        for record in records:
            if record.get('kind') == 'notice':
                self.messages_layout.addWidget(self._make_notice_label(record.get('message', '')))
                previous_group = None
                continue

            group_key = (record.get('sender'), bool(record.get('own')))
            show_sender = group_key != previous_group
            previous_group = group_key
            widget = self._build_message_widget(record, show_sender)
            message_id = record.get('message_id')
            if message_id:
                self.message_widgets[message_id] = widget
            self.messages_layout.addWidget(widget)

        self.messages_layout.addStretch(1)
        if scroll_to_bottom:
            QTimer.singleShot(0, self._scroll_to_bottom)

    def _find_message_data(self, message_id: str) -> Optional[dict]:
        key = self.message_to_conversation.get(message_id)
        if not key:
            return None
        for record in self.message_history.get(key, []):
            if record.get('message_id') == message_id:
                return record
        return None

    def _add_notice_to_conversation(self, conversation_key: str, message: str) -> None:
        self.message_history.setdefault(conversation_key, []).append({
            'kind': 'notice',
            'conversation_key': conversation_key,
            'message': message,
        })
        if conversation_key == self._current_conversation_key():
            self._render_current_conversation(scroll_to_bottom=True)

    def _delete_local_message(self, message_id: str) -> None:
        widget = self.message_widgets.pop(message_id, None)

        if widget:
            widget.hide()
            widget.deleteLater()

    def _refresh_empty_state(self) -> None:
        if not hasattr(self, 'empty_state'):
            return
        has_messages = bool(self.message_history.get(self._current_conversation_key(), []))
        self.empty_state.setVisible(not has_messages)
        if self.target_mode == 'public':
            self.empty_title.setText('Public Chat is ready')
            self.empty_subtitle.setText('Say hello and start the public conversation.')
        elif self.target_mode == 'room':
            self.empty_title.setText(f'{self.target_name or "Room"} is quiet')
            self.empty_subtitle.setText('Share the first room message with your members.')
        else:
            self.empty_title.setText(f'Start chatting with {self.target_name or "this user"}')
            self.empty_subtitle.setText('Send a message to begin this private conversation.')

    def _scroll_to_bottom(self) -> None:
        bar = self.messages_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _delete_message_for_everyone(self, message_id: str):
        record = self._find_message_data(message_id)
        if record:
            record['deleted'] = True
            record['message'] = 'This message was deleted'
            record['reactions'] = {}
        widget = self.message_widgets.get(message_id)
        if widget and hasattr(widget, 'mark_deleted'):
            widget.mark_deleted()

        if hasattr(self.network_client, 'delete_message'):
            self.network_client.delete_message(message_id)

    def _react_to_message(self, message_id: str, emoji: str):
        record = self._find_message_data(message_id)
        if record and emoji and not record.get('deleted'):
            reactions = record.setdefault('reactions', {})
            reactions[emoji] = reactions.get(emoji, 0) + 1
        widget = self.message_widgets.get(message_id)
        if widget and hasattr(widget, 'apply_reaction'):
            widget.apply_reaction(emoji)
        if hasattr(self.network_client, 'react_to_message'):
            self.network_client.react_to_message(message_id, emoji)

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
            sender_profile_picture=packet.get('sender_profile_picture', ''),
            reactions=packet.get('reactions', {}),
            conversation_key='public',
        )

        self._touch_private_meta(
            'public',
            'Public Chat',
            message,
            'Now',
            mode='public',
        )
        self._increase_unread_if_needed('public', incoming=not own)
        self._rebuild_sidebar()


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
            sender_profile_picture=packet.get('sender_profile_picture', ''),
            reactions=packet.get('reactions', {}),
            conversation_key=f"user:{(((packet.get('target') or self.target_name or sender) if own else sender)).lower()}",
        )

        other_user = (packet.get('target') or self.target_name or sender) if own else sender
        key = f'user:{other_user.lower()}'
        self._touch_private_meta(
            key,
            other_user,
            message,
            'DM',
            mode='private',
        )
        self._increase_unread_if_needed(key, incoming=not own)
        self._rebuild_sidebar()


    def _on_room_message(self, packet: dict) -> None:
        sender = packet.get('sender', 'Unknown')
        room = packet.get('room', 'Room')
        message = packet.get('message', '')

        own = sender == self.username

        self._add_message(
            sender='You' if own else sender,
            message=message,
            own=own,
            status_text=packet.get('status', ''),
            reply_to=packet.get('reply_to'),
            message_id=packet.get('message_id'),
            sender_profile_picture=packet.get('sender_profile_picture', ''),
            reactions=packet.get('reactions', {}),
            conversation_key=f'room:{room.lower()}',
        )

        key = f'room:{room.lower()}'
        self._touch_private_meta(
            key,
            room,
            message,
            'Room',
            mode='room',
        )
        self._increase_unread_if_needed(key, incoming=not own)
        self._rebuild_sidebar()
    # =====================================================
    # 26. SYSTEM NOTICES
    # Join, leave, and room joined notices.
    # =====================================================

    def _on_notice(self, message: str) -> None:
        self._add_notice_to_conversation('public', message)

    def _on_room_joined(self, message: str) -> None:
        self._add_notice_to_conversation(self._current_conversation_key(), message)

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
            f"you are online · {len(normalized_users)} users"
        )

        self._rebuild_sidebar()

    def _update_room_list(self, rooms: list[str]) -> None:
        normalized_rooms = []
        self.room_members = {}

        for item in rooms:
            if isinstance(item, dict):
                room = str(item.get('name') or item.get('room') or '').strip()
                members = [str(member) for member in item.get('members', []) if member]
            else:
                room = str(item).strip()
                members = []

            if not room:
                continue

            normalized_rooms.append(room)
            self.room_members[room.lower()] = members

            member_preview = ', '.join(members[:4])
            if len(members) > 4:
                member_preview += f', +{len(members) - 4}'

            self._touch_private_meta(
                f'room:{room.lower()}',
                room,
                member_preview or 'Room conversation',
                'Room',
                mode='room',
            )

        self.available_rooms = normalized_rooms

        if self.target_mode == 'room':
            self._apply_target('room', self.target_name)

        self._rebuild_sidebar()

    # =====================================================
    # 28. CONVERSATION PREVIEW / SIDEBAR META
    # Updates latest message preview in sidebar.
    # =====================================================

    def _conversation_key_for_packet(self, mode: str, sender: str = "", room: str = "") -> str:
        if mode == "public":
            return "public"
        if mode == "room":
            return f"room:{room.lower()}"
        other = self.target_name if sender == self.username else sender
        return f"user:{other.lower()}"

    def _is_current_conversation(self, mode: str, key: str) -> bool:
        if self.target_mode == "public" and key == "public":
            return True
        if self.target_mode == "room" and self.target_name and key == f"room:{self.target_name.lower()}":
            return True
        if self.target_mode == "private" and self.target_name and key == f"user:{self.target_name.lower()}":
            return True
        return False

    def _increase_unread_if_needed(self, key: str, incoming: bool) -> None:
        if not incoming or self._is_current_conversation(self.target_mode, key):
            return
        meta = self.conversations.get(key)
        if meta:
            meta.unread_count += 1

    def _touch_private_meta(
        self,
        key: str,
        name: str,
        subtitle: str,
        trailing: str,
        mode: str = 'private',
    ) -> None:
        old_unread = self.conversations.get(key).unread_count if key in self.conversations else 0
        self.conversations[key] = ConversationMeta(
            key=key,
            mode=mode,
            name=name,
            subtitle=subtitle,
            trailing=trailing,
            online=(mode == 'private'),
            accent=(mode == 'public'),
            unread_count=old_unread,
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

        record = self._find_message_data(message_id)
        if record:
            record['status'] = status

        widget = self.message_widgets.get(message_id)

        if widget and hasattr(widget, 'update_status'):
            widget.update_status(status)

    def _conversation_key_from_moderation_packet(self, packet: dict) -> str:
        mode = packet.get("target_mode") or packet.get("mode") or packet.get("scope") or "public"
        room = packet.get("room") or packet.get("target_room") or ""

        if mode == "room" and room:
            return f"room:{room.lower()}"

        if mode == "private" and packet.get("target"):
            return f"user:{packet.get('target', '').lower()}"

        return "public"

    def _remove_user_from_room_header(self, username: str, room: str) -> None:
        if not username or not room:
            return

        members = self.room_members.get(room.lower(), [])
        self.room_members[room.lower()] = [
            member for member in members
            if member.lower() != username.lower()
        ]

        if self.target_mode == "room" and self.target_name and self.target_name.lower() == room.lower():
            self._apply_target("room", self.target_name)

    def _remove_rejected_local_messages(self, conversation_key: str) -> None:
        records = self.message_history.get(conversation_key, [])
        if not records:
            return

        kept_records = []
        removed_ids = []

        for record in records:
            message_id = str(record.get("message_id", ""))
            should_remove = (
                record.get("kind") == "message"
                and record.get("own")
                and (record.get("pending") or message_id.startswith("local_"))
            )

            if should_remove:
                if message_id:
                    removed_ids.append(message_id)
                continue

            kept_records.append(record)

        if len(kept_records) == len(records):
            return

        self.message_history[conversation_key] = kept_records

        for message_id in removed_ids:
            self.message_to_conversation.pop(message_id, None)

        if conversation_key == self._current_conversation_key():
            self._render_current_conversation(scroll_to_bottom=True)

    def _on_moderation_notice(self, packet: dict) -> None:
        message = packet.get("message") or packet.get("notice")
        if not message:
            actor = packet.get("sender") or packet.get("admin") or "Admin"
            action = packet.get("action") or "removed"
            target = packet.get("target") or packet.get("username") or "a user"
            message = f"{actor} {action} {target}."

        key = self._conversation_key_from_moderation_packet(packet)
        self._add_notice_to_conversation(key, message)

        target = packet.get("target") or packet.get("username")
        room = packet.get("room") or packet.get("target_room")
        if target and room:
            self._remove_user_from_room_header(target, room)

    def _on_moderation_restriction(self, packet: dict) -> None:
        key = self._conversation_key_from_moderation_packet(packet)
        self.restricted_conversations.add(key)
        self._remove_rejected_local_messages(key)
        self._on_moderation_notice(packet)

        dialog_message = (
            packet.get("dialog_message")
            or packet.get("message")
            or "You have been removed from this chat and cannot send messages here anymore."
        )
        self._show_moderation_dialog(dialog_message)

    def _show_moderation_dialog(self, message: str) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Talkify")
        dialog.setText(message)
        dialog.setIcon(QMessageBox.Warning)
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
        current_profile["username"] = updated_user

        if display_name:
            current_profile["display_name"] = display_name

        if profile_picture:
            current_profile["profile_picture"] = profile_picture

        self.user_profiles[key] = current_profile

        if updated_user == self.username:
            if display_name:
                self.local_display_name = display_name
                self.user_name_label.setText(display_name)

                if not profile_picture:
                    self.user_avatar.setText(display_name[:1].upper())

            if profile_picture:
                self._apply_profile_image(profile_picture)

        self._rebuild_sidebar()

        if self.target_mode == 'private' and self.target_name and self.target_name.lower() == key:
            self._apply_target('private', self.target_name)
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
        if not message:
            return

        moderation_phrases = (
            "kicked",
            "banned",
            "removed from this chat",
            "cannot send messages",
            "not a member of room",
        )
        if any(phrase in message.lower() for phrase in moderation_phrases):
            self._show_moderation_dialog(message)
            return

        print("[TALKIFY ERROR]:", message)
        return


    def _show_info(self, message: str) -> None:
        if not message:
            return

        print("[TALKIFY INFO]:", message)
        return

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
        # Keep disconnect silent to avoid accidental pop-up flashes while interacting with the window.
        pass

    def closeEvent(self, event) -> None:
        self.network_client.disconnect()
        super().closeEvent(event)