# -*- coding: utf-8 -*-
"""
Material Design Ripple Button
Implements ripple effect animation on click
"""

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QPainterPath
from PyQt5.QtCore import Qt, QPoint

class RippleButton(QPushButton):
    """QPushButton with Material Design ripple effect"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ripple_radius = 0
        self._ripple_pos = QPoint()
        self._ripple_animation = None
        self._ripple_color = QColor(255, 255, 255, 80)

    def mousePressEvent(self, event):
        """Start ripple animation on mouse press"""
        self._ripple_pos = event.pos()
        self._start_ripple()
        super().mousePressEvent(event)

    def _start_ripple(self):
        """Start the ripple animation"""
        # Calculate max radius (corner to corner)
        max_radius = max(self.width(), self.height()) * 1.5

        # Create animation
        self._ripple_animation = QPropertyAnimation(self, b"ripple_radius")
        self._ripple_animation.setDuration(600)  # 600ms duration
        self._ripple_animation.setStartValue(0)
        self._ripple_animation.setEndValue(max_radius)
        self._ripple_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._ripple_animation.finished.connect(self._reset_ripple)
        self._ripple_animation.start()

    def _reset_ripple(self):
        """Reset ripple after animation completes"""
        self._ripple_radius = 0
        self.update()

    @pyqtProperty(float)
    def ripple_radius(self):
        return self._ripple_radius

    @ripple_radius.setter
    def ripple_radius(self, value):
        self._ripple_radius = value
        self.update()  # Trigger repaint

    def paintEvent(self, event):
        """Custom paint to draw ripple effect"""
        super().paintEvent(event)

        if self._ripple_radius > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Clip to button shape
            path = QPainterPath()
            path.addRoundedRect(self.rect(), 20, 20)  # Match button border-radius
            painter.setClipPath(path)

            # Draw ripple
            painter.setBrush(self._ripple_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self._ripple_pos, self._ripple_radius, self._ripple_radius)
