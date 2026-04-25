from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class SidebarItem(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str,
        trailing: str = '',
        avatar_text: str = '',
        accent: bool = False,
        online: bool = False,
    ) -> None:
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        avatar = QFrame()
        avatar.setObjectName('sidebarAvatarAccent' if accent else 'sidebarAvatar')
        avatar.setFixedSize(42, 42)

        avatar_layout = QVBoxLayout(avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)

        avatar_label = QLabel((avatar_text or title[:1]).upper())
        avatar_label.setObjectName('sidebarAvatarText')
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_layout.addWidget(avatar_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        safe_title = title
        if len(safe_title) > 18:
            safe_title = safe_title[:15] + "..."

        title_label = QLabel(safe_title)
        title_label.setObjectName('sidebarItemTitle')
        
        safe_subtitle = subtitle
        if len(safe_subtitle) > 28:
            safe_subtitle = safe_subtitle[:25] + "..."

        subtitle_label = QLabel(safe_subtitle)
        subtitle_label.setObjectName('sidebarItemSubtitle')
        subtitle_label.setWordWrap(False)
        subtitle_label.setTextInteractionFlags(Qt.NoTextInteraction)

        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)

        trailing_layout = QVBoxLayout()
        trailing_layout.setSpacing(4)

        trailing_label = QLabel(trailing)
        trailing_label.setObjectName('sidebarItemTrailing')
        trailing_label.setAlignment(Qt.AlignRight | Qt.AlignTop)

        status_label = QLabel('● Online' if online else '')
        status_label.setObjectName('sidebarOnlineDot')
        status_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)

        trailing_layout.addWidget(trailing_label)
        trailing_layout.addWidget(status_label)
        trailing_layout.addStretch()

        layout.addWidget(avatar)
        layout.addLayout(text_layout, 1)
        layout.addLayout(trailing_layout)
