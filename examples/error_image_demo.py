"""
Demo: Error Image Display Examples
Demonstrates various ways to use error images in the application

Usage:
    python examples/error_image_demo.py
    
Author: chamnv-dev
Date: 2025-11-07
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from utils.icon_utils import (
    get_error_icon, get_warning_icon, get_success_icon, get_info_icon,
    has_icon_support, get_icon_status
)
from ui.widgets.error_display import (
    create_error_display, create_warning_display,
    create_success_display, create_info_display
)
from ui.widgets.status_label import (
    create_error_label, create_warning_label,
    create_success_label, create_info_label
)


class ErrorImageDemo(QMainWindow):
    """Demo window showing error image usage examples"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Error Image Display Demo")
        self.setMinimumSize(900, 700)

        # Create central widget with scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Header
        header = QLabel("Error Image Display Examples")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #1E88E5; padding: 20px;")
        main_layout.addWidget(header)

        # Icon status
        status_text = "✅ Icon files available" if has_icon_support() else "⚠️ Using emoji fallback"
        status_label = QLabel(status_text)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("color: #666; padding-bottom: 10px;")
        main_layout.addWidget(status_label)

        # Scroll area for examples
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Example 1: Icon Pixmaps
        self._add_example_1(scroll_layout)

        # Example 2: Error Display Widgets (Standard)
        self._add_example_2(scroll_layout)

        # Example 3: Error Display Widgets (Compact)
        self._add_example_3(scroll_layout)

        # Example 4: Status Labels
        self._add_example_4(scroll_layout)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Footer
        footer = QLabel("See docs/ERROR_IMAGE_GUIDE.md for more information")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #888; padding: 10px;")
        main_layout.addWidget(footer)

    def _add_example_1(self, layout):
        """Example 1: Direct icon usage"""
        group = QGroupBox("Example 1: Direct Icon Pixmaps (QLabel)")
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        group_layout = QHBoxLayout()

        icons = [
            (get_error_icon, "Error", "#E53935"),
            (get_warning_icon, "Warning", "#FF8F00"),
            (get_success_icon, "Success", "#4CAF50"),
            (get_info_icon, "Info", "#1E88E5"),
        ]

        for icon_func, name, color in icons:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setAlignment(Qt.AlignCenter)

            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            pixmap = icon_func(size=(64, 64))
            if pixmap:
                icon_label.setPixmap(pixmap)
            else:
                # Fallback to first letter if icon not available
                fallback_char = {'Error': 'E', 'Warning': 'W', 'Success': 'S', 'Info': 'I'}
                icon_label.setText(fallback_char.get(name, '?'))
                icon_label.setFont(QFont("Segoe UI", 32))
            container_layout.addWidget(icon_label)

            text_label = QLabel(name)
            text_label.setAlignment(Qt.AlignCenter)
            text_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
            text_label.setStyleSheet(f"color: {color};")
            container_layout.addWidget(text_label)

            group_layout.addWidget(container)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _add_example_2(self, layout):
        """Example 2: ErrorDisplayWidget (standard layout)"""
        group = QGroupBox("Example 2: ErrorDisplayWidget - Standard Vertical Layout")
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        group_layout = QVBoxLayout()

        examples = [
            (create_error_display, "Connection Failed", 
             "Could not connect to the server. Please check your network and try again."),
            (create_warning_display, "Low Disk Space",
             "Your disk is running low on space. Consider freeing up some space."),
            (create_success_display, "Upload Complete",
             "All 15 videos have been successfully uploaded to the cloud."),
            (create_info_display, "New Version Available",
             "Version 7.2.0 is now available. Update to get the latest features."),
        ]

        for func, title, message in examples:
            widget = func(title, message, compact=False)
            widget.setMaximumHeight(200)
            group_layout.addWidget(widget)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _add_example_3(self, layout):
        """Example 3: ErrorDisplayWidget (compact layout)"""
        group = QGroupBox("Example 3: ErrorDisplayWidget - Compact Horizontal Layout")
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        group_layout = QVBoxLayout()

        examples = [
            (create_error_display, "5 videos failed to process"),
            (create_warning_display, "Processing may take longer than usual"),
            (create_success_display, "All tasks completed successfully"),
            (create_info_display, "Background processing in progress"),
        ]

        for func, title in examples:
            widget = func(title, "", compact=True)
            widget.setMaximumHeight(60)
            group_layout.addWidget(widget)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _add_example_4(self, layout):
        """Example 4: Status labels"""
        group = QGroupBox("Example 4: StatusLabel - Icon + Text Inline")
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        group_layout = QVBoxLayout()

        examples = [
            (create_error_label, "3 failed, 12/15 OK", "#E53935"),
            (create_warning_label, "API rate limit approaching", "#FF8F00"),
            (create_success_label, "15/15 videos processed", "#4CAF50"),
            (create_info_label, "Processing time: 2m 34s", "#1E88E5"),
        ]

        for func, text, color in examples:
            label = func(text, icon_size=20)
            label.setStyleSheet(f"color: {color}; font-weight: bold; padding: 8px;")
            group_layout.addWidget(label)

        group.setLayout(group_layout)
        layout.addWidget(group)


def main():
    """Main entry point"""
    print("=" * 60)
    print("Error Image Display Demo")
    print("=" * 60)

    # Check icon support
    print(f"\nIcon support: {has_icon_support()}")
    print("\nIcon status:")
    for icon_type, available in get_icon_status().items():
        status = "✓" if available else "✗"
        print(f"  {status} {icon_type}")

    print("\n" + "=" * 60)
    print("Starting demo application...")
    print("=" * 60 + "\n")

    # Create application
    app = QApplication(sys.argv)

    # Create and show demo window
    demo = ErrorImageDemo()
    demo.show()

    # Run
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
