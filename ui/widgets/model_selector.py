# -*- coding: utf-8 -*-
"""
ModelSelectorWidget - Collapsible widget for selecting 0-5 models
"""
import json

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ModelImageWidget(QLabel):
    """
    Image widget with selection and delete functionality.

    Features:
    - Click to select image (shows blue border highlight)
    - Hover to show delete button (X in top-right corner)
    - Visual feedback for selected state
    - Pointer cursor on hover for better UX

    Signals:
    - clicked(int): Emitted when image is clicked, passes widget index
    - delete_requested(int): Emitted when delete button is clicked

    Usage:
        widget = ModelImageWidget(image_path, index=0)
        widget.clicked.connect(on_image_selected)
        widget.delete_requested.connect(on_delete_image)
    """

    clicked = pyqtSignal(int)  # Emit index when clicked
    delete_requested = pyqtSignal(int)

    def __init__(self, image_path, index, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.index = index
        self.selected = False

        self.setFixedSize(128, 128)
        self.setScaledContents(True)
        self.setPixmap(QPixmap(image_path))
        self.setCursor(Qt.PointingHandCursor)

        # Delete button (hidden by default)
        self.btn_delete = QPushButton("✕", self)
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.move(104, 0)  # Top-right corner
        self.btn_delete.setVisible(False)
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.index))
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: #F44336;
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #D32F2F; }
        """)

        self._update_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.btn_delete.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_delete.setVisible(False)
        super().leaveEvent(event)

    def set_selected(self, selected):
        self.selected = selected
        self._update_style()

    def _update_style(self):
        if self.selected:
            self.setStyleSheet("border: 3px solid #2196F3; border-radius: 4px;")
        else:
            self.setStyleSheet("border: 1px solid #E0E0E0; border-radius: 4px;")


class ModelRow(QFrame):
    """Single model row with image + JSON editor"""

    remove_requested = pyqtSignal(object)  # self

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.image_path = None
        self.model_data = {}

        self.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                margin: 4px 0px;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        """Build the model row UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Left: Image preview (120x120px)
        left_layout = QVBoxLayout()

        self.img_preview = QLabel()
        self.img_preview.setFixedSize(120, 120)
        self.img_preview.setStyleSheet("""
            QLabel {
                background: #EEEEEE;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
            }
        """)
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.setText("Chưa chọn")
        self.img_preview.setFont(QFont("Segoe UI", 9))
        left_layout.addWidget(self.img_preview)

        btn_upload = QPushButton("📁 Chọn ảnh")
        btn_upload.setMaximumWidth(120)
        btn_upload.clicked.connect(self._pick_image)
        left_layout.addWidget(btn_upload)

        layout.addLayout(left_layout)

        # Right: JSON editor
        right_layout = QVBoxLayout()
        right_layout.setSpacing(4)

        # Header with model number and remove button
        header_layout = QHBoxLayout()
        lbl_header = QLabel(f"Model {self.index + 1}")
        lbl_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        header_layout.addWidget(lbl_header)
        header_layout.addStretch()

        btn_remove = QPushButton("✖")
        btn_remove.setFixedSize(24, 24)
        btn_remove.setStyleSheet("""
            QPushButton {
                background: #F44336;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #D32F2F;
            }
        """)
        btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        header_layout.addWidget(btn_remove)

        right_layout.addLayout(header_layout)

        # JSON editor
        self.ed_json = QTextEdit()
        self.ed_json.setPlaceholderText('{\n  "name": "Model name",\n  "age": 25,\n  "style": "casual"\n}')
        self.ed_json.setFont(QFont("Courier New", 9))
        self.ed_json.setMinimumHeight(100)
        self.ed_json.setMaximumHeight(150)
        right_layout.addWidget(self.ed_json)

        layout.addLayout(right_layout, 1)

    def _pick_image(self):
        """Pick image for model - Issue 4: Enhanced with error handling"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh người mẫu",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if path:
            # Issue 4: Verify file exists
            import os
            if not os.path.exists(path):
                QMessageBox.warning(self, "Lỗi", "File không tồn tại")
                return

            # Issue 4: Try to load the image
            pixmap = QPixmap(path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Lỗi", "Không thể load ảnh. Vui lòng chọn file ảnh hợp lệ.")
                return

            # Issue 4: Successfully loaded, save path and display
            self.image_path = path
            self.img_preview.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def get_data(self):
        """Get model data (image path + JSON)"""
        json_text = self.ed_json.toPlainText().strip()
        try:
            json_data = json.loads(json_text) if json_text else {}
        except:
            json_data = {"raw": json_text}

        return {
            "id": self.index,
            "image_path": self.image_path,
            "data": json_data
        }

    def set_data(self, image_path=None, json_data=None):
        """Set model data"""
        if image_path:
            self.image_path = image_path
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.img_preview.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        if json_data:
            try:
                json_text = json.dumps(json_data, ensure_ascii=False, indent=2)
                self.ed_json.setPlainText(json_text)
            except:
                pass


class ModelSelectorWidget(QGroupBox):
    """
    Collapsible model selector widget supporting 0-5 models
    - Expandable/collapsible with +/- buttons
    - Image preview 120x120px on left
    - JSON editor on right
    - Scrollable if > 2 models
    """

    models_changed = pyqtSignal()  # emitted when models are added/removed

    def __init__(self, title="Thông tin người mẫu", parent=None):
        super().__init__(title, parent)
        self.model_rows = []
        self.is_expanded = True
        self._build_ui()

    def _build_ui(self):
        """Build the widget UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # Header with expand/collapse and add buttons
        header_layout = QHBoxLayout()

        self.btn_toggle = QPushButton("▼")
        self.btn_toggle.setFixedSize(30, 30)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: #E0E0E0;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #BDBDBD;
            }
        """)
        self.btn_toggle.clicked.connect(self._toggle_expand)
        header_layout.addWidget(self.btn_toggle)

        lbl_count = QLabel()
        lbl_count.setFont(QFont("Segoe UI", 10))
        self.lbl_count = lbl_count
        self._update_count_label()
        header_layout.addWidget(lbl_count)

        header_layout.addStretch()

        self.btn_add = QPushButton("➕ Thêm người mẫu")
        self.btn_add.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #45A049;
            }
            QPushButton:disabled {
                background: #CCCCCC;
            }
        """)
        self.btn_add.clicked.connect(self._add_model)
        header_layout.addWidget(self.btn_add)

        main_layout.addLayout(header_layout)

        # Scrollable area for model rows
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(150)
        self.scroll_area.setMaximumHeight(400)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        self.models_container = QWidget()
        self.models_layout = QVBoxLayout(self.models_container)
        self.models_layout.setSpacing(8)
        self.models_layout.addStretch()

        self.scroll_area.setWidget(self.models_container)
        main_layout.addWidget(self.scroll_area)

    def _toggle_expand(self):
        """Toggle expand/collapse"""
        self.is_expanded = not self.is_expanded
        self.scroll_area.setVisible(self.is_expanded)
        self.btn_add.setVisible(self.is_expanded)
        self.btn_toggle.setText("▼" if self.is_expanded else "▶")

    def _add_model(self):
        """Add a new model row"""
        if len(self.model_rows) >= 5:
            QMessageBox.warning(self, "Giới hạn", "Tối đa 5 người mẫu!")
            return

        index = len(self.model_rows)
        row = ModelRow(index, self.models_container)
        row.remove_requested.connect(self._remove_model)

        # Insert before stretch
        self.models_layout.insertWidget(self.models_layout.count() - 1, row)
        self.model_rows.append(row)

        self._update_count_label()
        self._update_add_button()
        self.models_changed.emit()

    def _remove_model(self, row):
        """Remove a model row"""
        if row in self.model_rows:
            self.model_rows.remove(row)
            row.setParent(None)
            row.deleteLater()

            # Re-index remaining rows
            for i, r in enumerate(self.model_rows):
                r.index = i
                # Update label
                for lbl in r.findChildren(QLabel):
                    if lbl.text().startswith("Model"):
                        lbl.setText(f"Model {i + 1}")
                        break

            self._update_count_label()
            self._update_add_button()
            self.models_changed.emit()

    def _update_count_label(self):
        """Update model count label"""
        count = len(self.model_rows)
        self.lbl_count.setText(f"Số người mẫu: {count}")

    def _update_add_button(self):
        """Update add button state"""
        self.btn_add.setEnabled(len(self.model_rows) < 5)

    def get_models(self):
        """Get all model data"""
        return [row.get_data() for row in self.model_rows]

    def set_models(self, models_data):
        """Set models data (list of {image_path, data})"""
        # Clear existing
        for row in self.model_rows[:]:
            self._remove_model(row)

        # Add new
        for model in models_data[:5]:  # Max 5
            self._add_model()
            if self.model_rows:
                self.model_rows[-1].set_data(
                    model.get("image_path"),
                    model.get("data")
                )

    def clear(self):
        """Clear all models"""
        for row in self.model_rows[:]:
            self._remove_model(row)
