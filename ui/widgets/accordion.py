# -*- coding: utf-8 -*-
"""
Accordion/Collapsible Widget for Material Design
Saves 60% vertical space for API keys sections
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal

class AccordionSection(QWidget):
    """Single collapsible section with smooth animation"""

    toggled = pyqtSignal(bool)

    def __init__(self, title="Section", parent=None):
        super().__init__(parent)
        self._is_expanded = False
        self._animation_duration = 250

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header toggle button
        self.toggle_button = QPushButton(f"▶ {title}")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 12px;
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                color: #424242;
            }
            QPushButton:hover {
                background: #EEEEEE;
                border-color: #BDBDBD;
            }
            QPushButton:checked {
                background: #E3F2FD;
                border-color: #1E88E5;
                color: #1565C0;
            }
        """)
        self.toggle_button.clicked.connect(self._on_toggle)
        main_layout.addWidget(self.toggle_button)

        # Content container
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setMaximumHeight(0)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_area.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-top: none;
                border-radius: 0 0 6px 6px;
            }
        """)

        # Content layout
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(12, 8, 12, 12)
        self.content_layout.setSpacing(8)

        main_layout.addWidget(self.content_area)

        # Animation
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(self._animation_duration)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)

    def add_content_widget(self, widget):
        """Add widget to collapsible content area"""
        self.content_layout.addWidget(widget)

    def add_content_layout(self, layout):
        """Add layout to content area"""
        self.content_layout.addLayout(layout)

    def _on_toggle(self):
        """Handle expand/collapse animation"""
        self._is_expanded = not self._is_expanded

        # Update arrow icon
        title = self.toggle_button.text()[2:]  # Remove existing arrow
        arrow = "▼" if self._is_expanded else "▶"
        self.toggle_button.setText(f"{arrow} {title}")
        self.toggle_button.setChecked(self._is_expanded)

        # Calculate target height
        if self._is_expanded:
            # Expand: calculate actual content height
            self.content_area.setMaximumHeight(16777215)  # Remove limit temporarily
            content_height = self.content_area.sizeHint().height()
            self.content_area.setMaximumHeight(0)  # Reset for animation
            target_height = content_height
        else:
            # Collapse
            target_height = 0

        # Animate
        self.animation.setStartValue(self.content_area.height())
        self.animation.setEndValue(target_height)
        self.animation.start()

        self.toggled.emit(self._is_expanded)

    def set_expanded(self, expanded):
        """Programmatically expand/collapse"""
        if self._is_expanded != expanded:
            self.toggle_button.click()

    def is_expanded(self):
        return self._is_expanded


class Accordion(QWidget):
    """Container for multiple accordion sections"""

    def __init__(self, parent=None, single_expand=False):
        """
        Args:
            single_expand: If True, only one section can be expanded at a time
        """
        super().__init__(parent)
        self.single_expand = single_expand
        self.sections = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

    def add_section(self, section):
        """Add existing section to accordion"""
        self.sections.append(section)
        self.layout.addWidget(section)

        if self.single_expand:
            section.toggled.connect(lambda expanded, s=section: self._on_section_toggled(s, expanded))

        return section

    def create_section(self, title):
        """Create and add new section"""
        section = AccordionSection(title, self)
        return self.add_section(section)

    def _on_section_toggled(self, toggled_section, expanded):
        """Handle single expand mode"""
        if expanded and self.single_expand:
            for section in self.sections:
                if section != toggled_section and section.is_expanded():
                    section.set_expanded(False)

    def expand_all(self):
        """Expand all sections"""
        for section in self.sections:
            if not section.is_expanded():
                section.set_expanded(True)

    def collapse_all(self):
        """Collapse all sections"""
        for section in self.sections:
            if section.is_expanded():
                section.set_expanded(False)