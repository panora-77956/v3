# -*- coding: utf-8 -*-
"""
Responsive UI Utilities
Handle text ellipsis, DPI scaling, minimum sizes
"""

from PyQt5.QtWidgets import QLabel, QLineEdit
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import Qt

def elide_text(text, font, max_width, mode=Qt.ElideRight):
    """
    Elide text to fit width with ellipsis
    
    Args:
        text: Original text
        font: QFont to use
        max_width: Maximum width in pixels
        mode: Qt.ElideRight, Qt.ElideMiddle, or Qt.ElideLeft
    
    Returns:
        Elided text string
    """
    metrics = QFontMetrics(font)
    return metrics.elidedText(text, mode, max_width)

class ElidedLabel(QLabel):
    """QLabel that automatically elides text when resized"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def setText(self, text):
        self._full_text = text
        super().setText(text)
        self._elide_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide_text()

    def _elide_text(self):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.ElideRight, self.width())
        super().setText(elided)
        self.setToolTip(self._full_text if elided != self._full_text else "")

class ResponsiveLineEdit(QLineEdit):
    """QLineEdit with minimum height and responsive behavior"""

    def __init__(self, placeholder="", min_height=32, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(min_height)

def set_minimum_content_size(widget, min_width=None, min_height=None):
    """Set minimum size to prevent layout breaking"""
    if min_width:
        widget.setMinimumWidth(min_width)
    if min_height:
        widget.setMinimumHeight(min_height)

def calculate_optimal_width(text, font, padding=24):
    """Calculate optimal widget width for text"""
    metrics = QFontMetrics(font)
    return metrics.horizontalAdvance(text) + padding