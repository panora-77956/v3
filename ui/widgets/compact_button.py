# -*- coding: utf-8 -*-
"""
Compact Button System - 32px height buttons
30% smaller than original design
"""

from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QWidget
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QSize, Qt

class CompactButton(QPushButton):
    """Standard compact button - 32px height"""

    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, parent)

        # Consistent sizing
        self.setMinimumHeight(32)
        self.setMaximumHeight(32)
        self.setFont(QFont("Segoe UI", 13))

        if icon:
            if isinstance(icon, str):
                self.setText(f"{icon} {text}")
            else:
                self.setIcon(icon)
                self.setIconSize(QSize(16, 16))

        # Compact padding
        self.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
            }
        """)

        self.setCursor(Qt.PointingHandCursor)

class CompactIconButton(QPushButton):
    """Icon-only button - 32x32px square"""

    def __init__(self, icon, tooltip="", parent=None):
        super().__init__(parent)

        if isinstance(icon, str):
            # Emoji/text icon
            self.setText(icon)
            self.setFont(QFont("Segoe UI", 14))
        else:
            # QIcon
            self.setIcon(icon)
            self.setIconSize(QSize(18, 18))

        self.setToolTip(tooltip)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet("""
            QPushButton {
                padding: 0;
                border-radius: 4px;
            }
        """)

class CompactButtonGroup(QWidget):
    """Horizontal group of related buttons"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        self.buttons = []

    def add_button(self, button):
        """Add button to group"""
        self.buttons.append(button)
        self.layout.addWidget(button)
        return button

    def add_stretch(self):
        """Add flexible space"""
        self.layout.addStretch()

# Helper functions
def create_compact_button(text, object_name=None, icon=None):
    """Quick create compact button"""
    btn = CompactButton(text, icon)
    if object_name:
        btn.setObjectName(object_name)
    return btn

def create_button_row(*buttons_data):
    """
    Create horizontal row of buttons
    
    Args:
        buttons_data: tuples of (text, object_name, icon)
    
    Returns:
        CompactButtonGroup widget
    """
    group = CompactButtonGroup()

    for data in buttons_data:
        if len(data) == 2:
            text, obj_name = data
            icon = None
        else:
            text, obj_name, icon = data

        btn = create_compact_button(text, obj_name, icon)
        group.add_button(btn)

    return group