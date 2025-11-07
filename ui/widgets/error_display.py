"""
Error Display Widget - Reusable widget for displaying errors with icons
Supports both image icons and emoji fallbacks

Author: chamnv-dev
Date: 2025-11-07
Version: 1.0.0
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class ErrorDisplayWidget(QWidget):
    """
    A reusable widget for displaying errors with icons
    
    Features:
    - Supports error, warning, success, and info icons
    - Automatic fallback to emoji if images are not available
    - Configurable size and layout
    - Optional detailed message
    """

    def __init__(
        self,
        title: str,
        message: str = "",
        icon_type: str = "error",
        icon_size: int = 64,
        compact: bool = False,
        parent=None
    ):
        """
        Initialize error display widget
        
        Args:
            title: Main title/heading text
            message: Optional detailed message
            icon_type: Type of icon (error, warning, success, info)
            icon_size: Size of the icon in pixels
            compact: If True, uses horizontal layout with smaller text
            parent: Parent widget
        """
        super().__init__(parent)
        self.icon_type = icon_type
        self.icon_size = icon_size
        self.compact = compact

        self._setup_ui(title, message)

    def _setup_ui(self, title: str, message: str):
        """Setup the UI components"""
        if self.compact:
            self._setup_compact_layout(title, message)
        else:
            self._setup_standard_layout(title, message)

    def _setup_standard_layout(self, title: str, message: str):
        """Setup standard vertical layout"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Icon
        icon_label = self._create_icon_label()
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(self._get_title_color())
        layout.addWidget(title_label)

        # Message
        if message:
            msg_label = QLabel(message)
            msg_label.setFont(QFont("Segoe UI", 11))
            msg_label.setAlignment(Qt.AlignCenter)
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet("color: #666; margin-top: 8px;")
            layout.addWidget(msg_label)

    def _setup_compact_layout(self, title: str, message: str):
        """Setup compact horizontal layout"""
        layout = QHBoxLayout(self)

        # Icon
        icon_label = self._create_icon_label()
        layout.addWidget(icon_label)

        # Text container
        text_layout = QVBoxLayout()

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_label.setStyleSheet(self._get_title_color())
        text_layout.addWidget(title_label)

        # Message
        if message:
            msg_label = QLabel(message)
            msg_label.setFont(QFont("Segoe UI", 10))
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet("color: #666;")
            text_layout.addWidget(msg_label)

        layout.addLayout(text_layout)
        layout.addStretch()

    def _create_icon_label(self) -> QLabel:
        """Create icon label with image or emoji"""
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)

        try:
            from utils.icon_utils import load_icon_pixmap, EMOJI_FALLBACKS

            # Try to load icon image
            pixmap = load_icon_pixmap(self.icon_type, size=(self.icon_size, self.icon_size))

            if pixmap:
                icon_label.setPixmap(pixmap)
            else:
                # Fallback to emoji
                emoji = EMOJI_FALLBACKS.get(self.icon_type, '•')
                icon_label.setText(emoji)
                emoji_size = self.icon_size // 2 if self.compact else self.icon_size // 1.5
                icon_label.setFont(QFont("Segoe UI", int(emoji_size)))
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            # Fallback to default emoji if icon utils fails
            emoji_map = {
                'error': '❌',
                'warning': '⚠️',
                'success': '✅',
                'info': 'ℹ️'
            }
            emoji = emoji_map.get(self.icon_type, '•')
            icon_label.setText(emoji)
            emoji_size = self.icon_size // 2 if self.compact else self.icon_size // 1.5
            icon_label.setFont(QFont("Segoe UI", int(emoji_size)))

        return icon_label

    def _get_title_color(self) -> str:
        """Get color style for title based on icon type"""
        color_map = {
            'error': '#E53935',    # Red
            'warning': '#FF8F00',  # Orange
            'success': '#4CAF50',  # Green
            'info': '#1E88E5'      # Blue
        }
        color = color_map.get(self.icon_type, '#666')
        return f"color: {color};"

    def update_message(self, title: str = None, message: str = None):
        """
        Update the displayed message
        
        NOTE: This operation recreates the entire widget layout which can be
        expensive. For better performance:
        - Create a new ErrorDisplayWidget instead of updating an existing one
        - Or use this method only for infrequent updates (e.g., on user action)
        
        Performance: O(n) where n is the number of child widgets
        """
        if title or message:
            # Clear old widgets
            while self.layout().count():
                child = self.layout().takeAt(0)
                if child.widget():
                    child.widget().setParent(None)

            # Rebuild with new content
            new_title = title if title else ""
            new_message = message if message else ""
            self._setup_ui(new_title, new_message)


# Convenience factory functions
def create_error_display(title: str, message: str = "", compact: bool = False, parent=None) -> ErrorDisplayWidget:
    """Create an error display widget"""
    return ErrorDisplayWidget(title, message, "error", compact=compact, parent=parent)


def create_warning_display(title: str, message: str = "", compact: bool = False, parent=None) -> ErrorDisplayWidget:
    """Create a warning display widget"""
    return ErrorDisplayWidget(title, message, "warning", compact=compact, parent=parent)


def create_success_display(title: str, message: str = "", compact: bool = False, parent=None) -> ErrorDisplayWidget:
    """Create a success display widget"""
    return ErrorDisplayWidget(title, message, "success", compact=compact, parent=parent)


def create_info_display(title: str, message: str = "", compact: bool = False, parent=None) -> ErrorDisplayWidget:
    """Create an info display widget"""
    return ErrorDisplayWidget(title, message, "info", compact=compact, parent=parent)
