"""
Status Label Widget - Enhanced QLabel with icon support
Can display icons inline with text for status messages

Author: chamnv-dev
Date: 2025-11-07
Version: 1.0.0
"""

from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class StatusLabel(QWidget):
    """
    A label widget that can display an icon alongside text
    Useful for status messages, errors, warnings, etc.
    """
    
    def __init__(
        self,
        text: str = "",
        icon_type: str = None,
        icon_size: int = 16,
        parent=None
    ):
        """
        Initialize status label
        
        Args:
            text: Text to display
            icon_type: Type of icon (error, warning, success, info) or None
            icon_size: Size of the icon in pixels
            parent: Parent widget
        """
        super().__init__(parent)
        self.icon_size = icon_size
        self.icon_type = icon_type
        
        self._setup_ui(text)
    
    def _setup_ui(self, text: str):
        """Setup the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Icon label (if icon type is specified)
        if self.icon_type:
            self.icon_label = QLabel()
            self.icon_label.setAlignment(Qt.AlignCenter)
            self._update_icon()
            layout.addWidget(self.icon_label)
        else:
            self.icon_label = None
        
        # Text label
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label)
        
        layout.addStretch()
    
    def _update_icon(self):
        """Update the icon display"""
        if not self.icon_label or not self.icon_type:
            return
        
        try:
            from utils.icon_utils import load_icon_pixmap, EMOJI_FALLBACKS
            
            # Try to load icon image
            pixmap = load_icon_pixmap(self.icon_type, size=(self.icon_size, self.icon_size))
            
            if pixmap:
                self.icon_label.setPixmap(pixmap)
            else:
                # Fallback to emoji
                emoji = EMOJI_FALLBACKS.get(self.icon_type, '•')
                self.icon_label.setText(emoji)
                self.icon_label.setFont(QFont("Segoe UI", int(self.icon_size * 0.8)))
        except Exception:
            # Ultimate fallback to default emoji
            emoji_map = {
                'error': '❌',
                'warning': '⚠️',
                'success': '✅',
                'info': 'ℹ️'
            }
            emoji = emoji_map.get(self.icon_type, '•')
            self.icon_label.setText(emoji)
            self.icon_label.setFont(QFont("Segoe UI", int(self.icon_size * 0.8)))
    
    def setText(self, text: str):
        """Set the text"""
        self.text_label.setText(text)
    
    def text(self) -> str:
        """Get the text"""
        return self.text_label.text()
    
    def setIcon(self, icon_type: str):
        """Change the icon type"""
        self.icon_type = icon_type
        if self.icon_label:
            self._update_icon()
        elif icon_type:
            # Need to recreate layout with icon
            # Clear current layout
            while self.layout().count():
                child = self.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Recreate with icon
            current_text = self.text_label.text() if hasattr(self, 'text_label') else ""
            self._setup_ui(current_text)
    
    def setStyleSheet(self, style: str):
        """Apply stylesheet to text label"""
        if hasattr(self, 'text_label'):
            self.text_label.setStyleSheet(style)
    
    def setFont(self, font: QFont):
        """Set font for text label"""
        if hasattr(self, 'text_label'):
            self.text_label.setFont(font)
    
    def setAlignment(self, alignment):
        """Set alignment for text label"""
        if hasattr(self, 'text_label'):
            self.text_label.setAlignment(alignment)


# Convenience factory functions
def create_error_label(text: str, icon_size: int = 16, parent=None) -> StatusLabel:
    """Create an error status label"""
    return StatusLabel(text, "error", icon_size, parent)


def create_warning_label(text: str, icon_size: int = 16, parent=None) -> StatusLabel:
    """Create a warning status label"""
    return StatusLabel(text, "warning", icon_size, parent)


def create_success_label(text: str, icon_size: int = 16, parent=None) -> StatusLabel:
    """Create a success status label"""
    return StatusLabel(text, "success", icon_size, parent)


def create_info_label(text: str, icon_size: int = 16, parent=None) -> StatusLabel:
    """Create an info status label"""
    return StatusLabel(text, "info", icon_size, parent)
