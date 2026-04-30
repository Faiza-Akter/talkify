from __future__ import annotations

import os

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QPainterPath, QPixmap, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)


class RoomDialog(QDialog):
    def __init__(self, parent=None, users=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Rooms")
        self.setModal(True)
        self.setObjectName("roomDialog")
        self.setFixedSize(430, 620)

        self.selected_mode = "join"
        self.users = users or []
        self.parent_window = parent

        icons_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
        circle_plus_icon = os.path.join(icons_dir, "circle-plus.svg")
        door_open_icon = os.path.join(icons_dir, "door-open.svg")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("roomPlainHeader")
        header.setFixedHeight(94)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 10, 18, 10)
        header_layout.setSpacing(14)

        self.avatar_label = QLabel("💬")
        self.avatar_label.setObjectName("dialogHeroIcon")
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setFixedSize(58, 58)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Rooms")
        title.setObjectName("dialogTitle")

        subtitle = QLabel("Join a room or create a private space.")
        subtitle.setObjectName("dialogHint")
        subtitle.setWordWrap(True)

        title_box.addStretch()
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addStretch()

        header_layout.addWidget(self.avatar_label, alignment=Qt.AlignVCenter)
        header_layout.addLayout(title_box, 1)

        header_line = QFrame()
        header_line.setFrameShape(QFrame.HLine)
        header_line.setObjectName("roomHeaderLine")
        header_line.setFixedHeight(1)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)

        self.join_tab = QPushButton("  Join Room")
        self.join_tab.setObjectName("filterButton")
        self.join_tab.setCheckable(True)
        self.join_tab.setChecked(True)
        self.join_tab.setIcon(QIcon(circle_plus_icon))
        self.join_tab.setIconSize(QSize(18, 18))
        self.join_tab.setFixedHeight(36)
        self.join_tab.clicked.connect(lambda: self._switch("join"))

        self.create_tab = QPushButton("  Create Room")
        self.create_tab.setObjectName("filterButton")
        self.create_tab.setCheckable(True)
        self.create_tab.setIcon(QIcon(door_open_icon))
        self.create_tab.setIconSize(QSize(18, 18))
        self.create_tab.setFixedHeight(36)
        self.create_tab.clicked.connect(lambda: self._switch("create"))

        tab_row.addWidget(self.join_tab)
        tab_row.addWidget(self.create_tab)

        self.stack = QStackedWidget()
        self.stack.setFixedHeight(350)
        self.stack.addWidget(self._build_join_page())
        self.stack.addWidget(self._build_create_page())

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 2, 0, 0)
        actions.setSpacing(10)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("ghostToolButton")
        self.cancel_button.setFixedSize(84, 34)
        self.cancel_button.clicked.connect(self.reject)

        self.ok_button = QPushButton("Join Room")
        self.ok_button.setObjectName("primaryButton")
        self.ok_button.setFixedSize(124, 34)
        self.ok_button.setStyleSheet("""
            QPushButton#primaryButton {
                font-size: 14px;
                font-weight: 800;
            }
        """)
        self.ok_button.clicked.connect(self.accept)

        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.ok_button)
        actions.addStretch()

        root.addWidget(header)
        root.addWidget(header_line)
        root.addLayout(tab_row)
        root.addWidget(self.stack)
        root.addLayout(actions)

    def _build_join_page(self):
        page = QFrame()
        page.setObjectName("dialogGlassCard")

        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(18, 16, 18, 16)
        outer_layout.setSpacing(0)

        content = QVBoxLayout()
        content.setSpacing(6)

        helper = QLabel("Use the room name and password shared by the creator.")
        helper.setObjectName("dialogHint")
        helper.setWordWrap(True)
        helper.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        room_label = QLabel("ROOM NAME")
        room_label.setObjectName("fieldLabel")

        self.room_input = QLineEdit()
        self.room_input.setObjectName("profileInput")
        self.room_input.setPlaceholderText("e.g. work or friends")
        self.room_input.setFixedHeight(32)

        password_label = QLabel("ROOM PASSWORD")
        password_label.setObjectName("fieldLabel")

        self.password_input = QLineEdit()
        self.password_input.setObjectName("profileInput")
        self.password_input.setPlaceholderText("Enter password if required")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(32)

        content.addSpacing(6)
        content.addWidget(room_label)
        content.addWidget(self.room_input)

        content.addSpacing(6)
        content.addWidget(password_label)
        content.addWidget(self.password_input)

        content.addSpacing(14)
        helper.setFixedHeight(44)
        content.addWidget(helper)

        outer_layout.addLayout(content)
        outer_layout.addStretch(1)

        return page

    def _build_create_page(self):
        page = QFrame()
        page.setObjectName("dialogGlassCard")

        icons_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
        search_icon = os.path.join(icons_dir, "search.svg")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        room_label = QLabel("ROOM NAME")
        room_label.setObjectName("fieldLabel")

        self.create_room_input = QLineEdit()
        self.create_room_input.setObjectName("profileInput")
        self.create_room_input.setPlaceholderText("e.g. Work or Friends")
        self.create_room_input.setFixedHeight(28)

        users_label = QLabel("SELECT USERS")
        users_label.setObjectName("fieldLabel")

        self.user_search = QLineEdit()
        self.user_search.setObjectName("profileInput")
        self.user_search.setPlaceholderText("Search users...")
        self.user_search.setFixedHeight(25)
        self.user_search.addAction(QIcon(search_icon), QLineEdit.LeadingPosition)
        self.user_search.textChanged.connect(self._filter_users)

        self.users_list = QListWidget()
        self.users_list.setObjectName("dialogUserList")
        self.users_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.users_list.setFixedHeight(85)
        self._fill_users()

        password_label = QLabel("SET PASSWORD")
        password_label.setObjectName("fieldLabel")

        self.create_password_input = QLineEdit()
        self.create_password_input.setObjectName("profileInput")
        self.create_password_input.setPlaceholderText("Required for outsiders to join")
        self.create_password_input.setEchoMode(QLineEdit.Password)
        self.create_password_input.setFixedHeight(28)

        note = QLabel("Outsiders can join using this room name and password.")
        note.setObjectName("dialogHint")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)

        layout.addWidget(room_label)
        layout.addWidget(self.create_room_input)
        layout.addSpacing(3)
        layout.addWidget(users_label)
        layout.addWidget(self.user_search)
        layout.addWidget(self.users_list)
        layout.addSpacing(3)
        layout.addWidget(password_label)
        layout.addWidget(self.create_password_input)
        layout.addWidget(note)

        return page

    def _switch(self, mode):
        self.selected_mode = mode

        self.join_tab.setChecked(mode == "join")
        self.create_tab.setChecked(mode == "create")
        self.stack.setCurrentIndex(0 if mode == "join" else 1)

        self.ok_button.setText("Join Room" if mode == "join" else "Create Room")
        self.ok_button.setFixedSize(124 if mode == "join" else 145, 34)

    def _fill_users(self):
        self.users_list.clear()

        for user in self.users:
            item = QListWidgetItem()
            checkbox = QCheckBox(user)
            checkbox.setObjectName("dialogCheck")

            item.setSizeHint(checkbox.sizeHint())
            self.users_list.addItem(item)
            self.users_list.setItemWidget(item, checkbox)

    def _filter_users(self, text):
        text = text.lower().strip()

        for i in range(self.users_list.count()):
            item = self.users_list.item(i)
            widget = self.users_list.itemWidget(item)

            if widget:
                item.setHidden(bool(text and text not in widget.text().lower()))

    def get_selected_users(self):
        selected = []

        for i in range(self.users_list.count()):
            widget = self.users_list.itemWidget(self.users_list.item(i))

            if widget and widget.isChecked():
                selected.append(widget.text())

        return selected

    def _current_user_initial(self) -> str:
        name = getattr(self.parent_window, "local_display_name", "") or getattr(
            self.parent_window, "username", "U"
        )
        return name[:1].upper()

    def _load_current_avatar(self) -> None:
        if not self.parent_window:
            return

        username = getattr(self.parent_window, "username", "")
        profiles = getattr(self.parent_window, "user_profiles", {})
        profile = profiles.get(username.lower(), {}) if username else {}
        avatar_path = profile.get("profile_picture", "")

        if avatar_path and os.path.exists(avatar_path):
            pixmap = self._make_round_pixmap(avatar_path, 58)

            if not pixmap.isNull():
                self.avatar_label.setText("")
                self.avatar_label.setPixmap(pixmap)

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