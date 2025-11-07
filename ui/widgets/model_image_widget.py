# -*- coding: utf-8 -*-
"""
Model Image Widget - Clickable image frame with delete button
"""
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget


class ModelImageWidget(QWidget):
    """
    Clickable image widget with upload and delete functionality
    Used for model/product image selection
    """

    image_changed = pyqtSignal(str)  # Emits file path when image changes
    image_removed = pyqtSignal()      # Emits when image is deleted

    def __init__(self, label_text: str = "Model Image", size: int = 128, parent=None):
        """
        Initialize model image widget
        
        Args:
            label_text: Label to display above the image
            size: Size of the image display area (width and height)
            parent: Parent widget
        """
        super().__init__(parent)
        self.size = size
        self.image_path = None
        self._build_ui(label_text)

    def _build_ui(self, label_text: str):
        """Build the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        self.label = QLabel(label_text)
        self.label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.label)

        # Image frame - clickable
        self.image_frame = QLabel()
        self.image_frame.setFixedSize(self.size, self.size)
        self.image_frame.setAlignment(Qt.AlignCenter)
        self.image_frame.setStyleSheet("""
            QLabel {
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
                background: #F5F5F5;
                color: #757575;
                font-size: 12px;
            }
            QLabel:hover {
                border-color: #2196F3;
                background: #E3F2FD;
                cursor: pointer;
            }
        """)
        self.image_frame.setText("Click to\nupload")
        self.image_frame.setWordWrap(True)
        self.image_frame.mousePressEvent = self._on_image_click
        layout.addWidget(self.image_frame)

        # Delete button (hidden initially)
        self.btn_delete = QPushButton("🗑 Remove")
        self.btn_delete.setObjectName('btn_delete_xoa')
        self.btn_delete.setFixedHeight(28)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_delete.hide()
        layout.addWidget(self.btn_delete)

    def _on_image_click(self, event):
        """Handle click on image frame"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )

        if file_path and os.path.exists(file_path):
            self.set_image(file_path)

    def set_image(self, file_path: str):
        """
        Set the image from file path
        
        Args:
            file_path: Path to image file
        """
        if not file_path or not os.path.exists(file_path):
            return

        # Load and display image
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            # Scale to fit while maintaining aspect ratio
            scaled = pixmap.scaled(
                self.size - 4,  # Account for border
                self.size - 4,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_frame.setPixmap(scaled)
            self.image_frame.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    background: white;
                }
                QLabel:hover {
                    border-color: #2196F3;
                    cursor: pointer;
                }
            """)

            self.image_path = file_path
            self.btn_delete.show()
            self.image_changed.emit(file_path)

    def _on_delete(self):
        """Handle delete button click"""
        self.clear_image()
        self.image_removed.emit()

    def clear_image(self):
        """Clear the current image"""
        self.image_path = None
        self.image_frame.clear()
        self.image_frame.setText("Click to\nupload")
        self.image_frame.setStyleSheet("""
            QLabel {
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
                background: #F5F5F5;
                color: #757575;
                font-size: 12px;
            }
            QLabel:hover {
                border-color: #2196F3;
                background: #E3F2FD;
                cursor: pointer;
            }
        """)
        self.btn_delete.hide()

    def get_image_path(self) -> str:
        """Get current image path"""
        return self.image_path
